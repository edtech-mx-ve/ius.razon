# Implementación — IUS-Razón Sprint 4.2.1 v0.4.4

## Entorno

- Windows PowerShell
- Python 3.11 o superior
- entorno virtual activo
- proyecto IUS-Razón v0.4.3

## 1. Detener la aplicación

Presiona físicamente `Ctrl + C` en la terminal donde corre Streamlit.

## 2. Respaldar

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint421.bak" -Force
}

Copy-Item .\app.py .\app.py.pre-sprint421.bak -Force
```

## 3. Aplicar el parche

Coloca `IUS_Razon_Sprint_4_2_1_patch_v0.4.4.zip` en la raíz:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_2_1_patch_v0.4.4.zip `
    -DestinationPath . `
    -Force

python -m pip install -e ".[dev]"
```

## 4. Verificar versión

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Resultado esperado:

```text
Instalada: 0.4.4
Módulo: 0.4.4
Ruta: ...\src\ius_razon\__init__.py
```

## 5. Confirmar base activa

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
```

Si la variable está vacía:

```powershell
$db = Join-Path (Get-Location) "data_test\ius_razon_test.db"

if (-not (Test-Path $db)) {
    throw "No se encontró la base esperada: $db"
}

$env:IUS_RAZON_DB_PATH = (Resolve-Path $db).Path
Write-Host $env:IUS_RAZON_DB_PATH
```

## 6. Validar

```powershell
ruff check .
mypy src
pytest -v
```

Resultado esperado:

```text
All checks passed!
Success: no issues found
70 passed
```

## 7. Ejecutar

```powershell
streamlit run app.py
```

URL esperada:

```text
http://localhost:8501
```

## 8. Validación funcional

Genera nuevamente el informe integral de `PJ-001`.

Resultado esperado:

- versión del informe `4.2.1`;
- `ARG-003` identificado como argumento manual;
- ausencia del falso vacío «falta conclusión inferida»;
- concordancia correcta en hallazgos;
- puntuación simple en vínculos hecho–prueba;
- exportaciones JSON, Markdown y DOCX disponibles.

## Reversión

```powershell
Copy-Item .\app.py.pre-sprint421.bak .\app.py -Force
```

Restaura la copia `.pre-sprint421.bak` de la base solo si se produjo un problema
ajeno al parche. El parche no modifica el esquema SQLite.
