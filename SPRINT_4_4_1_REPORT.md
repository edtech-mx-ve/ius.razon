# Sprint 4.4.1 — Prueba externa controlada

## Objetivo

Validar de extremo a extremo el flujo diseñado para un proveedor externo antes
de utilizar red, credenciales o consumo facturable.

## Incremento funcional

Se incorporó un tercer modo de proveedor:

- **Simulado local:** flujo asistivo habitual.
- **Prueba externa controlada:** proveedor falso local que ejercita
  consentimiento, límites, contrato de respuesta y auditoría.
- **Proveedor externo:** permanece desactivado salvo configuración expresa.

La prueba controlada genera una sola respuesta determinista y conserva el flujo
de revisión humana. No realiza llamadas HTTPS y no necesita una clave API.

## Perfil de seguridad

| Control | Valor |
|---|---:|
| Entrada máxima | 2048 tokens |
| Salida máxima | 256 tokens |
| Costo máximo | USD 0.01 |
| Tiempo máximo | 15 segundos |
| Reintentos | 0 |
| Fallback local | Obligatorio |
| Anonimización | Obligatoria |
| Consentimiento | Tres confirmaciones |
| Confirmación adicional | Una sola invocación |
| Guardado automático aprobado | No |

## Arquitectura

- `ControlledExternalTestPolicy`: validaciones puras del perfil.
- `ControlledExternalTestProvider`: adaptador local compatible con
  `LLMProvider`.
- `LLMAssistantService`: selección de proveedor, preflight y auditoría.
- `llm_assistant_view`: vista previa, consentimiento y ejecución.
- `test_sprint_441.py`: doce pruebas nuevas.

La programación estructurada organiza el flujo de preflight; las clases
encapsulan proveedor y política; las funciones deterministas mantienen
transformaciones reproducibles.

## Datos y persistencia

No se modifica el esquema SQLite. El nuevo modo utiliza las tablas ya
existentes de borradores y auditoría. No almacena claves, prompts de sistema ni
contenido de respuesta en el registro de auditoría.

## Verificación realizada en construcción

- Compilación sintáctica: aprobada.
- Pruebas automatizadas: 112 aprobadas.
- Pruebas nuevas: 12.
- Líneas Python mayores de 100 caracteres: 0.
- Llamadas de red durante pruebas: 0.

Ruff y Mypy deben confirmarse en el entorno local del proyecto.

## Criterios de aceptación

- La prueba funciona sin Internet.
- No solicita clave API.
- Anonimización y consentimiento son obligatorios.
- Solo permite cero reintentos.
- El costo máximo es USD 0.01.
- El fallback local permanece activado.
- La auditoría registra `Externa: No`.
- El borrador queda `Generado` hasta revisión humana.
- Ruff, Mypy y Pytest pasan localmente.

## Limitaciones

Este modo no valida la compatibilidad con una API comercial concreta ni la
calidad de un modelo remoto. Valida únicamente el contrato, los guardrails y
la trazabilidad del flujo antes de una llamada real.
