# Sprint 5.4 — Factory único SQLite/PostgreSQL

## Propósito

Centralizar la construcción de persistencia para impedir que una ejecución
combine repositorios SQLite y PostgreSQL.

## PersistenceBundle

`PersistenceBundle` entrega como una sola unidad:

- backend seleccionado;
- repositorio de expedientes;
- repositorio de razonamiento;
- repositorio de argumentación;
- repositorio LLM;
- política `MutationBackup`;
- respaldo de arranque, cuando aplica.

## Rama SQLite

Todos los repositorios reciben el mismo `config.db_path`.

Antes de inicializar se conserva el respaldo de arranque existente. Los cuatro
servicios comparten una política `SQLiteMutationBackup` sobre esa misma base.

## Rama PostgreSQL

Todos los repositorios reciben exactamente la misma `DATABASE_URL` agrupada:

- `PostgresRepository`;
- `PostgresReasoningRepository`;
- `PostgresArgumentationRepository`;
- `PostgresLLMRepository`.

La política de recuperación es `NeonPitrMutationBackup` con una ventana de
referencia de 6 horas.

`DIRECT_DATABASE_URL` no se usa para operaciones normales del factory.

## Sin fallback

El factory no captura errores para regresar silenciosamente a SQLite.

Si se solicita PostgreSQL y ocurre un error de configuración, conexión o
esquema, la construcción falla. Esto evita un backend mixto o una degradación
silenciosa.

## Integración temporal con app.py

`app.py` deja de construir repositorios concretos y consume exclusivamente
`build_persistence_bundle`.

Sin embargo, durante este bloque conserva:

`persistence_settings.require_runtime_supported()`

antes de invocar el factory. Por tanto, el código PostgreSQL queda preparado
pero todavía no puede activarse desde el runtime Streamlit.

## Siguiente bloque

La activación PostgreSQL debe eliminar la guardia temporal únicamente después
de validar:

1. lectura de configuración Streamlit/entorno;
2. factory PostgreSQL real contra Neon;
3. servicios completos con los cuatro repositorios PostgreSQL;
4. política Neon PITR;
5. ausencia de fallback y backend mixto.
