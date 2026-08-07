# Sprint 5.4 — Activación runtime PostgreSQL

## Estado

PostgreSQL deja de estar bloqueado artificialmente en el runtime.

La activación se apoya en componentes ya validados durante Sprint 5.4:
los cuatro repositorios PostgreSQL, los protocolos de persistencia,
`NeonPitrMutationBackup`, `PersistenceBundle` y la ausencia de fallback.

## Selector

El backend se selecciona con `IUS_RAZON_PERSISTENCE_BACKEND`.

Valores permitidos: `sqlite` y `postgres`.

SQLite continúa siendo el valor predeterminado si el selector no existe.

Para PostgreSQL también deben estar configuradas `DATABASE_URL` y
`DIRECT_DATABASE_URL`.

La configuración puede obtenerse del entorno o del archivo local
`.streamlit/secrets.toml`. El entorno tiene prioridad.

## Streamlit Community Cloud

Para activar Neon en la aplicación desplegada debe añadirse a los secretos de
Streamlit:

`IUS_RAZON_PERSISTENCE_BACKEND = "postgres"`

Las URLs PostgreSQL existentes se conservan como secretos. No deben copiarse al
repositorio ni a archivos versionados.

## Factory

`app.py` usa exclusivamente `build_persistence_bundle`.

Cuando el backend es PostgreSQL, las cuatro capas reciben la misma conexión
agrupada `DATABASE_URL` y comparten `NeonPitrMutationBackup`.

No existe fallback PostgreSQL a SQLite.

## Validación previa al commit

El instalador ejecuta pruebas de configuración, construcción integrada del
bundle PostgreSQL real contra Neon, construcción de los cuatro servicios,
validación real del punto WAL, los cuatro smoke CRUD PostgreSQL existentes,
verificación de conexiones y esquema, y la suite completa.

Los smoke CRUD eliminan sus datos sintéticos al terminar.

## Seguridad

No se imprimen URLs PostgreSQL ni credenciales.

Los archivos `.streamlit/secrets*.toml` permanecen ignorados por Git.

## Paso posterior

Después de integrar este bloque, la activación en Streamlit requiere cambiar
únicamente el secreto del selector a `postgres` y verificar el despliegue
remoto.
