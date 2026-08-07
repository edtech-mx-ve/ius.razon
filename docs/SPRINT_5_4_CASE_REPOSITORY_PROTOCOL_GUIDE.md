# Sprint 5.4 — Desacoplamiento de CaseService

## Objetivo

Separar el servicio de casos de la implementación concreta de SQLite sin
activar todavía PostgreSQL en la aplicación pública.

## Contratos introducidos

`CaseRepository` define exclusivamente las operaciones de persistencia que
consume `CaseService`. Tanto `SQLiteRepository` como `PostgresRepository`
satisfacen estructuralmente este contrato.

`MutationBackup` separa la política de respaldo previo de la lógica de casos.

`SQLiteMutationBackup` conserva el comportamiento existente: antes de
actualizaciones, eliminaciones o cambios de vínculos protegidos se crea un
respaldo local de la base SQLite y la operación se cancela si el respaldo no
puede generarse.

## Estado de PostgreSQL

Este bloque NO cambia el backend activo de `app.py`.

`PostgresRepository` ya cumple el contrato de `CaseRepository`, pero la
aplicación seguirá construyendo `SQLiteRepository` y
`SQLiteMutationBackup`. La política de respaldo o recuperación de PostgreSQL
se definirá antes de activar el backend PostgreSQL para `CaseService`.

## Ventaja arquitectónica

`CaseService` deja de depender de detalles de SQLite. La persistencia y la
política de respaldo pasan a ser dependencias explícitas, lo que evita
introducir condicionales por motor de base de datos dentro de la capa de
servicio.
