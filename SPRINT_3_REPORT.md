# Reporte técnico — Sprint 3 v0.3.0

## Objetivo

Incorporar un motor de razonamiento jurídico simbólico y trazable sobre la base
fáctica, probatoria y documental construida en los sprints anteriores.

## Incremento entregado

- modelo de premisas;
- modelo de reglas y condiciones;
- reglas estrictas y provisionales;
- excepciones;
- encadenamiento hacia adelante;
- detección de contradicciones;
- bloqueo de defaults;
- conclusiones persistentes;
- trazas persistentes;
- huella de entrada;
- historial de ejecuciones;
- tres nuevas pestañas en Streamlit;
- migración aditiva.

## Decisiones técnicas

### Premisas atómicas

El motor no intenta inferir directamente desde narraciones libres. El usuario debe
convertir hechos y fuentes en premisas explícitas con una clave lógica estable.

### Reejecución completa

Cada corrida se calcula desde cero. Esto permite revisar conclusiones cuando cambian
premisas, excepciones o reglas sin mutar resultados históricos.

### Separación de responsabilidades

- Pydantic valida modelos.
- `ReasoningRepository` administra persistencia.
- `ReasoningEngine` ejecuta lógica pura.
- `ReasoningService` valida referencias y orquesta.
- Streamlit captura y presenta resultados.

### Soporte descriptivo

Los niveles insuficiente, bajo, medio y alto son heurísticos de completitud y
trazabilidad. No representan probabilidad de ganar un juicio.

## Esquema agregado

- `reasoning_assertions`
- `reasoning_rules`
- `reasoning_rule_conditions`
- `reasoning_runs`
- `reasoning_conclusions`
- `reasoning_traces`
- `reasoning_sequences`

## Compatibilidad

La migración fue diseñada para ejecutarse sobre una base v0.2.1. Solo crea tablas
nuevas y no modifica las existentes.

## Verificación

- 28 pruebas automatizadas aprobadas;
- compilación sintáctica completa;
- prueba de migración aditiva;
- prueba de persistencia de ejecuciones;
- prueba de regla estricta;
- prueba de default bloqueado por excepción;
- prueba de contradicción;
- prueba de encadenamiento provisional;
- prueba de premisas faltantes;
- prueba de referencias inexistentes.

## Criterios de aceptación

- crear premisas;
- crear reglas;
- ejecutar sobre un problema jurídico;
- producir conclusiones;
- identificar reglas bloqueadas;
- identificar premisas faltantes;
- detectar contradicciones;
- conservar la traza;
- conservar ejecuciones después de reiniciar;
- no alterar datos previos.

## Limitaciones

- no hay edición de premisas o reglas;
- la prioridad ordena, pero no resuelve completamente conflictos;
- no se implementa lógica temporal;
- no se implementa cuantificación probabilística;
- no se valida la corrección jurídica de una regla;
- toda conclusión requiere revisión humana.
