"""Composición de los casos de uso con los adaptadores SQLModel."""
from .config import UPLOAD_DIR
from .database import engine
from .repositories import IncidentRepository, UserRepository
from .services import AccountService, IncidentService

cuentas = AccountService(UserRepository(engine))
incidentes = IncidentService(IncidentRepository(engine), UPLOAD_DIR)
