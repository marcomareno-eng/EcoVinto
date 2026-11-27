"""Persistencia de cuentas e incidentes con SQLModel."""
from sqlalchemy import exists, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .domain import FiltrosIncidente
from .models import Incident, User


class IncidentRepository:
    def __init__(self, engine):
        self.engine = engine

    def add(self, incident: Incident) -> None:
        with Session(self.engine) as session:
            session.add(incident)
            session.commit()

    def get(self, incident_id: int) -> Incident | None:
        with Session(self.engine) as session:
            return session.get(Incident, incident_id)

    def list(self, filtros: FiltrosIncidente | None = None) -> list[Incident]:
        query = select(Incident).order_by(Incident.fecha.desc(), Incident.id.desc())
        if filtros:
            if filtros.tipo:
                query = query.where(Incident.tipo == filtros.tipo)
            if filtros.estado:
                query = query.where(Incident.estado == filtros.estado)
            if filtros.desde:
                query = query.where(Incident.fecha >= filtros.desde)
            if filtros.hasta:
                query = query.where(Incident.fecha < filtros.hasta)
            if filtros.zona:
                query = query.where(Incident.zona.icontains(filtros.zona, autoescape=True))
            if filtros.user_id is not None:
                query = query.where(Incident.user_id == filtros.user_id)
        with Session(self.engine) as session:
            return list(session.exec(query).all())

    def update_attention(self, previous: Incident, estado, responsable, atendido_en) -> bool:
        # Un segundo operador no debe sobrescribir cambios hechos desde otro diálogo.
        statement = (
            update(Incident)
            .where(
                Incident.id == previous.id,
                Incident.estado == previous.estado,
                Incident.responsable == previous.responsable,
                Incident.atendido_en == previous.atendido_en,
            )
            .values(estado=estado, responsable=responsable, atendido_en=atendido_en)
        )
        with Session(self.engine) as session:
            updated = session.execute(statement).rowcount == 1
            session.commit()
            return updated

    def has_image(self, filename: str) -> bool:
        with Session(self.engine) as session:
            return session.exec(select(Incident.id).where(Incident.imagen == filename).limit(1)).first() is not None


class UserRepository:
    def __init__(self, engine):
        self.engine = engine

    def add(self, user: User) -> bool:
        with Session(self.engine) as session:
            session.add(user)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                if self.by_email(user.email) is None:
                    raise
                return False
            return True

    def by_email(self, email: str) -> User | None:
        with Session(self.engine) as session:
            return session.exec(select(User).where(User.email == email)).first()

    def get(self, user_id: int) -> User | None:
        with Session(self.engine) as session:
            return session.get(User, user_id)

    def list(self) -> list[User]:
        with Session(self.engine) as session:
            return list(session.exec(select(User).order_by(User.id)).all())

    def update_password(self, user_id: int, password_hash: str, previous_hash: str) -> None:
        statement = (
            update(User)
            .where(User.id == user_id, User.password_hash == previous_hash)
            .values(password_hash=password_hash)
        )
        with Session(self.engine) as session:
            session.execute(statement)
            session.commit()

    def update_role(self, actor_id: int, user_id: int, role: str, previous_role: str) -> bool:
        actor = User.__table__.alias("actor")
        statement = (
            update(User)
            .where(
                User.id == user_id,
                User.rol == previous_role,
                exists(select(actor.c.id).where(actor.c.id == actor_id, actor.c.rol == "admin")),
            )
            .values(rol=role)
        )
        with Session(self.engine) as session:
            result = session.execute(statement)
            session.commit()
            return result.rowcount == 1
