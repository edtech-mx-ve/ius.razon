# Sprint 5.4 — Desacoplamiento de ArgumentationService

## Propósito

Separar `ArgumentationService` de los detalles de persistencia SQLite para que
pueda operar con cualquier repositorio que satisfaga
`ArgumentationRepositoryProtocol`.

## Cambios

`ArgumentationService` deja de depender de:

- `ArgumentationRepository` concreto.
- `repository.db_path`.
- `backup_dir`.
- `create_database_backup`.

El servicio pasa a recibir:

- `ArgumentationRepositoryProtocol`.
- `MutationBackup`.

La política SQLite continúa usando `SQLiteMutationBackup`. Las pruebas que no
requieren un respaldo persistente pueden usar `NoOpMutationBackup`.

## Compatibilidad

`ArgumentationRepository` y `PostgresArgumentationRepository` satisfacen el
mismo protocolo estructural.

`app.py` continúa construyendo la implementación SQLite y suministra
`SQLiteMutationBackup`. PostgreSQL sigue bloqueado para runtime por la guardia
de Sprint 5.4.

Este bloque no activa PostgreSQL, no modifica credenciales y no altera la
política de recuperación PostgreSQL, que se definirá antes de la activación
productiva.
