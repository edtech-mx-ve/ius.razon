# Sprint 5.4 — Guardia de activación del backend

## Propósito

IUS-Razón ya dispone de un `PostgresRepository` funcional para el núcleo y
`CaseService` dejó de depender directamente de SQLite. Sin embargo, las capas
de razonamiento, argumentación y asistencia LLM todavía utilizan repositorios
SQLite.

Activar PostgreSQL solo para el núcleo produciría un backend mixto: los datos
de un mismo expediente quedarían distribuidos entre motores diferentes.

## Regla de activación

`PersistenceSettings` continúa aceptando:

- `sqlite`
- `postgres`

Cuando se solicita `postgres`, primero se validan `DATABASE_URL` y
`DIRECT_DATABASE_URL`. Después, la aplicación aplica
`require_runtime_supported()`.

Mientras la migración completa no haya terminado, esta guardia detiene el
arranque con un error explícito. No hay fallback silencioso a SQLite y no se
imprimen credenciales.

## Estado actual

- SQLite: backend operativo de la aplicación.
- PostgreSQL núcleo: implementado y probado contra Neon.
- Razonamiento PostgreSQL: pendiente.
- Argumentación PostgreSQL: pendiente.
- LLM PostgreSQL: pendiente.
- Activación integral PostgreSQL: bloqueada intencionalmente.

## Criterio para retirar la guardia

La guardia solo debe sustituirse por una fábrica real de repositorios cuando
todas las capas persistentes puedan construirse sobre el mismo backend y
exista una estrategia de recuperación compatible con PostgreSQL.
