from datetime import datetime
from pydantic import NaiveDatetime
from typing import Optional
from sqlmodel import SQLModel, Field

from .domain import ESTADOS_VALIDOS, TIPOS_VALIDOS

TIPOS = list(TIPOS_VALIDOS)
ESTADOS = list(ESTADOS_VALIDOS)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    email: str = Field(index=True, unique=True)
    telefono: str = ""
    password_hash: str
    rol: str = "vecino"  # "admin" | "vecino"
    creado: NaiveDatetime = Field(default_factory=datetime.now)


class Incident(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tipo: str
    descripcion: str
    fecha: NaiveDatetime
    contacto: str = ""
    latitud: float
    longitud: float
    imagen: Optional[str] = Field(default=None, index=True)
    estado: str = "Reportado"
    responsable: str = ""
    zona: str = ""
    atendido_en: Optional[NaiveDatetime] = None
    user_id: int = Field(foreign_key="user.id")
    creado: NaiveDatetime = Field(default_factory=datetime.now)
