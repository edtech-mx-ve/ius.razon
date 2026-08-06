# IUS-Razón v0.3.3 — Hotfix de instantáneas de inferencia

## Corrección

Se corrige la detección de la columna `input_snapshot_json` en objetos
`sqlite3.Row`.

La simplificación sugerida por Ruff:

```python
"input_snapshot_json" in row
```

no es equivalente a consultar `row.keys()`, porque la pertenencia de un
`sqlite3.Row` no debe usarse como si fuera un diccionario de claves. Esto
provocaba que la instantánea se recuperara como `{}` y que fallara la
reproducción de ejecuciones.

La implementación corregida crea explícitamente el conjunto de columnas:

```python
available_columns = set(row.keys())
```

y consulta:

```python
"input_snapshot_json" in available_columns
```

## Compatibilidad

- No modifica el esquema SQLite.
- No elimina ni transforma expedientes.
- No cambia el algoritmo del motor 3.0.0.
- Conserva las ejecuciones e instantáneas ya almacenadas.
