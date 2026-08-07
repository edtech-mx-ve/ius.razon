# Sprint 5.4 — Desacoplamiento de LLMAssistantService

## Propósito

Separar `LLMAssistantService` de la persistencia concreta SQLite para permitir
que opere con `LLMRepository` o `PostgresLLMRepository` mediante un contrato
estructural común.

## Cambios

`LLMAssistantService` deja de depender de:

- `LLMRepository` concreto;
- `repository.db_path`;
- `backup_dir`;
- `create_database_backup`.

El servicio pasa a recibir:

- `LLMRepositoryProtocol`;
- `MutationBackup`.

Las construcciones existentes que usaban `backup_dir` se migran a
`SQLiteMutationBackup` porque `app.py` continúa ejecutándose con SQLite.

Si existiera alguna construcción que anteriormente omitiera `backup_dir`, el
instalador conserva ese comportamiento de ausencia explícita de respaldo usando
`NoOpMutationBackup`, únicamente en esa construcción ya existente.

## Compatibilidad

`LLMRepository` y `PostgresLLMRepository` satisfacen
`LLMRepositoryProtocol`.

Este bloque no activa PostgreSQL en `app.py` y no modifica secretos ni
credenciales. La política definitiva de recuperación PostgreSQL se definirá
antes de habilitar el backend PostgreSQL en producción.
