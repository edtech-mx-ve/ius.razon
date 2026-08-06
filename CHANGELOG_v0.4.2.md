# Changelog v0.4.2 — Sprint 4.2

## Añadido

- nueva pestaña `Informe integral`;
- modelo `IntegralReportRequest`;
- modelo `IntegralLegalReport`;
- servicio `LegalReportService`;
- selección de ejecución de inferencia;
- selección de escenario base y comparado;
- resumen ejecutivo automático o personalizado;
- comparación narrativa de escenarios;
- hallazgos descriptivos;
- limitaciones e información faltante;
- recomendaciones de revisión;
- matriz de trazabilidad argumental;
- exportación integral a JSON, Markdown y DOCX;
- índice estático, encabezado, pie y numeración de páginas en DOCX;
- huella SHA-256 determinista;
- ocho pruebas automatizadas nuevas.

## Compatibilidad

- versión de aplicación: `0.4.2`;
- versión del reporte: `4.2.0`;
- versión del motor de inferencia: `3.2.0`;
- sin cambios en el esquema SQLite;
- compatible con bases creadas por v0.4.1.

## Seguridad y límites

- no consulta fuentes externas;
- no ejecuta contenido proporcionado por el usuario;
- no incluye secretos ni rutas locales en los reportes;
- valida que la ejecución y los escenarios pertenezcan al problema activo;
- conserva la advertencia de revisión humana obligatoria.
