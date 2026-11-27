# EcoVinto

Sistema web para reportar y dar seguimiento a incidentes ambientales en el municipio de Vinto, Cochabamba. Proyecto de Taller de Programación de la Universidad Adventista de Bolivia.

- **Vecino:** registro, inicio de sesión, reporte con ubicación y fotografía opcional, consulta por categoría, estado, fechas, zona y autor.
- **Administrador:** panel de indicadores, mapa de reportes, asignación de responsables, gestión de estados y roles.
- **Tecnología:** Python, NiceGUI, SQLModel, SQLite, Leaflet y Docker Compose.

## Ejecutar en Windows con VS Code

Abre la carpeta `ecovinto` o la raíz del repositorio. Desde PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Pega el valor generado en `SECRET_KEY` en `.env` y define `ADMIN_PASSWORD` con al menos 12 caracteres. Luego ejecuta:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe main.py
```

Abre [http://127.0.0.1:8080](http://127.0.0.1:8080). El correo del administrador es el de `ADMIN_EMAIL`. Usa la contraseña configurada en el primer arranque. Los vecinos crean su cuenta en `/registro`. Si el puerto está ocupado, cambia `PORT` en `.env` y abre el puerto correspondiente.

En Linux y macOS, usa `python3 -m venv .venv`, `.venv/bin/python` y `cp .env.example .env` para los mismos pasos.

## Ejecutar con Docker

Crea y completa `.env` como arriba. Ejecuta:

```sh
docker compose up -d --build --wait
docker compose ps
docker compose logs ecovinto
```

Abre [http://127.0.0.1:8080](http://127.0.0.1:8080). Si el puerto está ocupado, ajusta `APP_PORT` en `.env`. Compose conserva la base, las fotos y las sesiones en el volumen `ecovinto_data`. `docker compose down` detiene la aplicación y conserva el volumen. El chequeo de salud consulta `/healthz` y ejecuta una consulta SQLite.

## Datos y permisos

Haz una copia de `data/` o del volumen antes de actualizar una instalación previa. EcoVinto añade las columnas `zona` y `atendido_en` si faltan y conserva los registros. Si la instalación conservaba la contraseña inicial antigua, el arranque exige una nueva en `ADMIN_PASSWORD`. En las demás cuentas administrativas existentes se conserva su contraseña guardada.

Las fotos se consultan con una sesión iniciada. Los datos de contacto del reporte aparecen en el detalle administrativo. Leaflet requiere acceso a OpenStreetMap para mostrar el mapa base. Si alojas la aplicación fuera del equipo, configura HTTPS y `SESSION_SECURE=true`.

## Entrega

- [Arquitectura, requisitos, pruebas y bitácora de Vibe Coding](docs/ENTREGA.md)
- [Guía de demostración](GUIA_DEMO_Y_CAPTURAS.md)
