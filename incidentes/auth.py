"""Vincula la identidad autenticada con la sesión de NiceGUI."""
from nicegui import app, ui

from .dependencies import cuentas
from .models import User


def login_user(user: User) -> None:
    app.storage.user.clear()
    app.storage.user["uid"] = user.id


def logout() -> None:
    app.storage.user.clear()
    ui.navigate.to("/login")


def current_user() -> dict | None:
    uid = app.storage.user.get("uid")
    user = cuentas.usuario(uid) if uid is not None else None
    if user:
        return {"id": user.id, "nombre": user.nombre, "rol": user.rol}
    return None


def require_login(role: str | None = None) -> dict | None:
    user = current_user()
    if user is None:
        ui.navigate.to("/login")
        return None
    if role and user["rol"] != role:
        ui.navigate.to("/")
        return None
    return user
