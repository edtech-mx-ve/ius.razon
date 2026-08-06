# Cambios v0.6.1 — Sprint 4.4.1

## Añadido

- Modo **Prueba externa controlada** disponible sin red ni clave API.
- Proveedor falso `ius-razon-external-test-v1` con contrato normalizado.
- Perfil fijo: 2048 tokens de entrada, 256 de salida, USD 0.01,
  15 segundos, cero reintentos y fallback local obligatorio.
- Confirmación explícita de una sola invocación.
- Auditoría diferenciada con `Externa: No`.
- Doce pruebas automatizadas nuevas.

## Seguridad

- La prueba no abre conexiones de red.
- No lee ni persiste claves.
- Exige anonimización, consentimiento completo y revisión humana.
- No aprueba ni incorpora borradores automáticamente.

## Compatibilidad

- Sin migraciones SQLite.
- Conserva los modos Simulado local y Proveedor externo.
- Los borradores y auditorías anteriores permanecen disponibles.
