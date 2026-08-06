# Guía de prueba Sprint 5.3 — Base sintética reproducible

## Objetivo

Validar que IUS-Razón puede construir una base SQLite de demostración sin publicar datos
personales, archivos adjuntos, secretos ni rutas absolutas en la salida del comando.

## Archivos incorporados

- `src/ius_razon/demo_database.py`;
- `scripts/create_demo_database.py`;
- `tests/test_sprint_53_demo_database.py`.

La base generada se guarda, de forma predeterminada, como `data/ius_razon_demo.db`. Los archivos
`*.db`, `*.db-wal` y `*.db-shm` permanecen excluidos por `.gitignore` y no deben agregarse al
repositorio.

## Generación

```powershell
python .\scripts\create_demo_database.py
```

Si la base ya existe, el comando se detiene para evitar una sobrescritura accidental. Para
reconstruirla deliberadamente:

```powershell
python .\scripts\create_demo_database.py --force
```

Para utilizar otra ubicación:

```powershell
python .\scripts\create_demo_database.py `
    --output .\data_test\ius_razon_demo_test.db `
    --force
```

## Contenido esperado

- un expediente marcado como `Demo pública`;
- dos partes identificadas únicamente mediante alias ficticios;
- tres hechos y tres pruebas sin archivos adjuntos;
- tres relaciones hecho-prueba;
- dos problemas jurídicos;
- dos reglas contractuales expresamente sintéticas;
- una referencia jurisprudencial ficticia y pendiente de verificación;
- una fuente doctrinal ficticia;
- cuatro relaciones problema-fuente.

Ninguna fuente creada por el generador constituye legislación, jurisprudencia, doctrina o
asesoría jurídica real.

## Validación automatizada

```powershell
ruff check .
python -m mypy --config-file .\pyproject.toml src
pytest -q
```

Las pruebas específicas del Sprint 5.3 pueden ejecutarse con:

```powershell
pytest -q .\tests\test_sprint_53_demo_database.py
```

## Revisión de privacidad

```powershell
git status --short
git check-ignore -v .\data\ius_razon_demo.db
```

La base debe aparecer como ignorada y nunca como archivo preparado para commit. La salida JSON
del generador solo muestra el nombre del archivo, el título sintético y los conteos; no muestra la
ruta absoluta del sistema.
