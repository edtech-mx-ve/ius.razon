# Aplicación del hotfix v0.4.3

Desde la raíz del proyecto, con el entorno virtual activo:

```powershell
Copy-Item .\app.py .\app.py.pre-v043.bak -Force

Expand-Archive `
    .\IUS_Razon_Sprint_4_2_hotfix_v0.4.3.zip `
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
Success: no issues found
66 passed
```
