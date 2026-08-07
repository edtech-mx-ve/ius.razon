# Sprint 5.4 — PostgresLLMRepository

## Propósito

Implementar persistencia PostgreSQL para borradores asistivos y auditoría de
proveedores sin activar todavía PostgreSQL en `app.py`.

La implementación conserva el contrato público de `LLMRepository`:

- validación expediente/problema;
- borradores `IA-###`;
- historial de borradores;
- revisión humana;
- auditoría de llamadas a proveedor;
- vínculo entre llamada auditada y borrador.

## PostgreSQL

`PostgresLLMRepository` utiliza `psycopg`, `dict_row` y placeholders `%s`.

No usa `sqlite3`, `PRAGMA`, `executescript`, `PRAGMA table_info` ni
placeholders SQL `?`.

Las tablas `llm_draft_sequences`, `llm_drafts` y `llm_provider_calls` ya forman
parte del esquema PostgreSQL Sprint 5.4. `initialize()` verifica ese esquema y
no ejecuta migraciones SQLite.

La secuencia `IA-###` utiliza `pg_advisory_xact_lock` y se sincroniza con los
códigos ya existentes para evitar colisiones concurrentes.

## Smoke Neon

El smoke crea un expediente temporal y valida exclusivamente persistencia:

- registro de llamada auditada;
- creación de dos borradores;
- vínculo llamada/borrador;
- aprobación y rechazo humano;
- protección contra doble revisión;
- historial y recuperación;
- secuencia `IA-001`, `IA-002`.

No realiza llamadas a OpenAI, Ollama ni proveedores externos.

La URL agrupada se utiliza para operaciones normales y la URL directa solo para
eliminar el expediente sintético al terminar. Ninguna credencial se imprime ni
se escribe en archivos versionados.

## Activación

Este bloque no modifica `app.py`. La guardia contra activación parcial continúa
bloqueando PostgreSQL en runtime.

El bloque siguiente desacoplará `LLMAssistantService` de `LLMRepository`,
`repository.db_path` y `backup_dir` mediante `MutationBackup`.
