# Aplicación del parche Sprint 3 v0.3.0

## 1. Detener

```powershell
Ctrl+C
```

## 2. Respaldar

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint3.bak" -Force
}
```

## 3. Aplicar

Coloca `IUS_Razon_Sprint_3_patch_v0.3.0.zip` en la raíz del proyecto.

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_3_patch_v0.3.0.zip `
    -DestinationPath . `
    -Force
```

## 4. Reinstalar

```powershell
python -m pip install -e ".[dev]"
```

## 5. Verificar base

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
```

## 6. Validar

```powershell
pytest -v
ruff check .
mypy src
```

Resultado esperado:

```text
28 passed
All checks passed!
Success: no issues found
```

## 7. Ejecutar

```powershell
streamlit run app.py
```

URL:

```text
http://localhost:8501
```

El parche no contiene `data`, `data_test`, archivos cargados ni bases SQLite.
