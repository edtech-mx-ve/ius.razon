# Sprint 5.4 — PostgresArgumentationRepository

## Propósito

Implementar la persistencia PostgreSQL del módulo de argumentación sin activar
todavía PostgreSQL en `app.py`.

El repositorio conserva el contrato público de `ArgumentationRepository` para
argumentos, relaciones, escenarios, contextos de conclusiones, códigos
conocidos, metadatos e instantáneas argumentales.

## Diferencias PostgreSQL

La implementación utiliza `psycopg`, `dict_row` y placeholders `%s`.

No usa `sqlite3`, `PRAGMA`, `executescript` ni placeholders `?`.

Las secuencias `ARG-###`, `REL-###` y `SCN-###` usan bloqueo transaccional
PostgreSQL para impedir colisiones concurrentes. Al inicializarse, la
implementación sincroniza las secuencias con los códigos existentes.

`initialize()` no crea ni altera tablas. Verifica que las tablas requeridas del
esquema Sprint 5.4 estén instaladas.

## Seguridad de despliegue

El repositorio no se activa todavía desde `app.py`.

La guardia de backend continúa impidiendo una activación parcial de PostgreSQL.
Después de este bloque debe desacoplarse `ArgumentationService`; posteriormente
se migrará la capa LLM y se definirá la política de recuperación PostgreSQL.

## Validación Neon

El smoke test crea un expediente temporal, genera una conclusión de
razonamiento, registra argumentos favorables y adversos, relaciones y un
escenario, valida las protecciones de dependencias y elimina el expediente
sintético al terminar.

La URL agrupada se usa para operaciones normales y la URL directa únicamente
para la limpieza administrativa del smoke. Ninguna credencial se imprime ni se
escribe en archivos versionados.
