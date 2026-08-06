# Instrucciones del parche — IUS-Razón v0.6.0

## 1. Punto de partida

Debe estar en:

```text
Rama: feature/sprint-4.4
Versión: 0.5.1
Estado Git: limpio
```

## 2. Detener la aplicación

Presiona físicamente `Ctrl + C`.

## 3. Aplicar el parche

Coloca `IUS_Razon_Sprint_4_4_patch_v0.6.0.zip` en la raíz y ejecuta:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_4_patch_v0.6.0.zip `
    -DestinationPath . `
    -Force
```

## 4. Reinstalar

```powershell
python -m pip install `
    -e . `
    --no-deps `
    --no-cache-dir `
    --force-reinstall
```

## 5. Verificar versión

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Esperado:

```text
Instalada: 0.6.0
Módulo: 0.6.0
```

## 6. Calidad

```powershell
ruff check .

Remove-Item .\.mypy_cache `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue

python -m mypy `
    --config-file .\pyproject.toml `
    src

pytest -v
```

Esperado: Ruff sin errores, Mypy sin errores y 100 pruebas aprobadas.

## 7. Ejecutar

```powershell
streamlit run app.py
```

El modo simulado sigue siendo el predeterminado.

## 8. Activar proveedor externo

No es necesario para validar el modo local. Para habilitarlo en una sesión:

```powershell
$env:IUS_RAZON_LLM_EXTERNAL_ENABLED = "true"
$env:IUS_RAZON_LLM_ENDPOINT = "https://SU-GATEWAY/generate"
$env:IUS_RAZON_LLM_API_KEY = "SU-CLAVE"
$env:IUS_RAZON_LLM_MODEL = "SU-MODELO"
```

El endpoint debe implementar el contrato descrito en el reporte técnico.

## 9. Desactivar y limpiar la sesión

```powershell
Remove-Item Env:IUS_RAZON_LLM_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:IUS_RAZON_LLM_ENDPOINT -ErrorAction SilentlyContinue
Remove-Item Env:IUS_RAZON_LLM_EXTERNAL_ENABLED -ErrorAction SilentlyContinue
Remove-Item Env:IUS_RAZON_LLM_MODEL -ErrorAction SilentlyContinue
```

## 10. Reversión

El código puede recuperarse con la etiqueta `v0.5.1`. La base previa está en
el respaldo `ius_razon_test_pre_sprint44_*.db`. No sobrescribas la base activa
sin detener Streamlit y conservar una copia adicional.
