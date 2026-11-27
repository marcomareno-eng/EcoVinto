import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/incidentes.db")
SECRET_KEY = os.getenv("SECRET_KEY", "")
SESSION_SECURE = os.getenv("SESSION_SECURE", "false").lower() == "true"
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
ADMIN_NAME = os.getenv("ADMIN_NAME", "Administrador")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@vinto.gob.bo")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
MAP_LAT = float(os.getenv("MAP_LAT", "-17.3833"))
MAP_LNG = float(os.getenv("MAP_LNG", "-66.3167"))

