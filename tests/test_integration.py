"""Integración con una base SQLite real y archivos aislados por prueba."""
from datetime import datetime, timedelta
import hashlib
from io import BytesIO
import sqlite3

from PIL import Image
import pytest
from sqlmodel import create_engine

from incidentes.database import init_db
from incidentes.domain import FiltrosIncidente, IncidenteFactory, estadisticas
from incidentes.models import User
from incidentes.repositories import IncidentRepository, UserRepository
from incidentes.security import Evidencia, hash_password, verify_password
from incidentes.services import AccountService, IncidentService


@pytest.fixture
def entorno(tmp_path):
    database = create_engine(f"sqlite:///{tmp_path / 'ecovinto.db'}")
    init_db(database)
    accounts = AccountService(UserRepository(database))
    incidents = IncidentService(IncidentRepository(database), tmp_path)
    yield accounts, incidents
    database.dispose()


@pytest.fixture
def datos():
    return IncidenteFactory.crear("Quema", "Hay humo cerca del parque", datetime(2026, 11, 26, 23, 59, 59),
                                  -17.39, -66.31, "Centro")


def test_cuenta_vecinal_y_correo_unico(entorno):
    cuentas, _ = entorno
    cuentas.registrar(" Vecina de prueba ", " Vecina@Example.Test ", "", "contraseña-demo")

    usuario = cuentas.autenticar("VECINA@example.test", "contraseña-demo")
    autenticacion_invalida = cuentas.autenticar("vecina@example.test", "otra-contraseña")
    with pytest.raises(ValueError, match="Ya existe"):
        cuentas.registrar("Otra", "vecina@example.test", "", "contraseña-demo")

    assert usuario.nombre == "Vecina de prueba"
    assert usuario.rol == "vecino"
    assert autenticacion_invalida is None
    assert len(cuentas.usuarios()) == 1


def test_cambio_de_rol_exige_admin_y_revalida_permiso(entorno):
    cuentas, _ = entorno
    for email in ("admin@example.test", "otra@example.test", "vecina@example.test"):
        cuentas.repository.add(User(nombre=email, email=email, rol="admin" if email.startswith("admin") else "vecino",
                                    password_hash="fixture"))
    admin, otra, vecina = cuentas.usuarios()

    cuentas.cambiar_rol(admin.id, otra.id)
    cuentas.cambiar_rol(otra.id, admin.id)
    with pytest.raises(ValueError, match="permiso"):
        cuentas.cambiar_rol(admin.id, vecina.id)
    with pytest.raises(ValueError, match="permiso"):
        cuentas.cambiar_rol(otra.id, otra.id)

    assert cuentas.usuario(admin.id).rol == "vecino"
    assert cuentas.usuario(otra.id).rol == "admin"
    assert cuentas.usuario(vecina.id).rol == "vecino"


def test_registro_foto_y_filtros_persisten(entorno, datos):
    cuentas, incidentes = entorno
    cuentas.repository.add(User(nombre="Vecina", email="vecina@example.test", password_hash="fixture"))
    [vecina] = cuentas.usuarios()
    archivo = BytesIO()
    Image.new("RGB", (20, 20), "blue").save(archivo, "PNG")
    evidencia = Evidencia.desde_archivo("foto.png", archivo.getvalue())

    incidentes.reportar(datos, " 123 ", vecina.id, evidencia)
    filtros = FiltrosIncidente.desde_formulario("Quema", "Reportado", "cent", "", "2026-11-26", vecina.id)
    [incidente] = incidentes.listar(filtros)
    foto = incidentes.foto(incidente.imagen)

    assert incidente.descripcion == datos.descripcion
    assert incidente.contacto == "123"
    assert incidente.zona == "Centro"
    assert foto.read_bytes() == evidencia.contenido
    assert incidentes.foto("sin-registro.png") is None
    assert incidentes.listar(FiltrosIncidente(zona="%")) == []
    assert incidentes.listar(FiltrosIncidente(user_id=vecina.id + 1)) == []


def test_retirar_archivo_si_falla_la_persistencia(entorno, datos, monkeypatch):
    _, incidentes = entorno
    archivo = BytesIO()
    Image.new("RGB", (20, 20)).save(archivo, "PNG")
    evidencia = Evidencia.desde_archivo("foto.png", archivo.getvalue())

    def rechazar_guardado(_incidente):
        raise RuntimeError("escritura fallida")

    monkeypatch.setattr(incidentes.repository, "add", rechazar_guardado)

    with pytest.raises(RuntimeError, match="escritura fallida"):
        incidentes.reportar(datos, "", 1, evidencia)

    assert list(incidentes.upload_dir.glob("*.png")) == []
    assert incidentes.listar() == []


def test_atencion_secuencial_y_deteccion_de_cambios_concurrentes(entorno, datos):
    cuentas, incidentes = entorno
    cuentas.repository.add(User(nombre="Vecina", email="vecina@example.test", password_hash="fixture"))
    [vecina] = cuentas.usuarios()
    incidentes.reportar(datos, "", vecina.id)
    [original] = incidentes.listar()
    primera_atencion = original.creado + timedelta(hours=2)

    with pytest.raises(ValueError, match="uno por uno"):
        incidentes.actualizar(original, "Cerrado", "Equipo")
    incidentes.actualizar(original, "En revisión", "")
    with pytest.raises(ValueError, match="otra sesión"):
        incidentes.actualizar(original, "En revisión", "Otra persona")
    revision = incidentes.detalle(original.id)
    with pytest.raises(ValueError, match="responsable"):
        incidentes.actualizar(revision, "En atención", "")
    incidentes.actualizar(revision, "En atención", "Equipo")
    incidentes.actualizar(incidentes.detalle(original.id), "Atendido", "Equipo", primera_atencion)
    incidentes.actualizar(incidentes.detalle(original.id), "Cerrado", "Equipo",
                          primera_atencion + timedelta(hours=2))

    [cerrado] = incidentes.listar()
    assert cerrado.estado == "Cerrado"
    assert cerrado.responsable == "Equipo"
    assert cerrado.atendido_en == primera_atencion
    assert estadisticas([cerrado])["horas_respuesta_media"] == 2


def test_migracion_sqlite_anterior_conserva_reportes(tmp_path):
    ruta = tmp_path / "anterior.db"
    with sqlite3.connect(ruta) as conexion:
        conexion.executescript("""
            CREATE TABLE incident (
              id INTEGER PRIMARY KEY, tipo VARCHAR, descripcion VARCHAR, fecha DATETIME,
              contacto VARCHAR, latitud FLOAT, longitud FLOAT, imagen VARCHAR, estado VARCHAR,
              responsable VARCHAR, user_id INTEGER, creado DATETIME
            );
            INSERT INTO incident VALUES (
              7, 'Quema', 'Reporte anterior', '2026-11-16 10:00:00', '',
              -17.39, -66.31, NULL, 'En revisión', '', 2, '2026-11-16 10:00:00'
            );
        """)
    database = create_engine(f"sqlite:///{ruta}")

    init_db(database)
    init_db(database)
    [anterior] = IncidentRepository(database).list()

    assert anterior.id == 7
    assert anterior.estado == "En revisión"
    assert anterior.zona == ""
    assert anterior.atendido_en is None
    database.dispose()


def test_passwords_nuevas_y_heredadas():
    password = "contraseña heredada"
    salt = b"sal-de-prueba-01"
    previous_digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    heredada = f"{salt.hex()}${previous_digest.hex()}"

    actual = hash_password(password)

    assert actual.startswith("600000$")
    assert verify_password(password, heredada)
    assert verify_password(password, actual)
    assert not verify_password("incorrecta", actual)


def test_imagen_con_firma_pero_sin_pixeles_se_rechaza():
    contenido = b"\x89PNG\r\n\x1a\ncontenido"

    with pytest.raises(ValueError, match="dañada o incompleta"):
        Evidencia.desde_archivo("foto.png", contenido)
