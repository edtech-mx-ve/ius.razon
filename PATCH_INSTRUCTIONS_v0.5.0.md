# Instrucciones del parche — IUS-Razón Sprint 4.3 v0.5.0

## 1. Detener la aplicación

Presiona físicamente `Ctrl + C` en la terminal donde corre Streamlit.

## 2. Confirmar ubicación

```powershell
Get-Location
Test-Path .\app.py
Test-Path .\pyproject.toml
Test-Path .\.venv\Scripts\python.exe
```

Los tres resultados deben ser `True`.

## 3. Activar el entorno

```powershell
.\.venv\Scripts\Activate.ps1
```

## 4. Respaldar bases SQLite

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item `
        $_.FullName `
        "$($_.FullName).pre-sprint43.bak" `
        -Force
}
```

## 5. Aplicar el parche

Copia `IUS_Razon_Sprint_4_3_patch_v0.5.0.zip` a la raíz y ejecuta:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_3_patch_v0.5.0.zip `
    -DestinationPath . `
    -Force
```

## 6. Reinstalar metadatos editables

```powershell
python -m pip install `
    -e . `
    --no-deps `
    --no-cache-dir `
    --force-reinstall
```

## 7. Verificar versión

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Esperado:

```text
Instalada: 0.5.0
Módulo: 0.5.0
Ruta: ...\src\ius_razon\__init__.py
```

## 8. Calidad

```powershell
ruff check .
mypy src
pytest -v
```

Esperado:

```text
All checks passed!
Success: no issues found
82 passed
```

## 9. Iniciar

```powershell
streamlit run app.py
```

URL:

```text
http://localhost:8501
```

La primera ejecución aplica una migración aditiva y crea:

```text
llm_draft_sequences
llm_drafts
```

## 10. Validación funcional

Abre `Asistente IA`, genera un resumen con anonimización activada y aprueba
el texto sin quitar sus referencias. Confirma cobertura `100 %`, estado
`Aprobado` e historial persistido.

## Recuperación

Detén Streamlit y restaura la base elegida:

```powershell
Copy-Item `
    .\data_test\ius_razon_test.db.pre-sprint43.bak `
    .\data_test\ius_razon_test.db `
    -Force
```

Después restaura el código desde Git o desde el paquete completo anterior.
