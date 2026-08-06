from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

_PERSISTENCE_FILE = ".ius_razon_persistence.json"
_DEFAULT_DEMO_DB = "data/ius_razon_demo.db"


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Configuración inmutable de la aplicación."""

    project_root: Path
    data_dir: Path
    db_path: Path
    upload_dir: Path
    log_dir: Path
    max_upload_bytes: int
    log_level: str

    @classmethod
    def from_env(cls, project_root: Path | None = None) -> AppConfig:
        """Construye la configuración y conserva la ubicación de persistencia.

        La precedencia es:
        1. Variables de entorno explícitas.
        2. Ubicación persistida en ``.ius_razon_persistence.json``.
        3. Base local existente con expedientes.
        4. ``data/ius_razon.db``.
        """

        root = (project_root or Path.cwd()).resolve()
        state_path = root / _PERSISTENCE_FILE
        demo_mode = cls._parse_boolean(
            os.getenv("IUS_RAZON_DEMO_MODE", "false"),
            variable_name="IUS_RAZON_DEMO_MODE",
        )
        saved = {} if demo_mode else cls._load_saved_persistence(state_path)

        raw_db_path = os.getenv("IUS_RAZON_DB_PATH")
        if demo_mode:
            demo_db_path = os.getenv("IUS_RAZON_DEMO_DB_PATH", _DEFAULT_DEMO_DB)
            db_path = cls._resolve_path(root, demo_db_path)
        elif raw_db_path:
            db_path = cls._resolve_path(root, raw_db_path)
        elif isinstance(saved.get("db_path"), str):
            db_path = cls._resolve_path(root, str(saved["db_path"]))
        else:
            db_path = cls._discover_existing_db(root) or (root / "data" / "ius_razon.db")

        raw_data_dir = os.getenv("IUS_RAZON_DATA_DIR")
        if demo_mode:
            data_dir = db_path.parent
        elif raw_data_dir:
            data_dir = cls._resolve_path(root, raw_data_dir)
        elif raw_db_path:
            data_dir = db_path.parent
        elif isinstance(saved.get("data_dir"), str):
            data_dir = cls._resolve_path(root, str(saved["data_dir"]))
        else:
            data_dir = db_path.parent

        max_upload_mb = cls._parse_positive_int(
            os.getenv("IUS_RAZON_MAX_UPLOAD_MB", "10"),
            variable_name="IUS_RAZON_MAX_UPLOAD_MB",
        )
        log_level = os.getenv("IUS_RAZON_LOG_LEVEL", "INFO").upper().strip()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("IUS_RAZON_LOG_LEVEL contiene un nivel inválido.")

        upload_dir = data_dir / "uploads"
        log_dir = data_dir / "logs"
        for directory in (data_dir, upload_dir, log_dir, db_path.parent):
            directory.mkdir(parents=True, exist_ok=True)

        if demo_mode:
            cls._ensure_demo_database(db_path)
        else:
            cls._save_persistence(
                state_path,
                {
                    "db_path": str(db_path.resolve()),
                    "data_dir": str(data_dir.resolve()),
                },
            )

        return cls(
            project_root=root,
            data_dir=data_dir,
            db_path=db_path,
            upload_dir=upload_dir,
            log_dir=log_dir,
            max_upload_bytes=max_upload_mb * 1024 * 1024,
            log_level=log_level,
        )

    @staticmethod
    def _resolve_path(root: Path, raw_path: str) -> Path:
        candidate = Path(raw_path).expanduser()
        return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()

    @staticmethod
    def _parse_boolean(raw_value: str, variable_name: str) -> bool:
        normalized = raw_value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(
            f"{variable_name} debe usar true/false, 1/0, yes/no u on/off."
        )

    @staticmethod
    def _parse_positive_int(raw_value: str, variable_name: str) -> int:
        try:
            parsed = int(raw_value)
        except ValueError as exc:
            raise ValueError(f"{variable_name} debe ser un entero.") from exc
        if parsed <= 0:
            raise ValueError(f"{variable_name} debe ser mayor que cero.")
        return parsed

    @staticmethod
    def _load_saved_persistence(state_path: Path) -> dict[str, Any]:
        if not state_path.exists():
            return {}
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _save_persistence(state_path: Path, payload: dict[str, str]) -> None:
        try:
            state_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            LOGGER.warning("No fue posible persistir la ubicación de datos: %s", exc)

    @classmethod
    def _ensure_demo_database(cls, db_path: Path) -> None:
        """Crea o repara la base pública sintética sin tocar la persistencia local."""

        if cls._case_count(db_path) > 0:
            return

        from ius_razon.demo_database import build_demo_database

        build_demo_database(db_path, force=db_path.exists())

    @classmethod
    def _discover_existing_db(cls, root: Path) -> Path | None:
        """Localiza una base previa dentro del proyecto sin modificarla."""

        candidates = {
            root / "data" / "ius_razon.db",
            root / "data_test" / "ius_razon_test.db",
        }
        for directory in root.glob("data*"):
            if directory.is_dir():
                candidates.update(directory.glob("*.db"))

        existing = [path.resolve() for path in candidates if path.is_file()]
        if not existing:
            return None

        return max(
            existing,
            key=lambda path: (
                cls._case_count(path),
                path.stat().st_mtime,
                path.stat().st_size,
            ),
        )

    @staticmethod
    def _case_count(db_path: Path) -> int:
        """Devuelve el número de expedientes; una base inválida puntúa cero."""

        try:
            connection = sqlite3.connect(db_path)
            try:
                row = connection.execute(
                    "SELECT COUNT(*) FROM cases"
                ).fetchone()
            finally:
                connection.close()
        except sqlite3.Error:
            return 0
        return int(row[0]) if row else 0
