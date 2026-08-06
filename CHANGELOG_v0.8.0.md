# CHANGELOG — IUS-Razón v0.8.0

## Sprint 5.1 — Privacidad y datos de demostración

### Añadido

- Centro de privacidad en Streamlit.
- Escáner determinista de patrones sensibles.
- Detección de correo, CURP, RFC, CLABE, tarjeta, teléfono, secretos,
  rutas locales y posibles nombres reales.
- Reporte JSON seguro sin valores originales.
- Modo de demostración pública mediante variables de entorno.
- Bloqueo de cargas y ocultamiento de rutas en modo público.
- Gate opcional de exportación condicionado a un análisis limpio.
- Pruebas automatizadas de configuración, reglas, truncamiento y política.

### Cambiado

- Versión del paquete a `0.8.0`.
- Encabezado de la aplicación a Sprint 5.1.
- Botones de exportación con control de privacidad.
- Cargadores de archivos deshabilitados cuando el modo público está activo.

### Seguridad

- Los hallazgos almacenan huellas SHA-256 truncadas, no datos sensibles.
- Los logs solo registran conteos, identificadores técnicos y resultado.
- No se modifica el esquema SQLite.
- El modo público fuerza cargas deshabilitadas, rutas ocultas y gate de exportación.

### Limitaciones

- La detección es heurística y puede producir falsos positivos o falsos negativos.
- No anonimiza automáticamente expedientes reales.
- No sustituye revisión legal, de privacidad ni de seguridad.
