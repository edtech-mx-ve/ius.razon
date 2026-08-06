# Instrucciones del parche v0.4.2

## Requisitos

- proyecto IUS-Razón v0.4.1;
- entorno virtual activo;
- base SQLite respaldada;
- parche ubicado en la raíz del proyecto.

## 1. Detener la aplicación

Presiona físicamente:

```text
Ctrl + C
```

No escribas `Ctrl+C` como comando.

## 2. Respaldo

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint42.bak" -Force
}

Copy-Item .\app.py .\app.py.pre-sprint42.bak -Force
```

## 3. Aplicar el parche

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_2_patch_v0.4.2.zip `
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
Instalada: 0.4.2
Módulo: 0.4.2
Ruta: ...\src\ius_razon\__init__.py
```

## 6. Confirmar base

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
```

La ruta debe seguir terminando en:

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
66 passed
```

## 8. Iniciar

```powershell
streamlit run app.py
```

URL:

```text
http://localhost:8501
```

## Compatibilidad

El parche no modifica el esquema SQLite. No elimina ni transforma datos
existentes.

## Restauración

Si la aplicación no inicia:

```powershell
Copy-Item .\app.py.pre-sprint42.bak .\app.py -Force
```

Para restaurar la base, copia el archivo `.pre-sprint42.bak` sobre la base activa
solo después de detener Streamlit.
