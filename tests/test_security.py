import pytest
from incidentes.security import validate_image_upload


@pytest.mark.parametrize("filename,content,expected", [
    ("foto.jpg", b"\xff\xd8\xff\xe0datos", ".jpg"),
    ("foto.jpeg", b"\xff\xd8\xff\xe0datos", ".jpeg"),
    ("foto.png", b"\x89PNG\r\n\x1a\ncontenido", ".png"),
    ("foto.webp", b"RIFF\x04\x00\x00\x00WEBPcontenido", ".webp"),
])
def test_acepta_firmas_de_imagen_validas(filename, content, expected):
    # Arrange: nombre y contenido que corresponden a un formato permitido.
    # Act: ejecutar la validación.
    resultado = validate_image_upload(filename, content)
    # Assert: devuelve la extensión normalizada.
    assert resultado == expected


@pytest.mark.parametrize("filename,content", [
    ("foto.exe", b"MZcontenido"),
    ("foto.png", b"esto no es un PNG"),
    ("foto.jpg", b""),
])
def test_rechaza_formato_o_contenido_invalido(filename, content):
    with pytest.raises(ValueError):
        validate_image_upload(filename, content)


def test_rechaza_archivo_mayor_al_limite():
    with pytest.raises(ValueError, match="5 MB"):
        validate_image_upload("foto.jpg", b"\xff\xd8\xff" + b"x" * 20, max_bytes=10)
