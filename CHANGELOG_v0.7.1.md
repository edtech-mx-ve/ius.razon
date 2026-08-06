# CHANGELOG v0.7.1

## Sprint 4.5.1 — Ollama local gratuito

### Añadido

- proveedor `OllamaLocalProvider` para `http://127.0.0.1:11434/api/chat`;
- configuración `OllamaProviderSettings` sin secretos;
- modelo predeterminado `qwen3:1.7b`;
- payload con `stream=false`, `think=false`, temperatura `0` y cero reintentos;
- límites separados de entrada, salida y ventana de contexto;
- costo auditable de USD 0;
- fallback al proveedor simulado cuando Ollama no responde;
- opción `Ollama local gratuito` en la interfaz;
- pruebas de endpoint local, payload, respuesta, auditoría y fallback.

### Cambiado

- versión del paquete a `0.7.1`;
- OpenAI y el proveedor externo genérico dejan de estar conectados a `app.py`;
- la interfaz activa solo ofrece modo simulado, Ollama local y prueba controlada;
- anonimización obligatoria para Ollama;
- documentación orientada a ejecución gratuita y local.

### Seguridad

- se rechazan hosts que no sean `127.0.0.1`, `localhost` o `::1`;
- se rechazan puertos distintos de `11434`;
- se exige la ruta exacta `/api/chat`;
- no se envían claves ni encabezados de autorización;
- no se realizan reintentos automáticos;
- las respuestas requieren revisión humana antes de aprobarse.

### Compatibilidad

- sin migraciones destructivas;
- los borradores y auditorías existentes permanecen intactos;
- el motor determinista continúa en la versión `3.2.0`.
