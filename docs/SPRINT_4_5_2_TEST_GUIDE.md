# Guía de prueba — Sprint 4.5.2

## Preparación

```powershell
git branch --show-current
python -c "import ius_razon; print(ius_razon.__version__)"
ollama --version
ollama list
```

Esperado:

```text
feature/sprint-4.5.2
0.7.2
qwen3:1.7b
```

## Prueba 1 — Diagnóstico por consola

```powershell
python .\scripts\diagnose_ollama.py
```

Criterios:

```text
ready = true
service_available = true
model_installed = true
configured_model = qwen3:1.7b
estimated_cost_usd = 0.0
```

No deben aparecer hechos, partes, pruebas, prompts ni respuestas.

## Prueba 2 — Diagnóstico en Streamlit

```powershell
streamlit run app.py
```

Abre `http://localhost:8501`, entra a `Asistente IA` y selecciona
`Ollama local gratuito`.

Debe mostrarse:

- servicio disponible;
- modelo instalado;
- versión;
- cantidad de modelos locales;
- botón `Actualizar diagnóstico de Ollama`.

## Prueba 3 — Generación normal

Selecciona únicamente códigos que existan en la interfaz. Para el caso de
demostración previamente validado pueden usarse, cuando existan:

```text
PJ-001
H-001
H-002
P-001
```

Indicación:

```text
Resume únicamente el pago acreditado y el vencimiento del plazo. Usa solo los elementos seleccionados, conserva las referencias internas y no agregues hechos.
```

Criterios:

```text
Proveedor = Ollama local gratuito
Modelo = qwen3:1.7b
Externa = No
Costo = USD 0.000000
Fallback = No
```

## Prueba 4 — Ausencia de conclusión

Genera sin seleccionar una conclusión y solicita que se informe el vacío.

La salida operativa debe quedar como:

```text
Control de contexto: no se proporcionó una conclusión de inferencia.
```

El borrador debe poder alcanzar 100 % de cobertura cuando las afirmaciones
sustantivas restantes tengan citas válidas.

## Prueba 5 — Modelo no permitido

En una terminal temporal:

```powershell
$env:IUS_RAZON_OLLAMA_MODEL = "qwen3:4b"
$env:IUS_RAZON_OLLAMA_ALLOWED_MODELS = "qwen3:1.7b"

python .\scripts\diagnose_ollama.py
```

Debe finalizar con configuración inválida. Limpia:

```powershell
Remove-Item Env:IUS_RAZON_OLLAMA_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:IUS_RAZON_OLLAMA_ALLOWED_MODELS -ErrorAction SilentlyContinue
```

## Prueba 6 — Modelo cloud bloqueado

```powershell
$env:IUS_RAZON_OLLAMA_MODEL = "gpt-oss:120b-cloud"
$env:IUS_RAZON_OLLAMA_ALLOWED_MODELS = "gpt-oss:120b-cloud"

python .\scripts\diagnose_ollama.py
```

Debe informar que los modelos cloud no están permitidos. Limpia las variables.

## Prueba 7 — Fallback

Detén Ollama desde la bandeja y actualiza el diagnóstico. Con datos de prueba,
genera un borrador con fallback habilitado.

Criterios:

```text
Fallback = Sí
Proveedor efectivo = Simulado local
Error seguro = ollama_unavailable u otro código local controlado
Externa = No
Costo = USD 0
```

Reinicia Ollama y confirma nuevamente `ready = true`.

## Prueba 8 — Calidad

```powershell
ruff check .
python -m mypy --config-file .\pyproject.toml src
pytest -q
```

Esperado:

```text
All checks passed!
Success: no issues found
159 passed
```

## Criterio final

No aprobar el sprint hasta que:

- diagnóstico real listo;
- generación real local correcta;
- fallback controlado probado;
- cita y revisión humana aprobadas;
- Git no incluya bases, logs, secretos ni respaldos.
