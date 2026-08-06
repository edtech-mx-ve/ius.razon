# Changelog v0.2.0

## Añadido

- problemas jurídicos `PJ-###`;
- normas `N-###`;
- jurisprudencia `J-###`;
- doctrina `D-###`;
- matriz problema–fuente;
- orientación y aplicabilidad;
- carga opcional de documentos para fuentes;
- metadatos SHA-256;
- nuevos contadores en el resumen;
- auditoría de fuentes y vínculos;
- tres pruebas específicas de Sprint 2.

## Cambiado

- versión del paquete a `0.2.0`;
- resumen del expediente ampliado;
- `updated_at` del expediente se actualiza al incorporar información;
- esquema SQLite ampliado de forma aditiva;
- corrección de estilo en el respaldo SQLite.

## Compatibilidad

Las bases v0.1.0, v0.1.1 y v0.1.2 son compatibles. La inicialización agrega tablas nuevas
sin eliminar registros existentes.
