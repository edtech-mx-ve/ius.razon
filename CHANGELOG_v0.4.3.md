# IUS-Razón v0.4.3 — Hotfix de calidad estática del informe integral

## Correcciones

- Ordena los imports detectados por Ruff.
- Importa `Iterable` desde `collections.abc`.
- Declara localmente las llamadas sin tipado de `python-docx`.
- Corrige el espaciado de portada mediante `paragraph_format`.
- Separa las variables de jurisprudencia y doctrina para evitar inferencias de tipo incompatibles.

## Compatibilidad

- No modifica el esquema SQLite.
- No altera expedientes, premisas, reglas, argumentos ni escenarios.
- Mantiene el motor de razonamiento 3.2.0.
- Mantiene el formato funcional del informe integral 4.2.0.
