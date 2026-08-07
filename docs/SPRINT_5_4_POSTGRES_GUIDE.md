# Sprint 5.4 — Conexión inicial con Neon PostgreSQL

## Alcance de este bloque

Este bloque incorpora la base técnica para PostgreSQL sin sustituir todavía los
repositorios SQLite:

- dependencia Psycopg 3 con distribución binaria;
- validación separada de conexión agrupada y directa;
- secretos locales en `.streamlit/secrets.toml`;
- verificación real de ambas conexiones;
- pruebas que impiden intercambiar las dos URL;
- mensajes de error que no exponen contraseñas.

## Variables privadas

- `DATABASE_URL`: conexión agrupada de Neon; el host contiene `-pooler`.
- `DIRECT_DATABASE_URL`: conexión directa; el host no contiene `-pooler`.

Los valores reales no deben incluirse en Git, documentación, capturas o
mensajes. `.streamlit/secrets.toml` está excluido mediante `.gitignore`.

## Validación

```powershell
python .\scripts\check_postgres.py
ruff check .
python -m mypy --config-file .\pyproject.toml src scripts
pytest -q
git diff --check
```

## Límite actual

IUS-Razón continúa utilizando SQLite para sus operaciones jurídicas. Este
bloque comprueba la infraestructura PostgreSQL y deja preparada la siguiente
etapa: crear el esquema compatible y migrar los repositorios de manera
controlada.