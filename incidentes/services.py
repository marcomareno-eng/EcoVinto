"""Casos de uso de EcoVinto, independientes de las vistas NiceGUI."""
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from .domain import DatosIncidente, FiltrosIncidente, validar_transicion
from .models import Incident, User
from .security import Evidencia, EXTENSIONES_IMAGEN, hash_password, verify_password


class IncidentStore(Protocol):
    def add(self, incident: Incident) -> None: ...
    def get(self, incident_id: int) -> Incident | None: ...
    def list(self, filtros: FiltrosIncidente | None = None) -> list[Incident]: ...
    def update_attention(self, previous: Incident, estado: str, responsable: str,
                         atendido_en: datetime | None) -> bool: ...
    def has_image(self, filename: str) -> bool: ...


class UserStore(Protocol):
    def add(self, user: User) -> bool: ...
    def get(self, user_id: int) -> User | None: ...
    def by_email(self, email: str) -> User | None: ...
    def list(self) -> list[User]: ...
    def update_role(self, actor_id: int, user_id: int, role: str, previous_role: str) -> bool: ...


class IncidentService:
    def __init__(self, repository: IncidentStore, upload_dir: Path):
        self.repository = repository
        self.upload_dir = upload_dir

    def reportar(self, datos: DatosIncidente, contacto: str, autor_id: int,
                 evidencia: Evidencia | None = None) -> None:
        incidente = Incident(
            tipo=datos.tipo, descripcion=datos.descripcion, fecha=datos.fecha, contacto=contacto.strip(),
            latitud=datos.coordenadas.latitud, longitud=datos.coordenadas.longitud,
            zona=datos.zona, user_id=autor_id,
        )
        foto = None
        try:
            if evidencia:
                incidente.imagen = f"{uuid4().hex}{evidencia.extension}"
                foto = self.upload_dir / incidente.imagen
                foto.write_bytes(evidencia.contenido)
            self.repository.add(incidente)
        except Exception:
            if foto:
                foto.unlink(missing_ok=True)
            raise

    def listar(self, filtros: FiltrosIncidente | None = None) -> list[Incident]:
        return self.repository.list(filtros)

    def detalle(self, incident_id: int) -> Incident | None:
        return self.repository.get(incident_id)

    def actualizar(self, original: Incident, estado: str, responsable: str,
                   ahora: datetime | None = None) -> None:
        responsable = responsable.strip()
        if not validar_transicion(original.estado, estado):
            raise ValueError("Avanza los estados uno por uno, sin retroceder.")
        if estado in ("En atención", "Atendido", "Cerrado") and not responsable:
            raise ValueError("Asigna un responsable para atender el reporte.")
        atendido_en = original.atendido_en
        if estado == "Atendido" and original.estado != "Atendido" and atendido_en is None:
            atendido_en = ahora or datetime.now()
        if not self.repository.update_attention(original, estado, responsable, atendido_en):
            raise ValueError("El reporte cambió en otra sesión. Cierra este detalle y vuelve a abrirlo.")

    def foto(self, filename: str) -> Path | None:
        # Solo se sirven archivos vinculados a un reporte y contenidos en la carpeta de evidencias.
        if (Path(filename).name != filename or Path(filename).suffix.lower() not in EXTENSIONES_IMAGEN
                or not self.repository.has_image(filename)):
            return None
        path = self.upload_dir / filename
        if path.is_symlink() or not path.is_file():
            return None
        return path


class AccountService:
    def __init__(self, repository: UserStore):
        self.repository = repository

    def autenticar(self, email: str, password: str) -> User | None:
        user = self.repository.by_email(email.strip().lower())
        if user and verify_password(password, user.password_hash):
            return user
        return None

    def registrar(self, nombre: str, email: str, telefono: str, password: str) -> None:
        nombre, email = nombre.strip(), email.strip().lower()
        local, separador, dominio = email.partition("@")
        if (not nombre or not separador or not local or "." not in dominio.strip(".")
                or "@" in dominio or any(c.isspace() for c in email)):
            raise ValueError("Escribe tu nombre y un correo válido.")
        if not 8 <= len(password) <= 128:
            raise ValueError("La contraseña debe tener entre 8 y 128 caracteres.")
        user = User(nombre=nombre, email=email, telefono=telefono.strip(), password_hash=hash_password(password))
        if not self.repository.add(user):
            raise ValueError("Ya existe una cuenta con ese correo.")

    def usuario(self, user_id: int) -> User | None:
        return self.repository.get(user_id)

    def usuarios(self) -> list[User]:
        return self.repository.list()

    def cambiar_rol(self, actor_id: int, user_id: int) -> None:
        actor = self.repository.get(actor_id)
        if actor is None or actor.rol != "admin" or actor_id == user_id:
            raise ValueError("No tienes permiso para realizar este cambio.")
        user = self.repository.get(user_id)
        if user is None:
            raise ValueError("La cuenta ya no está disponible.")
        nuevo_rol = "vecino" if user.rol == "admin" else "admin"
        if not self.repository.update_role(actor_id, user_id, nuevo_rol, user.rol):
            raise ValueError("El rol cambió en otra sesión. Actualiza la lista.")
