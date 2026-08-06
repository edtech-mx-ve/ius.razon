# Instrucciones del parche — Sprint 3.2 v0.3.4

## Origen compatible

Aplicar sobre IUS-Razón v0.3.3.

## Contenido

El parche actualiza:

```text
app.py
pyproject.toml
README.md
src/ius_razon/__init__.py
src/ius_razon/domain/reasoning_models.py
src/ius_razon/services/reasoning_engine.py
src/ius_razon/services/reasoning_service.py
tests/test_reasoning_engine.py
tests/test_sprint_32.py
CHANGELOG_v0.3.4.md
SPRINT_3_2_REPORT.md
docs/SPRINT_3_2_TEST_GUIDE.md
PATCH_INSTRUCTIONS_v0.3.4.md
```

No contiene bases de datos, cargas, respaldos ni logs.

## Implementación

Detén Streamlit presionando físicamente `Ctrl + C`.

Desde la raíz del proyecto:

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint32.bak" -Force
}
```

Coloca el ZIP en la raíz y ejecuta:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_3_2_patch_v0.3.4.zip `
    -DestinationPath . `
    -Force
```

Reinstala:

```powershell
python -m pip install -e ".[dev]"
```

Confirma la versión:

```powershell
python -c "from importlib.metadata import version; import ius_razon; print(version('ius-razon')); print(ius_razon.__version__); print(ius_razon.__file__)"
```

Esperado:

```text
0.3.4
0.3.4
<ruta del proyecto>\src\ius_razon\__init__.py
```

Confirma la base activa:

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
```

Debe seguir terminando en:

```text
data_test\ius_razon_test.db
```

Valida:

```powershell
ruff check .
mypy src
pytest -v
```

Esperado:

```text
All checks passed!
Success: no issues found in 17 source files
42 passed
```

Arranca:

```powershell
streamlit run app.py
```

URL:

```text
http://localhost:8501
```

## Validación funcional mínima

1. abre `Reglas`;
2. crea una regla rival con la misma clave de conclusión y valor opuesto;
3. asigna prioridad mayor que la regla original;
4. ejecuta la inferencia;
5. verifica una regla aplicada y otra derrotada;
6. iguala prioridad, tipo y especificidad;
7. verifica empate y suspensión de la conclusión;
8. restaura o desactiva la regla de prueba.

## Reversión

Detén Streamlit y restaura los archivos desde una copia del proyecto anterior.
La base no necesita reversión porque el parche no cambia el esquema.

Las nuevas ejecuciones creadas con motor `3.2.0` pueden conservarse. Si se
restaura el código anterior, solo se mostrarán como ejecuciones históricas.

## Seguridad

No expongas la URL de red local directamente a Internet. Para pruebas
compartidas, usa un despliegue controlado y datos sintéticos.
