# Changelog v0.3.2 — Sprint 3.1

## Añadido

- pestaña `Gestión razonamiento`;
- edición de premisas conservando código;
- edición y activación/desactivación de reglas conservando código;
- historial de versiones de premisas y reglas;
- respaldos SQLite antes de editar o eliminar;
- confirmación exacta para eliminaciones;
- bloqueo de eliminación por dependencias lógicas;
- instantánea completa de entradas para nuevas ejecuciones;
- comparación entre ejecuciones;
- exportación de reportes en JSON y Markdown;
- migración aditiva para bases v0.3.1;
- seis pruebas nuevas de Sprint 3.1.

## Cambiado

- versión del paquete: `0.3.2`;
- interfaz identificada como `Sprint 3.1 v0.3.2`;
- `ReasoningService` admite un directorio de respaldos;
- las ejecuciones nuevas persisten `input_snapshot_json`.

## Conservado

- motor lógico interno `3.0.0`;
- códigos existentes `A-###`, `R-###` y `C-###`;
- esquema y datos de expedientes, hechos, pruebas y fuentes;
- historial de ejecuciones anteriores;
- semántica de reglas estrictas y provisionales.

## Limitación

La derrota completa entre reglas rivales no forma parte de este incremento.
