# Sprint 5.4 — PostgresReasoningRepository

## Propósito

Implementar la persistencia PostgreSQL del módulo de razonamiento sin activar
todavía PostgreSQL en `app.py`.

El repositorio conserva el contrato público de `ReasoningRepository` para
premisas, reglas, condiciones, versionado, ejecuciones, conclusiones, trazas,
validación de expediente/problema, códigos conocidos y auditoría.

## Diferencias PostgreSQL

La implementación usa `psycopg`, `dict_row` y placeholders `%s`.

No usa `sqlite3`, `PRAGMA`, `executescript` ni placeholders `?`.

La generación de códigos `A-###` y `R-###` utiliza bloqueo transaccional
PostgreSQL para evitar colisiones concurrentes. El versionado aplica la misma
protección antes de calcular el siguiente número de versión.

`initialize()` no crea tablas. Verifica que el esquema PostgreSQL de Sprint
5.4 ya esté instalado y que `reasoning_runs.input_snapshot_json` exista.

## Seguridad de despliegue

Este repositorio no se activa todavía desde `app.py`.

La guardia de backend permanece bloqueando
`IUS_RAZON_PERSISTENCE_BACKEND=postgres` hasta que razonamiento,
argumentación, LLM y la política de recuperación sean compatibles con un único
backend PostgreSQL.

## Validación Neon

El smoke test crea un expediente sintético temporal mediante
`PostgresRepository`, ejecuta operaciones de razonamiento con la URL agrupada
y elimina el expediente completo al finalizar mediante la URL directa.

Las credenciales no se imprimen ni se escriben en archivos versionados.
