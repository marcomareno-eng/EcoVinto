from datetime import datetime
from nicegui import run, ui
from ..auth import require_login
from ..config import MAP_LAT, MAP_LNG
from ..dependencies import incidentes
from ..models import TIPOS, ESTADOS
from ..domain import FiltrosIncidente, IncidenteFactory
from ..adapters import LeafletAdapter
from ..security import Evidencia, MAX_IMAGE_BYTES
from ..ui_kit import frame, incident_card, mapa_base

@ui.page("/reportar")
def reportar_page():
    user = require_login()
    if not user:
        return
    frame(user, "/reportar")
    ubicacion = None
    evidencia = None
    enviando = False
    validando_foto = False

    with ui.column().classes("w-full max-w-4xl mx-auto gap-4 p-2"):
        ui.label("Reportar un incidente").classes("text-2xl font-extrabold text-blue-900")
        ui.label("Cuéntanos qué ocurre y marca el lugar exacto en el mapa.").classes("text-slate-500 -mt-3")

        with ui.card().classes("w-full p-6 rounded-xl gap-3"):
            tipo = ui.select(TIPOS, label="Tipo de incidente", value=TIPOS[0]).props("outlined dense").classes("w-full")
            desc = ui.textarea("Descripción detallada").props("outlined").classes("w-full")
            with ui.row().classes("w-full gap-3"):
                fecha = ui.input("Fecha y hora", value=datetime.now().strftime("%Y-%m-%dT%H:%M")) \
                    .props("outlined dense type=datetime-local").classes("flex-1 min-w-[220px]")
                contacto = ui.input("Datos de contacto (teléfono o correo)").props("outlined dense") \
                    .classes("flex-1 min-w-[220px]")

            zona = ui.input("Zona / barrio / referencia local", placeholder="Ej.: plaza principal, zona norte").props("outlined dense").classes("w-full")
            ui.label("Evidencia fotográfica").classes("font-bold text-blue-900 mt-2")

            foto_adjunta = ui.label("Sin foto adjunta").classes("text-sm text-slate-500")

            async def al_subir(e):
                nonlocal evidencia, validando_foto
                sesion = require_login()
                if not sesion or sesion["id"] != user["id"] or enviando or validando_foto:
                    return
                validando_foto = True
                try:
                    if e.file.size() > MAX_IMAGE_BYTES:
                        raise ValueError("La imagen supera el límite permitido de 5 MB.")
                    contenido = await e.file.read()
                    evidencia = await run.io_bound(Evidencia.desde_archivo, e.file.name, contenido)
                except ValueError as error:
                    return ui.notify(str(error), type="negative")
                finally:
                    validando_foto = False
                foto_adjunta.text = f"Foto adjunta: {e.file.name}"
                ui.notify("Foto adjuntada.", type="positive")

            def quitar_foto():
                nonlocal evidencia
                if validando_foto or enviando:
                    return
                evidencia = None
                foto_adjunta.text = "Sin foto adjunta"
                selector.reset()

            selector = ui.upload(label="Seleccionar foto (máx. 5 MB)", on_upload=al_subir, auto_upload=True,
                                 max_files=1, max_file_size=MAX_IMAGE_BYTES,
                                 on_rejected=lambda: ui.notify("Archivo rechazado. Usa JPG, PNG o WEBP de hasta 5 MB.",
                                                              type="negative"))
            selector.props("accept=.jpg,.jpeg,.png,.webp flat bordered").classes("w-full")
            ui.button("Quitar foto", icon="delete_outline", on_click=quitar_foto).props("flat dense no-caps")

            ui.label("Ubicación").classes("font-bold text-blue-900 mt-2")
            ui.label("Haz clic en el mapa para colocar el marcador.").classes("text-sm text-slate-500 -mt-2")
            mapa = mapa_base(center=(MAP_LAT, MAP_LNG), zoom=14).classes("w-full h-96 rounded-lg")
            marcador = None
            coords = ui.label("Ubicación por marcar").classes("text-xs text-slate-500")

            def al_clic(e):
                nonlocal ubicacion, marcador
                try:
                    ubicacion = LeafletAdapter.desde_evento(e.args)
                except (KeyError, TypeError, ValueError):
                    return ui.notify("No se pudo leer la ubicación. Marca el lugar otra vez.", type="warning")
                punto = LeafletAdapter.a_marcador(ubicacion)
                if marcador is None:
                    marcador = mapa.marker(latlng=punto)
                else:
                    marcador.move(*punto)
                coords.text = f"Lat {ubicacion.latitud:.5f}, Lng {ubicacion.longitud:.5f}"

            mapa.on("map-click", al_clic)

            def enviar():
                nonlocal enviando
                sesion = require_login()
                if not sesion or sesion["id"] != user["id"] or enviando:
                    return
                if validando_foto:
                    return ui.notify("Espera a que termine de cargar la fotografía.", type="warning")
                if ubicacion is None:
                    return ui.notify("Marca la ubicación del incidente en el mapa.", type="warning")
                try:
                    momento = datetime.strptime(fecha.value, "%Y-%m-%dT%H:%M")
                    datos = IncidenteFactory.crear(tipo.value, desc.value, momento, ubicacion.latitud,
                                                  ubicacion.longitud, zona.value or "")
                except (ValueError, TypeError) as error:
                    return ui.notify(f"Datos inválidos: {error}", type="warning")
                enviando = True
                try:
                    incidentes.reportar(datos, contacto.value or "", user["id"], evidencia)
                except Exception:
                    enviando = False
                    raise
                ui.notify("Incidente reportado. ¡Gracias por cuidar Vinto!", type="positive")
                ui.navigate.to("/incidentes")

            ui.button("Enviar reporte", icon="send", on_click=enviar).props("no-caps unelevated size=lg").classes("self-end")


@ui.page("/incidentes")
def incidentes_page():
    user = require_login()
    if not user:
        return
    frame(user, "/incidentes")
    f = {"tipo": "Todos", "estado": "Todos", "zona": "", "desde": "", "hasta": "", "mios": False}

    @ui.refreshable
    def lista():
        try:
            filtros = FiltrosIncidente.desde_formulario(f["tipo"], f["estado"], f["zona"], f["desde"],
                                                       f["hasta"], user["id"] if f["mios"] else None)
        except (ValueError, OverflowError):
            ui.label("Revisa el rango de fechas. La fecha inicial debe ser anterior o igual a la final.")
            return
        datos = incidentes.listar(filtros)
        if not datos:
            with ui.column().classes("items-center w-full py-10 gap-2"):
                ui.icon("search_off", size="48px").classes("text-blue-300")
                ui.label("No hay incidentes con estos filtros.").classes("text-slate-500")
                ui.button("Reportar un incidente", on_click=lambda: ui.navigate.to("/reportar")).props("no-caps flat")
            return
        with ui.row().classes("w-full gap-4"):
            for inc in datos:
                incident_card(inc)

    def set_f(k):
        def _(e):
            f[k] = e.value
            lista.refresh()
        return _

    with ui.column().classes("w-full max-w-6xl mx-auto gap-4 p-2"):
        ui.label("Incidentes registrados").classes("text-2xl font-extrabold text-blue-900")
        with ui.card().classes("w-full p-4 rounded-xl"):
            with ui.row().classes("w-full items-center gap-3"):
                ui.select(["Todos"] + TIPOS, label="Categoría", value="Todos", on_change=set_f("tipo")) \
                    .props("outlined dense").classes("w-52")
                ui.select(["Todos"] + ESTADOS, label="Estado", value="Todos", on_change=set_f("estado")) \
                    .props("outlined dense").classes("w-44")
                ui.input("Desde", on_change=set_f("desde")).props("outlined dense type=date").classes("w-40")
                ui.input("Hasta", on_change=set_f("hasta")).props("outlined dense type=date").classes("w-40")
                ui.input("Zona", on_change=set_f("zona")).props("outlined dense clearable").classes("w-40")
                ui.switch("Solo mis reportes", on_change=set_f("mios"))
        lista()
