from collections import Counter
from nicegui import ui
from ..auth import require_login
from ..config import MAP_LAT, MAP_LNG
from ..dependencies import cuentas, incidentes
from ..models import ESTADOS, TIPOS
from ..domain import estadisticas
from ..ui_kit import frame, mapa_base

AZULES = ["#93c5fd", "#38bdf8", "#2563eb", "#0d9488", "#1e3a8a"]


def _stat(titulo, valor, icono):
    with ui.card().classes("flex-1 min-w-[150px] p-4 rounded-xl border-l-4 border-blue-600"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label(str(valor)).classes("text-3xl font-extrabold text-blue-900")
            ui.icon(icono, size="28px").classes("text-blue-300")
        ui.label(titulo).classes("text-sm text-slate-500")


@ui.page("/admin")
def admin_page():
    user = require_login("admin")
    if not user:
        return
    frame(user, "/admin")

    @ui.refreshable
    def resumen():
        incs = incidentes.listar()
        metricas = estadisticas(incs)
        por_estado = Counter(i.estado for i in incs)
        por_tipo = Counter(i.tipo for i in incs)
        with ui.row().classes("w-full gap-4"):
            _stat("Total de reportes", len(incs), "assignment")
            _stat("Tiempo medio de respuesta", f"{metricas['horas_respuesta_media']} h" if metricas['horas_respuesta_media'] is not None else "Sin datos", "schedule")
            for e in ESTADOS:
                _stat(e, por_estado.get(e, 0), "flag")
        with ui.row().classes("w-full gap-4 mt-2"):
            with ui.card().classes("flex-1 min-w-[320px] rounded-xl"):
                ui.label("Reportes por categoría").classes("font-bold text-blue-900")
                ui.echart({"tooltip": {}, "grid": {"bottom": 80},
                           "xAxis": {"type": "category", "data": TIPOS, "axisLabel": {"rotate": 30}},
                           "yAxis": {"type": "value", "minInterval": 1},
                           "series": [{"type": "bar", "data": [por_tipo.get(t, 0) for t in TIPOS],
                                       "itemStyle": {"color": "#2563eb", "borderRadius": [4, 4, 0, 0]}}]}) \
                    .classes("w-full h-72")
            with ui.card().classes("flex-1 min-w-[320px] rounded-xl"):
                ui.label("Reportes por estado").classes("font-bold text-blue-900")
                ui.echart({"tooltip": {"trigger": "item"}, "color": AZULES, "legend": {"bottom": 0},
                           "series": [{"type": "pie", "radius": ["45%", "70%"],
                                       "data": [{"name": e, "value": por_estado.get(e, 0)} for e in ESTADOS]}]}) \
                    .classes("w-full h-72")
        with ui.card().classes("w-full rounded-xl mt-2"):
            ui.label("Zonas críticas (más reportes)").classes("font-bold text-blue-900")
            for zona_nombre, cantidad in metricas['zonas_criticas']:
                ui.label(f"{zona_nombre}: {cantidad} reporte(s)")
        with ui.card().classes("w-full rounded-xl mt-2"):
            ui.label("Mapa de incidentes").classes("font-bold text-blue-900")
            m = mapa_base(center=(MAP_LAT, MAP_LNG), zoom=13).classes("w-full h-96 rounded-lg")
            for i in incs:
                m.marker(latlng=(i.latitud, i.longitud))

    @ui.refreshable
    def gestion():
        incs = incidentes.listar()
        autores = {u.id: u.nombre for u in cuentas.usuarios()}
        filas = [{"id": i.id, "tipo": i.tipo, "fecha": f"{i.fecha:%d/%m/%Y %H:%M}", "estado": i.estado,
                  "responsable": i.responsable or "—", "vecino": autores.get(i.user_id, "?")} for i in incs]
        cols = [{"name": k, "label": l, "field": k, "align": "left", "sortable": True} for k, l in
                [("id", "#"), ("tipo", "Categoría"), ("fecha", "Fecha"), ("vecino", "Vecino"),
                 ("estado", "Estado"), ("responsable", "Responsable")]]
        buscar = ui.input("Buscar", placeholder="Categoría, vecino, estado…").props("outlined dense clearable") \
            .classes("w-72")
        tabla = ui.table(columns=cols, rows=filas, row_key="id", pagination=10).classes("w-full cursor-pointer")
        buscar.bind_value_to(tabla, "filter")
        tabla.add_slot("body-cell-estado", '<q-td :props="props"><q-badge color="primary">{{ props.value }}</q-badge></q-td>')
        tabla.on("rowClick", lambda e: abrir(e.args[1]["id"]))
        if not filas:
            ui.label("Aún no hay incidentes registrados.").classes("text-slate-500")

    def abrir(iid: int):
        if not require_login("admin"):
            return
        inc = incidentes.detalle(iid)
        if inc is None:
            return ui.notify("El reporte ya no está disponible.", type="warning")
        autor = cuentas.usuario(inc.user_id)
        nombre_autor = f"{autor.nombre} ({autor.email})" if autor else "Cuenta no disponible"
        with ui.dialog().props("maximized=false") as d, ui.card().classes("w-[760px] max-w-full gap-3"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(f"#{inc.id} · {inc.tipo}").classes("text-xl font-extrabold text-blue-900")
                ui.button(icon="close", on_click=d.close).props('flat round dense aria-label="Cerrar detalle"')
            ui.label(inc.descripcion).classes("text-slate-700")
            ui.label(f"Reportó: {nombre_autor} · Contacto: {inc.contacto or '—'} · {inc.fecha:%d/%m/%Y %H:%M}") \
                .classes("text-xs text-slate-500")
            if inc.imagen:
                ui.image(f"/uploads/{inc.imagen}").classes("w-full max-h-80 rounded-lg")
            else:
                ui.label("Sin evidencia fotográfica.").classes("text-sm text-slate-400")
            m = mapa_base(center=(inc.latitud, inc.longitud), zoom=16).classes("w-full h-60 rounded-lg")
            m.marker(latlng=(inc.latitud, inc.longitud))
            with ui.row().classes("w-full gap-3"):
                est = ui.select(ESTADOS, label="Estado", value=inc.estado).props("outlined dense").classes("flex-1")
                resp = ui.input("Responsable asignado", value=inc.responsable).props("outlined dense").classes("flex-1")

            def guardar():
                if not require_login("admin"):
                    return
                try:
                    incidentes.actualizar(inc, est.value, resp.value or "")
                except ValueError as error:
                    return ui.notify(str(error), type="warning")
                d.close()
                ui.notify("Incidente actualizado.", type="positive")
                gestion.refresh()
                resumen.refresh()

            ui.button("Guardar cambios", icon="save", on_click=guardar).props("no-caps unelevated").classes("self-end")
        d.on("hide", lambda: d.delete())
        d.open()
        ui.timer(0.4, lambda: m.run_map_method("invalidateSize"), once=True)

    @ui.refreshable
    def usuarios():
        us = cuentas.usuarios()
        for u in us:
            with ui.card().classes("w-full flex-row items-center gap-3 p-3 rounded-xl"):
                ui.icon("person").classes("text-blue-500")
                ui.label(f"{u.nombre} · {u.email}").classes("text-sm")
                ui.space()
                ui.badge("Administrador" if u.rol == "admin" else "Vecino").props("color=primary" if u.rol == "admin" else "color=blue-grey")
                if u.id != user["id"]:
                    ui.button("Cambiar rol", on_click=lambda uid=u.id: cambiar_rol(uid)).props("flat no-caps dense")

    def cambiar_rol(uid: int):
        actor = require_login("admin")
        if not actor:
            return
        try:
            cuentas.cambiar_rol(actor["id"], uid)
        except ValueError as error:
            return ui.notify(str(error), type="warning")
        ui.notify("Rol actualizado.", type="positive")
        usuarios.refresh()

    with ui.column().classes("w-full max-w-6xl mx-auto gap-2 p-2"):
        ui.label("Panel de administración").classes("text-2xl font-extrabold text-blue-900")
        with ui.tabs().classes("w-full text-blue-800") as tabs:
            t1 = ui.tab("Resumen", icon="dashboard")
            t2 = ui.tab("Gestión de incidentes", icon="table_view")
            t3 = ui.tab("Usuarios", icon="group")
        with ui.tab_panels(tabs, value=t1).classes("w-full bg-transparent"):
            with ui.tab_panel(t1).classes("p-0 pt-3"):
                resumen()
            with ui.tab_panel(t2).classes("p-0 pt-3"):
                gestion()
            with ui.tab_panel(t3).classes("p-0 pt-3 gap-2"):
                usuarios()
