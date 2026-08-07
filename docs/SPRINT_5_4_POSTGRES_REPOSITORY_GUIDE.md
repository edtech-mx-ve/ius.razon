# Sprint 5.4 — Primer PostgresRepository funcional

## Alcance

Este bloque implementa `PostgresRepository` para el núcleo de IUS-Razón
manteniendo el contrato público de `SQLiteRepository`.

La implementación cubre:

- expedientes;
- partes;
- hechos;
- pruebas;
- vínculos hecho-prueba;
- problemas jurídicos;
- normas;
- jurisprudencia;
- doctrina;
- vínculos problema-fuente;
- actualización y eliminación protegida;
- contadores y resúmenes;
- auditoría;
- secuencias de códigos estables.

## Compatibilidad

La lógica de dominio permanece alineada con SQLite. PostgreSQL cambia
exclusivamente la infraestructura de conexión, placeholders SQL y el control
concurrente de secuencias.

Los errores `RepositoryError`, `NotFoundError` y `ConflictError` se reutilizan
desde la implementación existente para preservar la identidad de las
excepciones que ya conoce la aplicación.

## Concurrencia de códigos

PostgreSQL utiliza `pg_advisory_xact_lock` por expediente y tabla antes de
incrementar `code_sequences`. De esta manera se evita que dos operaciones
concurrentes generen el mismo código lógico.

## Estado de activación

`app.py` NO cambia en este bloque. SQLite continúa siendo el backend operativo
de la aplicación hasta que razonamiento, argumentación, asistente y estrategia
de respaldo estén preparados para PostgreSQL.

## Prueba real

`scripts/smoke_postgres_repository.py` crea un expediente completamente
sintético en Neon, valida CRUD, vínculos, códigos, auditoría y protecciones, y
lo elimina al finalizar, incluso cuando la prueba falla después de crear el
expediente.
