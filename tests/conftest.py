from __future__ import annotations

from pathlib import Path

import pytest

from ius_razon.config import AppConfig
from ius_razon.persistence.sqlite_repository import SQLiteRepository
from ius_razon.services.case_service import CaseService


@pytest.fixture
def service(tmp_path: Path) -> CaseService:
    data_dir = tmp_path / "data"
    config = AppConfig(
        project_root=tmp_path,
        data_dir=data_dir,
        db_path=data_dir / "test.db",
        upload_dir=data_dir / "uploads",
        log_dir=data_dir / "logs",
        max_upload_bytes=1024 * 1024,
        log_level="INFO",
    )
    config.upload_dir.mkdir(parents=True)
    config.log_dir.mkdir(parents=True)
    repository = SQLiteRepository(config.db_path)
    repository.initialize()
    return CaseService(repository=repository, config=config)
