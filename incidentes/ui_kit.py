from nicegui import ui
from .auth import logout
from .models import ESTADOS

ESTADO_COLOR = {"Reportado": "blue-grey", "En revisión": "light-blue-7",
                "En atención": "blue-8", "Atendido": "teal-7", "Cerrado": "green-8"}


def setup_theme():
    ui.colors(primary="#1d4ed8", secondary="#0ea5e9", accent="#38bdf8",
              positive="#0d9488", info="#0284c7")
    ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;700;800&display=swap" rel="stylesheet">'
                     '<style>body{font-family:"Plus Jakarta Sans",system-ui,sans-serif}</style>')
    ui.query("body").classes("bg-slate-50")


def frame(user: dict, active: str):
    """Cabecera + menú lateral según el rol."""
    setup_theme()
    items = [("Reportar incidente", "add_location_alt", "/reportar"),
             ("Incidentes", "travel_explore", "/incidentes")]
    if user["rol"] == "admin":
        items.insert(0, ("Panel de administración", "space_dashboard", "/admin"))

    with ui.header().classes("bg-gradient-to-r from-blue-950 to-blue-600 text-white items-center gap-3 shadow-md"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()).props("flat round dense color=white")
        ui.icon("water_drop", size="28px")
        ui.label("EcoVinto").classes("text-xl font-extrabold tracking-tight")
        ui.label("Incidentes ambientales").classes("text-sm opacity-80 max-sm:hidden")
        ui.space()
        ui.label(user["nombre"]).classes("text-sm font-medium max-sm:hidden")
        ui.badge("Administrador" if user["rol"] == "admin" else "Vecino").props("color=sky-6")
        ui.button(icon="logout", on_click=logout).props('flat round dense color=white aria-label="Cerrar sesión"').tooltip("Cerrar sesión")

    with ui.left_drawer(value=True).classes("bg-white border-r border-blue-100 pt-6") as drawer:
        with ui.column().classes("w-full gap-1"):
            for label, icon, path in items:
                on = path == active
                ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)) \
                    .props("flat no-caps align=left").classes(
                        "w-full justify-start " + ("bg-blue-50 text-blue-800 font-bold" if on else "text-slate-600"))


def mapa_base(center: tuple[float, float], zoom: int):
    mapa = ui.leaflet(center=center, zoom=zoom)
    mapa.clear_layers()
    mapa.tile_layer(
        url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        options={"attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'},
    )
    return mapa


def estado_badge(estado: str):
    return ui.badge(estado).props(f"color={ESTADO_COLOR.get(estado, 'primary')}")


def incident_card(inc, on_click=None):
    prog = ESTADOS.index(inc.estado) / (len(ESTADOS) - 1)
    with ui.card().classes("w-80 p-0 rounded-xl shadow-sm border border-blue-100 overflow-hidden"):
        if inc.imagen:
            ui.image(f"/uploads/{inc.imagen}").classes("h-40 w-full")
        else:
            with ui.element("div").classes("h-40 w-full bg-blue-50 flex items-center justify-center"):
                ui.icon("image_not_supported", size="40px").classes("text-blue-300")
        with ui.column().classes("p-4 gap-1 w-full"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(inc.tipo).classes("font-bold text-blue-900")
                estado_badge(inc.estado)
            ui.label(inc.descripcion).classes("text-sm text-slate-600 line-clamp-3")
            ui.label(f"{inc.fecha:%d/%m/%Y %H:%M}  ·  #{inc.id}").classes("text-xs text-slate-400")
            if inc.responsable:
                ui.label(f"Responsable: {inc.responsable}").classes("text-xs text-slate-500")
            ui.linear_progress(value=prog, show_value=False).props("rounded color=primary track-color=blue-1")
    return None
