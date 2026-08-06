# Guía de prueba funcional — Sprint 4.4.1 v0.6.1

## Precondiciones

- Rama `feature/sprint-4.4.1`.
- Versión instalada `0.6.1`.
- Base respaldada y verificada.
- No configurar `IUS_RAZON_LLM_API_KEY`.
- Streamlit detenido durante la instalación.

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
0.6.1
0.6.1
All checks passed!
Success: no issues found
112 passed
```

## Prueba funcional

Inicia:

```powershell
streamlit run app.py
```

En **Asistente IA** selecciona:

```text
Proveedor: Prueba externa controlada
Problema: PJ-001
Ejecución: 3385ccd1 · 1 conclusiones
Tarea: Resumen del expediente
Anonimizar partes: activado y bloqueado
```

Indicación:

```text
Prioriza el pago acreditado, el vencimiento del plazo y la conclusión
provisional. Conserva las referencias internas y no agregues hechos nuevos.
```

Verifica el perfil:

```text
Entrada: 2048 tokens
Salida: 256 tokens
Costo máximo: USD 0.0100
Tiempo: 15 s
Reintentos: 0
Fallback local obligatorio
Red desactivada
```

Marca:

```text
Confirmo que revisé el contexto y los códigos seleccionados
Autorizo esta prueba específica sin red
Acepto el límite de costo mostrado
Confirmo una sola invocación de prueba y cero reintentos
```

Pulsa **Ejecutar prueba externa controlada**.

## Resultado esperado

El borrador debe mostrar:

```text
Modo: Prueba externa controlada
Proveedor: Externo falso de integración
Modelo: ius-razon-external-test-v1
Cobertura: 100 %
Estado: Generado
```

En **Auditoría de proveedores**:

```text
Modo: Prueba externa controlada
Estado: Completada
Externa: No
Fallback: No
Costo USD: 0.000000
```

Aprueba el borrador únicamente después de revisar el texto. El historial debe
mostrar `Estado: Aprobado`.

## Prueba negativa

Desmarca la confirmación de una sola invocación y pulsa el botón. Debe
bloquearse con un mensaje equivalente a:

```text
Debes confirmar que se ejecutará una sola invocación de prueba.
```

La auditoría debe registrar `Bloqueada` y
`single_call_not_confirmed`.

## Criterio de cierre

El sprint puede cerrarse cuando la validación técnica y funcional pasan, la
auditoría no contiene secretos ni contenido sensible y Git queda limpio.
