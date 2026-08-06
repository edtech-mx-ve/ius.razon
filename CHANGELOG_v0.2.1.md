# Changelog v0.2.1 — Sprint 2.1

## Añadido

- Pestaña **Corrección segura**.
- Edición de problemas jurídicos, normas, jurisprudencia y doctrina.
- Edición y desvinculación de relaciones problema–fuente.
- Confirmación exacta por código para eliminaciones.
- Protección de entidades con vínculos activos.
- Respaldos automáticos antes de operaciones sensibles.
- Auditoría de actualizaciones, desvinculaciones y eliminaciones.
- Secuencias persistentes de códigos.
- Archivo histórico de documentos reemplazados o eliminados.
- Ocho pruebas nuevas para corrección, integridad y persistencia.

## Cambiado

- Versión del proyecto: `0.2.0` → `0.2.1`.
- Los nombres de respaldo incluyen microsegundos para evitar colisiones.
- Vincular una fuente crea un respaldo previo porque la operación puede actualizar
  una relación existente.
- Los documentos sustituidos ya no se destruyen: se mueven a `archived_uploads/`.

## Compatibilidad

- Compatible con bases v0.1.2 y v0.2.0.
- Migración aditiva mediante `CREATE TABLE IF NOT EXISTS`.
- No modifica los códigos ni los registros existentes.
