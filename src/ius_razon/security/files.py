from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".png", ".jpg", ".jpeg"}


@dataclass(frozen=True, slots=True)
class StoredFile:
    original_name: str
    stored_name: str
    path: Path
    sha256: str
    size: int


def sanitize_file_name(original_name: str) -> str:
    """Obtiene un nombre visible seguro sin conservar rutas proporcionadas por el cliente."""
    base_name = Path(original_name).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base_name).strip("._")
    if not cleaned:
        raise ValueError("El archivo no tiene un nombre válido.")
    return cleaned[:180]


def store_uploaded_file(
    *,
    case_id: str,
    original_name: str,
    content: bytes,
    upload_root: Path,
    max_size_bytes: int,
) -> StoredFile:
    """Valida y almacena un archivo sin ejecutar ni interpretar su contenido."""
    if not content:
        raise ValueError("El archivo está vacío.")
    if len(content) > max_size_bytes:
        raise ValueError("El archivo excede el tamaño máximo permitido.")

    safe_original = sanitize_file_name(original_name)
    extension = Path(safe_original).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extensión no permitida: {extension or 'sin extensión'}.")

    case_dir = (upload_root / case_id).resolve()
    upload_root_resolved = upload_root.resolve()
    if upload_root_resolved not in case_dir.parents:
        raise ValueError("Ruta de expediente inválida.")

    case_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    target = (case_dir / stored_name).resolve()
    if case_dir not in target.parents:
        raise ValueError("Ruta de archivo inválida.")

    digest = hashlib.sha256(content).hexdigest()
    target.write_bytes(content)

    return StoredFile(
        original_name=safe_original,
        stored_name=stored_name,
        path=target,
        sha256=digest,
        size=len(content),
    )
