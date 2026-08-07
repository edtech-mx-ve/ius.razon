# Sprint 5.4 — Política de recuperación PostgreSQL Neon

## Decisión

Para la activación PostgreSQL de Sprint 5.4 se utiliza la recuperación
administrada por Neon mediante Point-in-Time Recovery / Instant Restore.

La política de runtime no crea archivos SQLite ni ejecuta `pg_dump` antes de
cada mutación. En su lugar, `NeonPitrMutationBackup` verifica antes de una
mutación sensible que PostgreSQL puede proporcionar:

- una marca temporal del servidor;
- el LSN WAL actual.

Si no puede obtenerse ese punto técnico, la mutación se cancela.

## Plan Free utilizado

Revisión realizada el 2026-08-07 sobre documentación pública de Neon.

El plan Free documenta Instant Restore con una ventana de hasta 6 horas o
1 GB de cambios, lo que ocurra primero. Esta ventana es adecuada para el
objetivo de costo cero de Sprint 5.4, pero no equivale a una política de
retención prolongada.

Los snapshots programados no forman parte de esta política de costo cero.

## Alcance de MutationBackup

`SQLiteMutationBackup` continúa creando respaldos físicos para SQLite.

`NeonPitrMutationBackup` implementa el mismo contrato, pero delega la
recuperación histórica en Neon y valida la disponibilidad de un punto WAL
previo a la mutación.

`NoOpMutationBackup` queda reservado para pruebas o construcciones que
explícitamente no requieren persistencia de recuperación. No debe utilizarse
para activar PostgreSQL en runtime.

## Conexión

La política usa `DATABASE_URL`, la conexión agrupada destinada al runtime.
No necesita `DIRECT_DATABASE_URL`, credenciales adicionales ni una Neon API key.

No se imprime ni registra ninguna URL de conexión.

## Recuperación operativa

Ante una mutación errónea:

1. identificar la hora inmediatamente anterior al incidente;
2. utilizar Instant Restore / PITR en Neon dentro de la ventana disponible;
3. restaurar o crear una rama desde el punto anterior;
4. validar datos y esquema antes de redirigir el runtime;
5. conservar temporalmente la rama anterior mientras se verifica la recuperación.

La política de aplicación no intenta automatizar el cambio de rama.
La restauración sigue siendo una operación administrativa deliberada.

## Activación

Este bloque no modifica `app.py`, no retira todavía
`BackendActivationError` y no habilita PostgreSQL en Streamlit.

El siguiente bloque puede construir el factory/selector de persistencia usando
`NeonPitrMutationBackup` para el backend PostgreSQL.
