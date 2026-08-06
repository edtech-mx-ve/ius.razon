# IUS-Razón v0.4.1 — Sprint 4.1

## Incorporado

- escenarios argumentales persistentes con códigos `SCN-###`;
- estados `Borrador`, `Activo` y `Archivado`;
- selección controlada de argumentos por escenario;
- supuestos explícitos;
- grafo dirigido de argumentos y relaciones;
- visualización DOT dentro de Streamlit;
- formas diferenciadas por posición argumental;
- métricas de nodos, relaciones, ataques, réplicas y componentes;
- detección de objeciones sin réplica;
- detección de argumentos aislados;
- comparación entre escenarios y vista completa;
- huellas SHA-256 deterministas;
- exportación a JSON, Markdown y DOT;
- edición y eliminación segura de escenarios;
- protección de argumentos incluidos en escenarios;
- respaldo y auditoría antes de mutaciones.

## Migración

La migración crea `argument_scenarios` y su índice. No modifica las tablas
previas ni transforma registros existentes.

## Compatibilidad

- aplicación: `0.4.1`;
- motor de razonamiento: `3.2.0`;
- Python: `>=3.11`;
- Streamlit: `>=1.40,<2`;
- base de origen recomendada: IUS-Razón `0.4.0`.

## Pruebas

Se agregan ocho pruebas automatizadas para escenarios, grafos, comparación,
exportación, aislamiento entre problemas, edición segura y protección de
dependencias.
