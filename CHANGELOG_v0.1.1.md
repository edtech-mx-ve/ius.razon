# IUS-Razón v0.1.1 — Correcciones de calidad

## Cambios

1. `app.py`
   - Se eliminaron `os`, `sys` y la modificación manual de `sys.path`.
   - Las importaciones del paquete quedaron en el nivel superior.
   - La ejecución requiere instalar el proyecto en modo editable.

2. `config.py`
   - `AppConfig.from_env()` retorna `AppConfig` sin anotación entre comillas.

3. `domain/enums.py`
   - Los enumerados ahora heredan de `enum.StrEnum`.

4. `domain/models.py`
   - Se eliminó `field_validator`, que no se utilizaba.
   - `utc_now()` utiliza `datetime.UTC`.

5. `persistence/sqlite_repository.py`
   - `Iterator` se importa desde `collections.abc`.

6. `services/case_service.py`
   - Se ajustó una línea para respetar el límite de 100 caracteres.

7. `pyproject.toml`
   - Versión actualizada a `0.1.1`.

## Compatibilidad

No se modificó el esquema SQLite ni la lógica de negocio. Los expedientes generados con
v0.1.0 pueden utilizarse con v0.1.1.

## Instalación

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest -v
ruff check .
mypy src
streamlit run app.py
```
