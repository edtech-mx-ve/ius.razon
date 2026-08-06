# Guía de prueba funcional — Sprint 3.1

## Preparación

```powershell
pytest -v
ruff check .
mypy src
streamlit run app.py
```

Abre:

```text
http://localhost:8501
```

Selecciona el expediente que contiene `PJ-001`, las siete premisas y `R-001`.

## Prueba 1 — Edición versionada

1. Abre `Gestión razonamiento`.
2. Selecciona el problema `PJ-001`.
3. En `Premisas`, selecciona `A-006 causa_justificante`.
4. Cambia el valor de `Desconocido` a `Verdadero`.
5. Conserva la clave `causa_justificante`.
6. Pulsa `Guardar cambios de premisa`.

Resultado esperado:

```text
Premisa A-006 actualizada y versionada.
```

Comprueba:

- el código sigue siendo `A-006`;
- aparece una versión anterior;
- existe un nuevo archivo en `<data_dir>/backups/`.

## Prueba 2 — Bloqueo por excepción

1. Abre `Inferencia`.
2. Ejecuta `PJ-001`.
3. Revisa la traza.

Resultado esperado:

```text
R-001 · Bloqueada por excepción
Conclusiones: 0
```

## Prueba 3 — Comparación

Con al menos dos ejecuciones:

1. abre `Comparar ejecuciones`;
2. usa como base la ejecución con `A-006=Desconocido`;
3. usa como comparada la ejecución con `A-006=Verdadero`;
4. pulsa `Comparar resultados`.

Resultado esperado:

- `same_input` es `false`;
- `incumplimiento_entrega=Verdadero` aparece entre las conclusiones removidas.

## Prueba 4 — Exportación

En una ejecución:

1. pulsa `Descargar JSON`;
2. pulsa `Descargar Markdown`;
3. abre ambos archivos.

El JSON debe contener:

```text
input_snapshot
conclusions
traces
input_hash
```

El Markdown debe contener la huella, las conclusiones y la traza.

## Prueba 5 — Desactivación

1. abre `Gestión razonamiento` → `Reglas`;
2. selecciona `R-001`;
3. desmarca `Regla activa`;
4. guarda.

Resultado esperado:

- el código continúa siendo `R-001`;
- la versión anterior muestra `active=true`;
- `Inferencia` muestra cero reglas activas.

Activa nuevamente la regla para continuar.

## Prueba 6 — Eliminación protegida

1. selecciona `A-001 pago_acreditado`;
2. escribe `A-001`;
3. intenta eliminar.

Resultado esperado:

```text
La premisa no puede eliminarse porque su clave lógica aparece en condiciones de reglas.
```

No debe desaparecer ningún registro.

## Restauración del escenario

Devuelve:

```text
A-006 causa_justificante = Desconocido
R-001 activa = Sí
```

Ejecuta de nuevo. Debe reaparecer la conclusión provisional de incumplimiento.
