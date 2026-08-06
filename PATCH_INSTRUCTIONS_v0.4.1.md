# Instrucciones del parche IUS-Razón v0.4.1

## Requisito

Proyecto instalado en IUS-Razón `0.4.0` con la base activa definida mediante:

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
```

## 1. Detener la aplicación

Presiona físicamente:

```text
Ctrl + C
```

No escribas `Ctrl+C` como comando.

## 2. Respaldo adicional

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint41.bak" -Force
}
```

Respalda también la interfaz actual:

```powershell
Copy-Item .\app.py .\app.py.pre-sprint41.bak -Force
```

## 3. Aplicar el parche

Coloca `IUS_Razon_Sprint_4_1_patch_v0.4.1.zip` en la raíz del proyecto:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_1_patch_v0.4.1.zip `
    -DestinationPath . `
    -Force
```

## 4. Reinstalar

```powershell
python -m pip install -e ".[dev]"
```

## 5. Verificar versión

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Resultado esperado:

```text
Instalada: 0.4.1
Módulo: 0.4.1
Ruta: ...\src\ius_razon\__init__.py
```

## 6. Confirmar base activa

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
```

Debe seguir terminando en:

```text
data_test\ius_razon_test.db
```

## 7. Validar

```powershell
ruff check .
mypy src
pytest -v
```

Resultado esperado:

```text
All checks passed!
Success: no issues found
58 passed
```

## 8. Iniciar

```powershell
streamlit run app.py
```

URL:

```text
http://localhost:8501
```

## Migración

Al iniciar, se crea de forma aditiva:

```text
argument_scenarios
idx_argument_scenarios_case
```

No se eliminan ni reemplazan datos existentes.

## Recuperación

Si la interfaz no inicia:

```powershell
Copy-Item `
    .\app.py.pre-sprint41.bak `
    .\app.py `
    -Force
```

La restauración de la base solo debe realizarse con Streamlit detenido y usando
el respaldo creado antes de aplicar el parche.
