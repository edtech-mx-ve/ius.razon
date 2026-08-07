# Sprint 5.4 — Desacoplamiento de ReasoningService

## Propósito

Separar `ReasoningService` de la implementación SQLite para permitir que el
mismo servicio pueda operar, posteriormente, con `ReasoningRepository` o
`PostgresReasoningRepository` mediante un contrato estructural común.

## Cambios

Se incorpora `ReasoningRepositoryProtocol`, que declara únicamente las
operaciones de persistencia requeridas por `ReasoningService`.

`ReasoningService` deja de importar el repositorio SQLite concreto y deja de
crear respaldos a partir de `repository.db_path`.

La política previa a mutaciones se inyecta mediante `MutationBackup`.

Para SQLite se conserva `SQLiteMutationBackup`. Para pruebas y contextos donde
el respaldo persistente no corresponde se incorpora `NoOpMutationBackup` como
política explícita.

## Compatibilidad

Las construcciones existentes de `ReasoningService` se migran de forma
explícita:

- aplicación SQLite: `SQLiteMutationBackup`;
- pruebas sin respaldo persistente: `NoOpMutationBackup`.

No se activa PostgreSQL desde `app.py`.

## Estado posterior

- núcleo PostgreSQL: disponible;
- razonamiento PostgreSQL: disponible;
- `CaseService`: desacoplado;
- `ReasoningService`: desacoplado;
- argumentación PostgreSQL: pendiente;
- LLM PostgreSQL: pendiente;
- activación integral PostgreSQL: bloqueada.
