from pathlib import Path

from sqlalchemy import event, inspect, text
from sqlmodel import SQLModel, create_engine

from . import config
from .models import User
from .repositories import UserRepository
from .security import hash_password, verify_password

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {},
)


if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")


def init_db(database=engine):
    if database.url.get_backend_name() == "sqlite" and database.url.database not in (None, ":memory:"):
        Path(database.url.database).parent.mkdir(parents=True, exist_ok=True)
    if database.dialect.name == "sqlite":
        with database.begin() as conexion:
            # SQLite serializa esta migración si dos procesos se inician a la vez.
            conexion.exec_driver_sql("BEGIN IMMEDIATE")
            SQLModel.metadata.create_all(conexion)
            columnas = {columna["name"] for columna in inspect(conexion).get_columns("incident")}
            if "zona" not in columnas:
                conexion.execute(text("ALTER TABLE incident ADD COLUMN zona VARCHAR NOT NULL DEFAULT ''"))
            if "atendido_en" not in columnas:
                conexion.execute(text("ALTER TABLE incident ADD COLUMN atendido_en DATETIME"))
            conexion.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_incident_imagen ON incident (imagen)")
    else:
        SQLModel.metadata.create_all(database)


def init_admin():
    usuarios = UserRepository(engine)
    email = config.ADMIN_EMAIL.strip().lower()
    usuario = usuarios.by_email(email)
    if usuario and usuario.rol != "admin":
        raise RuntimeError("ADMIN_EMAIL ya está asignado a una cuenta vecinal. Usa el correo de un administrador.")
    if usuario and not verify_password("Admin12345", usuario.password_hash):
        return
    password = config.ADMIN_PASSWORD
    if not 12 <= len(password) <= 128 or password.lower() == "admin12345":
        raise RuntimeError("Configura ADMIN_PASSWORD con una contraseña de 12 a 128 caracteres para crear al administrador.")
    password_hash = hash_password(password)
    if usuario:
        usuarios.update_password(usuario.id, password_hash, usuario.password_hash)
    else:
        usuarios.add(User(nombre=config.ADMIN_NAME, email=email, rol="admin", password_hash=password_hash))
