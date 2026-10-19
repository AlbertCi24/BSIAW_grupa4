"""Przechowywanie plakatów.

LocalStorage zapisuje pliki na dysku. Za load balancerem z kilkoma instancjami
dysk nie jest wspólny, więc w chmurze trzeba podmienić tę klasę na storage
obiektowy (S3, GCS) z tymi samymi metodami: save, delete, send.
"""

import io
import os
import re
import uuid

from flask import abort, send_from_directory
from PIL import Image, UnidentifiedImageError

# Format wykryty z zawartości pliku -> rozszerzenie, pod którym go zapisujemy.
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
MAX_DIMENSIONS = (1000, 1500)
FILENAME_RE = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp)$")


class InvalidImage(ValueError):
    pass


def sanitize_image(stream):
    """Sprawdza, czy plik jest obrazkiem, i koduje go od nowa.

    Rozszerzenie i nazwa od użytkownika są ignorowane. Ponowne zakodowanie
    usuwa metadane i doklejone do obrazka dane (np. pliki poliglotyczne).
    """
    try:
        with Image.open(stream) as img:
            image_format = img.format
            if image_format not in ALLOWED_FORMATS:
                raise InvalidImage("Dozwolone formaty: JPG, PNG, WEBP.")
            img.load()
            img.thumbnail(MAX_DIMENSIONS)
            if image_format == "JPEG" and img.mode != "RGB":
                img = img.convert("RGB")
            elif img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            out = io.BytesIO()
            img.save(out, format=image_format)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise InvalidImage("Plik nie jest poprawnym obrazkiem.") from exc
    return out.getvalue(), ALLOWED_FORMATS[image_format]


class LocalStorage:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def save(self, data, extension):
        filename = f"{uuid.uuid4().hex}.{extension}"
        with open(os.path.join(self.folder, filename), "wb") as f:
            f.write(data)
        return filename

    def delete(self, filename):
        if filename and FILENAME_RE.match(filename):
            try:
                os.remove(os.path.join(self.folder, filename))
            except FileNotFoundError:
                pass

    def send(self, filename):
        if not FILENAME_RE.match(filename):
            abort(404)
        return send_from_directory(self.folder, filename)
