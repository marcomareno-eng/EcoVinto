# Demostración de EcoVinto

Prepara una instancia con las instrucciones del README y usa cuentas y datos de demostración. Abre dos sesiones separadas, por ejemplo una ventana normal para el vecino y otra de incógnito para el administrador.

| Paso | Acción | Resultado esperado |
|---|---|---|
| 1 | Inicia sesión como vecino o crea una cuenta desde `/registro`. Visita `/admin`. | La app redirige a los incidentes. |
| 2 | Abre **Reportar incidente** y llena categoría, descripción, fecha y zona. Adjunta un JPG, PNG o WebP y marca la ubicación en el mapa. | La interfaz confirma el adjunto y muestra un marcador y sus coordenadas. |
| 3 | Envía el reporte. Prueba **Zona**, **Estado** y **Solo mis reportes**. | La tarjeta conserva la descripción y la fotografía tras recargar. |
| 4 | Entra como administrador y abre el detalle desde **Gestión de incidentes**. | Aparecen la foto, la ubicación y los datos de contacto. |
| 5 | Prueba saltar a **Cerrado**. Después avanza a **En revisión** y a **En atención** con un responsable. Completa **Atendido** y **Cerrado**. | El sistema rechaza el salto y conserva el responsable al cerrar. |
| 6 | Abre **Resumen** y **Usuarios**. | El panel refleja categoría, estado, zona y tiempo medio. El administrador puede gestionar roles. |
| 7 | Ejecuta `python -m pytest -q`. | Pytest muestra el resultado de las pruebas unitarias y de integración. |

Para la defensa, explica qué valida el Factory, qué convierte el Adapter de Leaflet, dónde vive la transición de estados y cómo los servicios reciben sus repositorios por constructor. La media de respuesta mide desde la creación del reporte hasta su primer cambio a **Atendido**.
