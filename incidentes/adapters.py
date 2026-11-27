"""Adapter de geolocalización: el dominio no depende del componente Leaflet."""
from .domain import Coordenadas

class LeafletAdapter:
    @staticmethod
    def desde_evento(event_args: dict) -> Coordenadas:
        latlng = event_args['latlng']
        return Coordenadas(float(latlng['lat']), float(latlng['lng']))

    @staticmethod
    def a_marcador(coordenadas: Coordenadas) -> tuple[float, float]:
        return coordenadas.latitud, coordenadas.longitud
