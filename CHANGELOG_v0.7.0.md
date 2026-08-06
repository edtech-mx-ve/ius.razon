# IUS-Razón v0.7.0 — Sprint 4.5

## Añadido

- modo `OpenAI Responses API`;
- adaptador específico al endpoint oficial de Responses;
- clave leída exclusivamente desde `OPENAI_API_KEY`;
- endpoint fijo para reducir riesgo de SSRF;
- solicitud con `store=false` y sin herramientas;
- perfil de una sola llamada, cero reintentos y fallback local;
- tarifas configurables mediante variables de entorno;
- estimación previa y validación posterior de costo;
- auditoría sin prompt, respuesta, alias ni secretos;
- 16 pruebas automatizadas nuevas.

## Modificado

- `ProviderMode` incorpora OpenAI;
- la anonimización es obligatoria para OpenAI;
- la vista previa muestra límites, costo y códigos autorizados;
- el servicio diferencia OpenAI del proveedor JSON genérico;
- versión del paquete actualizada a `0.7.0`.

## Compatibilidad

- sin migraciones destructivas;
- no modifica expedientes, inferencias, argumentos ni informes;
- conserva modos local, prueba externa y proveedor JSON genérico;
- no añade dependencias de ejecución.

## Seguridad

- OpenAI permanece desactivado por defecto;
- la clave no se persiste ni se registra;
- las tarifas deben configurarse explícitamente;
- la primera integración exige una sola llamada y cero reintentos;
- el borrador permanece sujeto a aprobación humana.
