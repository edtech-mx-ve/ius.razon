from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from ius_razon.config import AppConfig


def configure_logging(config: AppConfig) -> None:
    """Configura bitácora técnica sin incluir contenido de expedientes."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    root_logger.setLevel(config.log_level)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        config.log_dir / "ius_razon.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console)
    root_logger.addHandler(file_handler)
