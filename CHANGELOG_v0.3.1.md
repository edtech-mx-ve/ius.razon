# IUS-Razón v0.3.1

## Correcciones

- Se corrigió la organización del bloque de importaciones en `tests/test_reasoning_engine.py`.
- Se cambió el parámetro de auditoría de `dict[str, object]` a `Mapping[str, object]`
  para aceptar de forma segura resúmenes tipados con valores `int`, `str` y `bool`.
- No se modificó el esquema SQLite ni la lógica de inferencia.
- La actualización es compatible con las bases de datos de v0.3.0.
