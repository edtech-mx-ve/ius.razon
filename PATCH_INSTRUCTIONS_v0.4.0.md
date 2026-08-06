# Instrucciones del parche v0.4.0

## Requisito

Proyecto IUS-Razón v0.3.4 instalado y base activa confirmada.

## Implementación

Detén Streamlit presionando físicamente `Ctrl + C`.

Desde la raíz del proyecto:

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint4.bak" -Force
}

Expand-Archive `
    .\IUS_Razon_Sprint_4_patch_v0.4.0.zip `
    -DestinationPath . `
    -Force

python -m pip install -e ".[dev]"

python -c "from importlib.metadata import version; import ius_razon; print(version('ius-razon')); print(ius_razon.__version__); print(ius_razon.__file__)"

Write-Host $env:IUS_RAZON_DB_PATH

ruff check .
mypy src
pytest -v

streamlit run app.py
```

## Resultado esperado

```text
Versión instalada: 0.4.0
Versión del módulo: 0.4.0
All checks passed!
Success: no issues found
50 passed
Local URL: http://localhost:8501
```

## Migración

Al iniciar se crean, si no existen:

```text
legal_arguments
argument_relations
argument_sequences
```

No se eliminan ni reemplazan tablas anteriores.

## Reversión

1. Detén Streamlit.
2. Conserva una copia de la base actual.
3. Restaura el código v0.3.4.
4. Restaura la base `.pre-sprint4.bak` solo cuando necesites eliminar también
   los registros argumentales creados con Sprint 4.
