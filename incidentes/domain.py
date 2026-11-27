"""Reglas de negocio independientes de NiceGUI y de la base de datos (SRP)."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from math import isfinite

TIPOS_VALIDOS = ('Acumulación de basura', 'Contaminación de ríos', 'Quema',
                 'Contaminación del aire', 'Botadero clandestino', 'Tala de árboles',
                 'Vertido ilegal', 'Otro')
ESTADOS_VALIDOS = ('Reportado', 'En revisión', 'En atención', 'Atendido', 'Cerrado')

@dataclass(frozen=True)
class Coordenadas:
    latitud: float
    longitud: float

    def __post_init__(self):
        if not (isfinite(self.latitud) and isfinite(self.longitud)
                and -90 <= self.latitud <= 90 and -180 <= self.longitud <= 180):
            raise ValueError('Coordenadas fuera de rango')

@dataclass(frozen=True)
class DatosIncidente:
    tipo: str
    descripcion: str
    fecha: datetime
    coordenadas: Coordenadas
    zona: str = ''

@dataclass(frozen=True)
class FiltrosIncidente:
    tipo: str = ""
    estado: str = ""
    zona: str = ""
    desde: datetime | None = None
    hasta: datetime | None = None
    user_id: int | None = None

    @classmethod
    def desde_formulario(cls, tipo: str, estado: str, zona: str, desde: str, hasta: str,
                         user_id: int | None) -> "FiltrosIncidente":
        inicio = date.fromisoformat(desde) if desde else None
        fin = date.fromisoformat(hasta) if hasta else None
        if inicio and fin and inicio > fin:
            raise ValueError("La fecha inicial debe ser anterior o igual a la final.")
        return cls(
            tipo=tipo if tipo in TIPOS_VALIDOS else "",
            estado=estado if estado in ESTADOS_VALIDOS else "",
            zona=(zona or "").strip(),
            desde=datetime.combine(inicio, time.min) if inicio else None,
            hasta=datetime.combine(fin + timedelta(days=1), time.min) if fin else None,
            user_id=user_id,
        )


class IncidenteFactory:
    """Factory: centraliza la creación/validación de datos de incidentes (OCP)."""
    @staticmethod
    def crear(tipo: str, descripcion: str, fecha: datetime,
              latitud: float, longitud: float, zona: str = '') -> DatosIncidente:
        if tipo not in TIPOS_VALIDOS:
            raise ValueError('Categoría no permitida')
        if len((descripcion or '').strip()) < 10:
            raise ValueError('La descripción requiere al menos 10 caracteres')
        if not isinstance(fecha, datetime):
            raise ValueError('Fecha inválida')
        if len((zona or '').strip()) > 100:
            raise ValueError('Zona demasiado larga')
        return DatosIncidente(tipo, descripcion.strip(), fecha,
                              Coordenadas(float(latitud), float(longitud)), zona.strip())

def validar_transicion(origen: str, destino: str) -> bool:
    """Transición hacia el siguiente estado o permanencia; sin saltos ni retrocesos."""
    if origen not in ESTADOS_VALIDOS or destino not in ESTADOS_VALIDOS:
        return False
    return ESTADOS_VALIDOS.index(destino) - ESTADOS_VALIDOS.index(origen) in (0, 1)

def estadisticas(incidentes):
    """Resumen sin dependencia de ORM, fácil de probar con dobles de prueba."""
    from collections import Counter
    datos = list(incidentes)
    por_zona = Counter((getattr(i, 'zona', '') or 'Sin zona') for i in datos)
    respuestas = [(i.atendido_en - i.creado).total_seconds() / 3600
                  for i in datos if getattr(i, 'atendido_en', None) is not None
                  and getattr(i, 'creado', None) is not None
                  and i.atendido_en >= i.creado]
    return {'total': len(datos),
            'horas_respuesta_media': round(sum(respuestas) / len(respuestas), 2) if respuestas else None,
            'zonas_criticas': por_zona.most_common(5)}
