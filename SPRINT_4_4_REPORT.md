# Reporte técnico — Sprint 4.4

## Identificación

- producto: IUS-Razón;
- versión: 0.6.0;
- rama prevista: `feature/sprint-4.4`;
- incremento: proveedor LLM externo controlado;
- motor determinista: 3.2.0;
- formato de informe: 4.2.1.

## Objetivo

Conectar de forma opcional un endpoint LLM externo sin debilitar la
trazabilidad, privacidad, revisión humana ni reproducibilidad del sistema.

## Implementación

### Arquitectura

La programación estructurada mantiene el flujo de validación y generación.
La POO encapsula proveedores, configuración, transporte y repositorios.
Las funciones puras conservan anonimización, evaluación, huellas y estimación.
Las guardas bloquean configuraciones, contextos y presupuestos inseguros.

### Componentes

- `ExternalProviderSettings`: lectura y validación segura del entorno;
- `ExternalHTTPProvider`: adaptador HTTPS JSON;
- `UrllibJSONTransport`: transporte estándar con límite de respuesta;
- `ProviderMode`: local o externo;
- `ExternalConsent`: tres confirmaciones explícitas;
- `ProviderCallAuditRecord`: auditoría sin contenido ni secreto;
- `LLMAssistantService`: preflight, fallback, evaluación y persistencia;
- interfaz Streamlit: selección, vista previa, consentimiento y auditoría.

### Contrato JSON del endpoint

Solicitud:

```json
{
  "model": "external-model",
  "system_instruction": "...",
  "task": "Resumen del expediente",
  "instructions": "...",
  "context": [],
  "allowed_codes": ["PJ-001", "H-001"],
  "max_output_tokens": 2000
}
```

Respuesta mínima:

```json
{
  "output_text": "Texto con referencias [H-001]."
}
```

Respuesta extendida opcional:

```json
{
  "output_text": "Texto con referencias [H-001].",
  "request_id": "req-123",
  "usage": {
    "input_tokens": 1000,
    "output_tokens": 250
  }
}
```

## Seguridad

- externo desactivado por defecto;
- HTTPS obligatorio;
- clave únicamente en variable de entorno;
- clave no incluida en `repr`, resumen seguro, SQLite, logs ni payload;
- anonimización obligatoria;
- códigos seleccionados explícitamente;
- bloqueo por consentimiento incompleto;
- bloqueo por límites de entrada, salida o costo;
- señales de inyección requieren reconocimiento explícito;
- reintentos limitados;
- timeout controlado;
- fallback local opcional;
- revisión humana obligatoria.

## Persistencia

La migración añade columnas a `llm_drafts` y crea `llm_provider_calls`.
No elimina tablas, columnas ni registros. Los borradores de v0.5.x se
interpretan como modo simulado local mediante valores predeterminados.

## Pruebas

La suite contiene 100 pruebas:

- 88 pruebas previas;
- 12 pruebas nuevas de configuración, secretos, consentimiento, transporte,
  éxito externo, fallback, auditoría, costo y tokens.

Verificación de construcción realizada:

- `pytest`: 100 aprobadas;
- `compileall`: aprobado;
- longitud máxima de líneas Python: 100;
- Ruff y Mypy: deben confirmarse en el entorno local del usuario.

## Criterios de aceptación

- modo simulado funciona sin red;
- proveedor externo desactivado por defecto;
- ninguna clave persiste;
- toda llamada externa exige consentimiento;
- se respetan límites de uso;
- el fallback queda trazado;
- las respuestas siguen evaluándose;
- el usuario debe revisar y aprobar;
- la auditoría no contiene prompt ni secreto.

## Limitaciones

- el adaptador implementa un contrato JSON genérico;
- proveedores propietarios pueden necesitar un gateway;
- los tokens se estiman por caracteres antes de la llamada;
- el costo depende de tarifas configuradas por el usuario;
- una prueba real requiere endpoint HTTPS y credenciales del usuario;
- las guardas son defensas complementarias, no garantías absolutas.
