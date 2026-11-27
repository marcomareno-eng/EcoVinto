from datetime import datetime, timedelta
from types import SimpleNamespace
import pytest
from incidentes.domain import Coordenadas, IncidenteFactory, estadisticas, validar_transicion
from incidentes.adapters import LeafletAdapter

@pytest.fixture
def fecha():
    return datetime(2026, 11, 16, 10, 0)

def test_factory_valida_y_normaliza(fecha):
    resultado = IncidenteFactory.crear('Quema', '  Humo en el barrio  ', fecha, -17.39, -66.31, 'Centro')
    assert resultado.descripcion == 'Humo en el barrio'
    assert resultado.zona == 'Centro'

@pytest.mark.parametrize('tipo,desc,lat,lng', [
    ('Inexistente', 'Un reporte válido', -17.39, -66.31),
    ('Quema', 'Corta', -17.39, -66.31),
    ('Quema', 'Una descripción válida', 100, -66.31),
    ('Quema', 'Una descripción válida', -17.39, float('nan')),
])
def test_factory_rechaza_datos(tipo, desc, lat, lng, fecha):
    with pytest.raises(ValueError):
        IncidenteFactory.crear(tipo, desc, fecha, lat, lng)

def test_transiciones():
    assert validar_transicion('Reportado', 'En revisión')
    assert validar_transicion('En atención', 'En atención')
    assert not validar_transicion('Reportado', 'Cerrado')
    assert not validar_transicion('Cerrado', 'Reportado')

def test_adapter():
    c = LeafletAdapter.desde_evento({'latlng': {'lat': -17.39, 'lng': -66.31}})
    assert c == Coordenadas(-17.39, -66.31)
    assert LeafletAdapter.a_marcador(c) == (-17.39, -66.31)

def test_estadisticas(fecha):
    incs = [SimpleNamespace(zona='Centro', creado=fecha, atendido_en=fecha + timedelta(hours=2)),
            SimpleNamespace(zona='Centro', creado=fecha, atendido_en=None),
            SimpleNamespace(zona='Norte', creado=fecha, atendido_en=fecha + timedelta(hours=4))]
    dato = estadisticas(incs)
    assert dato['total'] == 3
    assert dato['horas_respuesta_media'] == 3
    assert dato['zonas_criticas'][0] == ('Centro', 2)

def test_estadisticas_sin_respuestas():
    assert estadisticas([])['horas_respuesta_media'] is None
