# Aplicación del hotfix v0.3.3

Desde la raíz del proyecto en PowerShell:

```powershell
Ctrl+C

Copy-Item `
    .\src\ius_razon\persistence\reasoning_repository.py `
    .\src\ius_razon\persistence\reasoning_repository.py.pre-v033.bak `
    -Force

Expand-Archive `
    .\IUS_Razon_Sprint_3_1_hotfix_v0.3.3.zip `
    -DestinationPath . `
    -Force

python -m pip install -e ".[dev]"

ruff check .
mypy src
pytest -v

streamlit run app.py
```

Resultado esperado:

```text
All checks passed!
Success: no issues found in 17 source files
34 passed
```
