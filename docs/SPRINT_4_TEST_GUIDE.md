# Guía de prueba funcional — Sprint 4

## Objetivo

Validar creación de argumentos, contraargumentos, réplicas, trazabilidad,
diagnóstico y exportación para `PJ-001`.

## Preparación

En `Gestión razonamiento → Reglas` deja:

```text
R-001: activa
Reglas rivales de prueba: desactivadas
Reglas dependientes de prueba: desactivadas
```

En `Inferencia`, ejecuta `PJ-001` y confirma una conclusión vigente:

```text
incumplimiento_entrega = Verdadero
```

## Prueba 1 — Argumento favorable

Abre `Argumentación`.

Selecciona `PJ-001` y, en `Crear desde una conclusión`, elige la conclusión
vigente de incumplimiento.

Completa:

```text
Título:
Incumplimiento contractual por falta de entrega

Posición:
Favorable

Estado:
Sustentado

Pretensión:
Debe reconocerse, dentro del modelo, que existe soporte para considerar
incumplida la obligación contractual de entrega.

Desarrollo:
La obligación de entrega aparece como válida, exigible y vencida. El expediente
registra pago acreditado y falta de entrega. La regla R-001 conecta esas
premisas con la conclusión provisional. La conclusión permanece sujeta a la
verificación profesional de causas justificantes, prórrogas y aplicabilidad de
las fuentes.
```

Resultado esperado:

```text
ARG-001 creado
Trazabilidad automática a C, R, A, H, P y fuentes disponibles
Soporte descriptivo Alto cuando están presentes los cinco componentes
```

## Prueba 2 — Argumento adverso

En `Crear argumento manual` registra:

```text
Título:
Insuficiencia para atribuir incumplimiento definitivo

Posición:
Adverso

Clave:
incumplimiento_entrega

Enunciado:
No existe soporte suficiente para afirmar un incumplimiento definitivo.

Valor:
Falso

Estado:
No resuelto

Pretensión:
La conclusión favorable no debe tratarse como definitiva mientras permanezcan
sin resolver posibles causas justificantes o modificaciones del plazo.

Desarrollo:
Las premisas causa_justificante y prorroga_acordada permanecen desconocidas.
La ausencia de información no demuestra por sí sola que exista una excepción,
pero limita la fuerza de una atribución definitiva.

Premisas:
A-006, A-007

Fuentes:
J-001, D-001
```

Ajusta los códigos si tu expediente usa otros.

Resultado esperado:

```text
ARG-002 creado
Información faltante visible
```

## Prueba 3 — Ataque

En `Relacionar argumentos`:

```text
Origen: ARG-002
Tipo: Ataca
Destino: ARG-001
Justificación:
El argumento adverso cuestiona que la conclusión provisional pueda tratarse
como definitiva mientras existan excepciones no esclarecidas.
```

Resultado esperado:

```text
REL-001 creado
Conflictos/ataques: 1
ARG-002 aparece como objeción pendiente
```

## Prueba 4 — Réplica

Crea un tercer argumento favorable desde la conclusión vigente:

```text
Título:
Réplica sobre el carácter provisional de la conclusión

Posición:
Favorable

Estado:
Respondido

Pretensión:
La objeción no elimina la conclusión provisional porque ninguna excepción está
actualmente acreditada.

Desarrollo:
El modelo distingue desconocimiento de falsedad. Las excepciones desconocidas
limitan la conclusión, pero no bloquean R-001 mientras no tengan valor
Verdadero. La conclusión sigue siendo provisional y revisable.
```

Relaciona:

```text
Origen: ARG-003
Tipo: Responde
Destino: ARG-002
```

Resultado esperado:

```text
ARG-002 deja de aparecer entre objeciones pendientes
```

## Prueba 5 — Exportación

Descarga:

```text
JSON
Markdown
DOCX
```

Verifica:

- misma huella SHA-256;
- argumentos y relaciones presentes;
- información faltante presente;
- advertencia de uso presente;
- el DOCX abre correctamente.

## Criterio de cierre

```text
Argumento favorable creado
Argumento adverso creado
Ataque registrado
Réplica registrada
Objeción resuelta
Trazabilidad validada
Información faltante visible
JSON, Markdown y DOCX descargados
50 pruebas automatizadas aprobadas
```
