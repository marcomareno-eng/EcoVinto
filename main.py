from incidentes.config import HOST, PORT, SECRET_KEY, SESSION_SECURE, UPLOAD_DIR

from fastapi import HTTPException
from fastapi.responses import FileResponse
from nicegui import app, ui
from sqlalchemy import text

from incidentes.auth import current_user
from incidentes.database import engine, init_admin, init_db
from incidentes.dependencies import incidentes
from incidentes.pages import admin, auth_pages, citizen  # noqa: F401  (registran las rutas)


@app.get("/healthz")
def health():
    with engine.connect() as conexion:
        conexion.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/uploads/{filename}")
def foto(filename: str):
    if current_user() is None:
        raise HTTPException(status_code=401)
    path = incidentes.foto(filename)
    if path is None:
        raise HTTPException(status_code=404)
    return FileResponse(path, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


if __name__ in {"__main__", "__mp_main__"}:
    if len(SECRET_KEY) < 32 or SECRET_KEY.startswith("cambia-esta-clave"):
        raise SystemExit("Configura SECRET_KEY con un valor aleatorio de al menos 32 caracteres.")
    init_db()
    init_admin()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ui.run(host=HOST, port=PORT, title="EcoVinto · Incidentes ambientales", favicon="💧",
           storage_secret=SECRET_KEY,
           session_middleware_kwargs={"https_only": SESSION_SECURE}, reload=False, show=False)
