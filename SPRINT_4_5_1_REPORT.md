# Reporte Sprint 4.5.1 — IUS-Razón v0.7.1

## Objetivo

Sustituir el flujo comercial activo por un proveedor generativo gratuito que
se ejecute exclusivamente en el equipo del usuario mediante Ollama, sin claves
API, cobros por solicitud ni envío del expediente a Internet.

## Implementación

### Configuración

`src/ius_razon/security/llm_ollama_config.py` valida:

- endpoint local fijo o equivalente de loopback;
- puerto `11434`;
- ruta `/api/chat`;
- modelo con caracteres permitidos;
- cero reintentos;
- límites de entrada, salida y contexto compatibles.

### Proveedor

`OllamaLocalProvider`:

- usa `POST /api/chat`;
- establece `stream=false` y `think=false`;
- limita `num_predict`;
- fija temperatura determinista;
- no usa autenticación;
- normaliza `message.content`;
- registra `prompt_eval_count` y `eval_count`;
- marca `external_call=false` y costo `0.0`.

### Orquestación

`LLMAssistantService`:

- valida anonimización;
- aplica límites antes de invocar;
- bloquea señales de instrucciones incrustadas no revisadas;
- audita bloqueos, éxito y fallback;
- usa el proveedor simulado si Ollama no responde y el fallback está habilitado.

### Interfaz

La pestaña `Asistente IA` ofrece:

1. Simulado local.
2. Ollama local gratuito.
3. Prueba externa controlada.

Los proveedores comerciales no se muestran ni se construyen desde `app.py`.

## Pruebas

Se añadieron pruebas para:

- configuración predeterminada;
- rechazo de host remoto, puerto y ruta;
- rechazo de reintentos;
- anonimización obligatoria;
- payload sin autenticación;
- `think=false` y `stream=false`;
- normalización de tokens;
- rechazo de respuestas vacías;
- resumen seguro;
- generación y auditoría local;
- fallback determinista;
- bloqueo por límite de salida;
- ausencia de OpenAI en el flujo activo.

## Criterios de aceptación

- Ollama funciona sin clave API.
- Solo se permite loopback local.
- El costo registrado es USD 0.
- La anonimización es obligatoria.
- Las referencias internas se evalúan.
- Toda salida requiere aprobación humana.
- No hay migraciones destructivas.
- La suite automatizada pasa.
- Ruff y Mypy deben confirmarse en el entorno local del usuario.

## Limitaciones

- la primera carga del modelo puede tardar;
- el rendimiento depende de CPU, GPU y memoria del equipo;
- el cálculo previo de tokens es aproximado;
- un modelo pequeño puede requerir edición humana significativa;
- el sistema no verifica vigencia ni aplicabilidad jurídica de las fuentes.
