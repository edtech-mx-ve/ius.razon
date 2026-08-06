# Guía de prueba funcional — Sprint 4.5.1 v0.7.1

## Precondiciones

- rama `feature/sprint-4.5.1-ollama`;
- Ollama instalado;
- `qwen3:1.7b` visible en `ollama list`;
- API local operativa en `127.0.0.1:11434`;
- base SQLite respaldada.

## Validación técnica

```powershell
python -c "from importlib.metadata import version; import ius_razon; print(version('ius-razon')); print(ius_razon.__version__)"
ruff check .

Remove-Item .\.mypy_cache -Recurse -Force -ErrorAction SilentlyContinue
python -m mypy --config-file .\pyproject.toml src

pytest -v
```

Resultado esperado:

```text
0.7.1
0.7.1
All checks passed!
Success: no issues found
142 passed
```

## Prueba funcional

Inicia:

```powershell
streamlit run app.py
```

En `Asistente IA`:

```text
Proveedor: Ollama local gratuito
Problema: PJ-001
Ejecución: 3385ccd1 · 1 conclusiones
Tarea: Resumen del expediente
Anonimizar partes: activado
```

Conserva un contexto reducido, por ejemplo:

```text
PJ-001
H-001
H-002
P-001
C-001
```

Indicación:

```text
Resume únicamente el pago acreditado, el vencimiento del plazo y la conclusión
provisional. Conserva las referencias internas y no agregues hechos nuevos.
```

Pulsa `Generar con Ollama local`.

## Resultado esperado

- proveedor: `Ollama local gratuito`;
- modelo: `qwen3:1.7b`;
- llamada externa: `No`;
- costo: `USD 0.000000`;
- referencias inválidas: `0`;
- texto disponible para revisión;
- botón `Aprobar versión revisada`;
- auditoría con tokens locales reportados.

## Fallback

Detén Ollama y repite una generación con fallback habilitado. Debe:

- generar mediante `Simulado local`;
- mostrar aviso de fallback;
- registrar `fallback_used=true`;
- conservar `external_call=false`.

Reinicia Ollama antes de continuar.

## Aceptación humana

Revisa el texto, conserva las referencias y añade:

```text
Validación funcional de Ollama local: generación sin clave, sin costo, sin
envío externo y con revisión humana.
```

Aprueba la versión revisada y confirma estado `Aprobado`.
