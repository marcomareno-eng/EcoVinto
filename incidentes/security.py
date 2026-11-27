"""Validaciones de seguridad para archivos recibidos desde la interfaz."""

from dataclasses import dataclass
import hashlib
import hmac
from io import BytesIO
import os
from pathlib import Path

from PIL import Image, UnidentifiedImageError


MAX_IMAGE_BYTES = 5_000_000

_IMAGE_SIGNATURES = {
    ".jpg": lambda data: data.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    ".png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    ".webp": lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
}


def validate_image_upload(filename: str, content: bytes, max_bytes: int = MAX_IMAGE_BYTES) -> str:
    """Valida tamaño, extensión y firma básica; devuelve la extensión normalizada."""
    if not isinstance(content, bytes) or not content:
        raise ValueError("El archivo está vacío o no contiene datos válidos.")
    if len(content) > max_bytes:
        raise ValueError("La imagen supera el límite permitido de 5 MB.")

    extension = Path(filename or "").suffix.lower()
    signature_check = _IMAGE_SIGNATURES.get(extension)
    if signature_check is None:
        raise ValueError("Formato no permitido. Usa JPG, PNG o WEBP.")
    if not signature_check(content):
        raise ValueError("El contenido del archivo no coincide con el formato indicado.")
    return extension


EXTENSIONES_IMAGEN = tuple(_IMAGE_SIGNATURES)
_PASSWORD_ITERATIONS = 600_000
_IMAGE_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PASSWORD_ITERATIONS)
    return f"{_PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        parts = stored.split("$")
        if len(parts) == 2:
            salt, expected = parts
            iterations = 200_000
        else:
            rounds, salt, expected = parts
            iterations = int(rounds)
            if iterations != _PASSWORD_ITERATIONS:
                return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iterations)
        return hmac.compare_digest(digest.hex(), expected)
    except ValueError:
        return False


@dataclass(frozen=True)
class Evidencia:
    extension: str
    contenido: bytes

    @classmethod
    def desde_archivo(cls, nombre: str, contenido: bytes) -> "Evidencia":
        extension = validate_image_upload(nombre, contenido)
        try:
            with Image.open(BytesIO(contenido), formats=[_IMAGE_FORMATS[extension]]) as foto:
                if foto.width * foto.height > 20_000_000:
                    raise ValueError("La foto supera el límite de 20 megapíxeles.")
                foto.verify()
            with Image.open(BytesIO(contenido), formats=[_IMAGE_FORMATS[extension]]) as foto:
                foto.load()
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as error:
            raise ValueError("La imagen está dañada o incompleta.") from error
        return cls(extension, contenido)
