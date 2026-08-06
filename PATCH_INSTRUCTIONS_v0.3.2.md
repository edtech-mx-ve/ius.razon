# Instrucciones del parche v0.3.2

## Alcance

Este parche actualiza IUS-Razón v0.3.1 a Sprint 3.1 v0.3.2. No contiene bases
de datos, archivos cargados ni información del usuario.

## Aplicación en Windows PowerShell

Detén Streamlit:

```powershell
Ctrl+C
```

Desde la raíz del proyecto, respalda todas las bases:

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint31.bak" -Force
}
```

Aplica el parche:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_3_1_patch_v0.3.2.zip `
    -DestinationPath . `
    -Force
```

Reinstala:

```powershell
python -m pip install -e ".[dev]"
```

Verifica la base activa:

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
```

Ejecuta:

```powershell
pytest -v
ruff check .
mypy src
```

Resultado esperado:

```text
34 passed
All checks passed!
Success: no issues found
```

Arranca:

```powershell
streamlit run app.py
```

URL:

```text
http://localhost:8501
```

## Migración automática

Al iniciar, se crean:

```text
reasoning_assertion_versions
reasoning_rule_versions
reasoning_runs.input_snapshot_json
```

Las ejecuciones antiguas conservan su huella y muestran que no tienen
instantánea completa. Las ejecuciones nuevas sí conservan la entrada completa.

## Reversión

1. detén Streamlit;
2. conserva una copia del estado actual;
3. restaura la base `.pre-sprint31.bak`;
4. reaplica el paquete v0.3.1;
5. reinstala dependencias.

No mezcles una base editada con v0.3.2 y un código antiguo sin restaurar el
respaldo correspondiente.
