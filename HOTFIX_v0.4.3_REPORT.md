# IUS-Razón v0.4.3 — Reporte del hotfix

## Incidencias corregidas

- Ruff I001 en `report_models.py`.
- Ruff I001 y UP035 en `legal_report_service.py`.
- Mypy `no-untyped-call` en saltos de página de `python-docx`.
- Mypy `attr-defined` para el espaciado de portada.
- Mypy `assignment` y `attr-defined` por reutilización de la variable `item`
  entre jurisprudencia y doctrina.

## Solución

- Imports ordenados y `Iterable` movido a `collections.abc`.
- Supresión localizada y documentada en dos llamadas de `python-docx` sin stubs.
- Uso de `paragraph.paragraph_format.space_after`.
- Variables diferenciadas: `precedent` y `doctrine`.
- Versión de aplicación actualizada a 0.4.3.

## Compatibilidad

No hay cambios de esquema SQLite ni de datos. El motor sigue en 3.2.0 y el
formato funcional del informe integral permanece en 4.2.0.

## Verificación de construcción

- 66 pruebas automatizadas aprobadas.
- Sintaxis Python validada.
- Ninguna línea Python supera 100 caracteres.
- Ruff y Mypy deben confirmarse en el entorno local del usuario.
