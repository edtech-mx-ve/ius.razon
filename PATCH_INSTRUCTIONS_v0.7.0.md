# Instalación — Sprint 4.5 v0.7.0

## Entorno

- Windows PowerShell
- Python 3.11 o superior
- entorno virtual activo
- rama esperada: `feature/sprint-4.5`

## 1. Respaldo

Conserva el respaldo previo ya verificado. No es necesaria una migración
destructiva.

## 2. Aplicar parche

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_5_patch_v0.7.0.zip `
    -DestinationPath . `
    -Force
```

## 3. Reinstalar

```powershell
python -m pip install `
    -e . `
    --no-deps `
    --no-cache-dir `
    --force-reinstall
```

## 4. Validar

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"

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

Resultado esperado:

```text
Instalada: 0.7.0
Módulo: 0.7.0
All checks passed!
Success: no issues found
128 passed
```

## 5. Prueba funcional sin clave

```powershell
streamlit run app.py
```

Comprueba que sigan disponibles:

- `Simulado local`;
- `Prueba externa controlada`.

`OpenAI Responses API` no debe aparecer mientras esté desactivado.

## 6. Configuración posterior

No escribas la clave en código, `.env`, Git ni el historial de PowerShell.
Consulta `docs/OPENAI_ENV.example.txt`.

Primero configura variables no secretas y valida. La primera llamada real
debe realizarse después, con el expediente de demostración, contexto reducido,
anonimización, costo mínimo, cero reintentos y fallback local.

## Resultado esperado

La aplicación inicia, los modos locales funcionan y OpenAI permanece oculto
hasta tener configuración completa.
