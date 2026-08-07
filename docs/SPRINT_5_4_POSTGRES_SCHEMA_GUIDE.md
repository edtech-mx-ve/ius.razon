# Sprint 5.4 — Esquema PostgreSQL y transición controlada

## Resultado

Este bloque crea en Neon el esquema PostgreSQL equivalente a la persistencia
actual de IUS-Razón. El SQL se genera a partir de los cuatro esquemas SQLite
vigentes para evitar divergencias accidentales.

Se incluyen 28 tablas de aplicación y una tabla interna de metadatos de versión.

## Estrategia

SQLite continúa siendo el backend predeterminado. La variable
`IUS_RAZON_PERSISTENCE_BACKEND` queda preparada con dos valores:

- `sqlite`: comportamiento local actual;
- `postgres`: reservado para la migración progresiva de repositorios.

Este bloque no cambia `app.py` y no sustituye todavía los repositorios SQLite.

## Seguridad

La creación del esquema usa únicamente `DIRECT_DATABASE_URL`. Las credenciales
se leen desde variables de entorno o `.streamlit/secrets.toml` y no se imprimen.

Los archivos `secrets*.toml` quedan ignorados por Git.

## Validación

```powershell
python .\scripts\init_postgres_schema.py
python .\scripts\check_postgres_schema.py
ruff check .
python -m mypy --config-file .\pyproject.toml src scripts
pytest -q
git diff --check
```

## Siguiente etapa

Implementar el repositorio PostgreSQL del núcleo de expedientes y validarlo
contra el contrato funcional existente. Después se migrarán razonamiento,
argumentación y asistente en bloques separados.
