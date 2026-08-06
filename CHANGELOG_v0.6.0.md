# IUS-Razón v0.6.0 — Sprint 4.4

## Añadido

- proveedor HTTPS JSON externo opcional y desacoplado;
- configuración exclusiva mediante variables de entorno;
- validación de endpoint HTTPS y ausencia de credenciales en URL;
- selección explícita de proveedor;
- vista previa del contexto externo;
- anonimización obligatoria para llamadas externas;
- consentimiento en tres pasos;
- límites de tokens de entrada y salida;
- límites de costo, tiempo y reintentos;
- fallback opcional al proveedor simulado local;
- auditoría separada de llamadas sin prompt ni secretos;
- tokens, costo estimado, request ID y estado de fallback en borradores;
- tabla `llm_provider_calls`;
- migración aditiva de `llm_drafts`;
- 12 pruebas nuevas del Sprint 4.4.

## Seguridad

- el proveedor externo permanece desactivado por defecto;
- la clave API nunca se persiste ni se registra;
- el encabezado `Authorization` existe solo en memoria;
- las señales de instrucciones incrustadas bloquean el envío hasta confirmación;
- la revisión humana sigue siendo obligatoria;
- ningún borrador modifica entidades jurídicas.

## Compatibilidad

- motor determinista: 3.2.0;
- formato de informe: 4.2.1;
- modo simulado v0.5.1 conservado;
- bases SQLite existentes se amplían sin eliminar registros;
- Python mínimo declarado: 3.11.
