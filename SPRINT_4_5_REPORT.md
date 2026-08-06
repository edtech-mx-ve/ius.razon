# Reporte técnico — Sprint 4.5

## Incremento

**IUS-Razón v0.7.0 — Adaptador específico OpenAI Responses API**

## Objetivo

Integrar un proveedor comercial específico sin debilitar el motor
determinista, la selección de contexto, la trazabilidad, la anonimización,
la auditoría ni la revisión humana.

## Implementación

### Arquitectura

- `OpenAIProviderSettings`: configuración segura y validada.
- `OpenAIResponsesProvider`: adaptación del contrato interno al endpoint
  Responses API.
- `LLMAssistantService`: preflight, fallback, auditoría y persistencia.
- `llm_assistant_view`: selección y consentimiento.
- `ProviderMode.OPENAI`: modo explícito y auditable.

### Contrato de salida

La respuesta se normaliza en `ProviderResponse` con:

- texto;
- proveedor y modelo;
- identificador de solicitud;
- tokens de entrada y salida;
- costo estimado;
- indicador de llamada externa;
- indicador de fallback.

### Seguridad

- endpoint fijo `https://api.openai.com/v1/responses`;
- clave únicamente desde `OPENAI_API_KEY`;
- `store=false`;
- sin herramientas, navegación ni ejecución remota;
- contexto anonimizado;
- selección exacta de códigos;
- consentimiento explícito;
- una llamada real;
- cero reintentos;
- fallback local obligatorio;
- auditoría sin contenido ni secreto.

## Pruebas

Se añadieron 16 pruebas para:

- configuración desactivada;
- clave requerida;
- tarifas requeridas;
- redacción del secreto;
- anonimización;
- forma del payload;
- `store=false`;
- ausencia de herramientas;
- extracción de texto;
- uso y costo;
- consentimiento;
- llamada única;
- cero reintentos;
- fallback obligatorio;
- auditoría;
- bloqueo previo por costo.

Total ejecutado en construcción: **128 pruebas aprobadas**.

Verificaciones adicionales:

- compilación sintáctica de `src` y `app.py`: aprobada;
- líneas Python mayores de 100 caracteres: 0;
- llamadas reales durante pruebas: 0;
- Ruff y Mypy: pendientes de confirmación en el entorno local del usuario.

## Criterios de aceptación

- versión `0.7.0`;
- Ruff sin errores;
- Mypy sin errores;
- 128 pruebas aprobadas;
- OpenAI oculto mientras no esté configurado;
- ninguna llamada real durante pruebas;
- ninguna clave en Git, SQLite o logs;
- prueba funcional local de configuración;
- primera llamada real separada y expresamente autorizada.

## Limitaciones

- no se ejecutó una llamada real durante la construcción;
- la disponibilidad del modelo depende de la cuenta;
- las tarifas son externas al código y deben verificarse;
- la estimación de tokens es aproximada;
- la trazabilidad formal no equivale a corrección jurídica;
- la salida requiere revisión humana.
