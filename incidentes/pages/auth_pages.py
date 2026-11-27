from nicegui import run, ui
from ..auth import current_user, login_user
from ..dependencies import cuentas
from ..ui_kit import setup_theme


def _shell(titulo: str, subtitulo: str):
    setup_theme()
    with ui.column().classes("absolute-full items-center justify-center p-4 bg-gradient-to-br from-blue-950 via-blue-800 to-sky-400"):
        card = ui.card().classes("w-full max-w-md p-8 rounded-2xl shadow-2xl gap-3")
    with card:
        with ui.row().classes("items-center gap-2"):
            ui.icon("water_drop", size="32px").classes("text-blue-700")
            ui.label("EcoVinto").classes("text-2xl font-extrabold text-blue-900")
        ui.label(titulo).classes("text-xl font-bold text-slate-800")
        ui.label(subtitulo).classes("text-sm text-slate-500 -mt-2")
    return card


def _field(label, **kw):
    return ui.input(label, **kw).props("outlined dense").classes("w-full")


@ui.page("/")
def home():
    user = current_user()
    ui.navigate.to("/login" if not user else "/admin" if user["rol"] == "admin" else "/incidentes")


@ui.page("/login")
def login_page():
    if current_user():
        return ui.navigate.to("/")
    with _shell("Iniciar sesión", "Reporta y sigue los incidentes ambientales del municipio de Vinto."):
        email = _field("Correo electrónico")
        pw = _field("Contraseña", password=True, password_toggle_button=True)

        async def entrar():
            u = await run.io_bound(cuentas.autenticar, email.value or "", pw.value or "")
            if not u:
                return ui.notify("Correo o contraseña incorrectos.", type="negative")
            login_user(u)
            ui.navigate.to("/")

        pw.on("keydown.enter", entrar)
        ui.button("Ingresar", on_click=entrar).classes("w-full").props("no-caps unelevated size=lg")
        ui.link("Crear cuenta de vecino", "/registro").classes("text-sm text-blue-700 self-center")


@ui.page("/registro")
def registro_page():
    if current_user():
        return ui.navigate.to("/")
    with _shell("Crear cuenta", "Regístrate como vecino para reportar incidentes."):
        nombre = _field("Nombre completo")
        email = _field("Correo electrónico")
        tel = _field("Teléfono (opcional)")
        pw = _field("Contraseña (mínimo 8 caracteres)", password=True, password_toggle_button=True)
        pw2 = _field("Repite la contraseña", password=True)

        async def crear():
            if pw.value != pw2.value:
                return ui.notify("Las contraseñas no coinciden.", type="warning")
            try:
                await run.io_bound(cuentas.registrar, nombre.value or "", email.value or "",
                                   tel.value or "", pw.value or "")
            except ValueError as error:
                return ui.notify(str(error), type="warning")
            ui.notify("Cuenta creada. Ya puedes iniciar sesión.", type="positive")
            ui.navigate.to("/login")

        ui.button("Crear cuenta", on_click=crear).classes("w-full").props("no-caps unelevated size=lg")
        ui.link("Ya tengo cuenta", "/login").classes("text-sm text-blue-700 self-center")
