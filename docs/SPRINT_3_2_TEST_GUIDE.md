# Guía de prueba funcional — Sprint 3.2

## Objetivo

Validar prioridad, tipo, especificidad, empate y retirada de conclusiones
dependientes sin alterar definitivamente el escenario `PJ-001`.

## Preparación

Confirma:

```text
A-001 pago_acreditado = Verdadero
A-002 obligacion_entrega_valida = Verdadero
A-003 obligacion_exigible = Verdadero
A-004 plazo_vencido = Verdadero
A-005 entrega_realizada = Falso
A-006 causa_justificante = Desconocido
A-007 prorroga_acordada = Desconocido
```

Conserva `R-001` activa.

## Prueba 1 — Escenario base

Ejecuta `PJ-001`.

Esperado:

```text
R-001 aplicada
incumplimiento_entrega=Verdadero
```

Exporta JSON y Markdown.

## Prueba 2 — Derrota por prioridad

Crea una regla rival:

```text
Nombre:
Negación prioritaria de incumplimiento para prueba

Tipo:
Provisional

Prioridad:
200

Clave de conclusión:
incumplimiento_entrega

Valor:
Falso

Enunciado:
No existe soporte suficiente para considerar incumplida la obligación.

Prerrequisitos:
obligacion_entrega_valida=Verdadero
obligacion_exigible=Verdadero
plazo_vencido=Verdadero
entrega_realizada=Falso
pago_acreditado=Verdadero

Excepciones:
vacío

Fundamentos:
N-001, N-002, N-003, N-004, J-001, D-001
```

Usa como explicación:

```text
Regla rival creada únicamente para validar la política de derrota del motor.
Comparte la clave de conclusión con R-001, produce el valor opuesto y tiene una
prioridad mayor. No representa una conclusión jurídica definitiva.
```

Ejecuta.

Esperado:

```text
Conclusión vigente:
incumplimiento_entrega=Falso

Rival:
Regla provisional aplicada

R-001:
Derrotada por menor prioridad
```

El resumen debe mostrar al menos:

```text
Conflictos: 1
Reglas derrotadas: 1
Empates: 0
```

## Prueba 3 — Preferencia de regla estricta

En `Gestión razonamiento`, cambia la regla rival:

```text
Prioridad: 100
Tipo: Estricta
Excepciones: vacío
```

Mantén `R-001` provisional con prioridad `100`.

Ejecuta.

Esperado:

```text
Regla rival estricta aplicada
R-001 derrotada por regla estricta rival
incumplimiento_entrega=Falso
```

## Prueba 4 — Especificidad

Cambia la regla rival a:

```text
Tipo: Provisional
Prioridad: 100
```

Añade un prerrequisito adicional confirmado, por ejemplo:

```text
pago_acreditado=Verdadero
```

La rival debe tener más prerrequisitos distintos que `R-001`. Si `R-001` ya
incluye esa clave, crea primero una premisa de prueba válida y úsala solo en la
rival.

Ejecuta.

Esperado:

```text
Regla rival aplicada
R-001 derrotada por menor especificidad
```

## Prueba 5 — Empate exacto

Haz que ambas reglas tengan:

```text
misma prioridad
mismo tipo
mismo número de prerrequisitos distintos
```

Los enunciados pueden ser diferentes; el ranking debe ser idéntico.

Ejecuta.

Esperado:

```text
Conclusiones rivales suspendidas
Empates: 2
Conflictos no resueltos: 1
```

Ambas trazas deben indicar:

```text
Empate entre reglas rivales
```

No debe aparecer como vigente ninguna de estas conclusiones:

```text
incumplimiento_entrega=Verdadero
incumplimiento_entrega=Falso
```

## Prueba 6 — Retirada dependiente

Para una prueba aislada, crea una cadena:

```text
R-A:
premisa_base=Verdadero
→ resultado_intermedio=Verdadero
Prioridad 100

R-B:
premisa_derivada=Verdadero
→ resultado_intermedio=Falso
Prioridad 200

R-C:
resultado_intermedio=Verdadero
→ resultado_dependiente=Verdadero

R-D:
premisa_base=Verdadero
→ premisa_derivada=Verdadero
```

La primera iteración puede activar `resultado_intermedio=Verdadero`. Cuando
`R-D` active `premisa_derivada`, `R-B` derrota a `R-A`. El resultado final debe
mostrar:

```text
R-A derrotada por menor prioridad
R-C retirada por dependencia derrotada
resultado_dependiente ausente
resultado_intermedio=Falso
```

Esta prueba puede realizarse en un expediente sintético separado para no
contaminar `PJ-001`.

## Comparación de ejecuciones

Compara la ejecución base con una ejecución de derrota.

Debes ver:

```text
added_conclusions
removed_conclusions
changed_statuses
changed_rule_outcomes
```

Ejemplo:

```text
R-001: Regla provisional aplicada → Derrotada por menor prioridad
```

## Exportación

Descarga JSON y Markdown de:

- escenario base;
- derrota por prioridad;
- empate exacto.

El Markdown debe contener:

```text
## Resolución de conflictos
```

## Restauración

Al finalizar:

1. desactiva o elimina la regla rival con confirmación exacta;
2. confirma `R-001` activa;
3. restaura prioridades y tipos originales;
4. ejecuta `PJ-001`.

Esperado:

```text
Reglas aplicadas: 1
Conclusiones: 1
incumplimiento_entrega=Verdadero
Tipo: Provisional
```

## Validación técnica

```powershell
ruff check .
mypy src
pytest -v
```

Esperado:

```text
All checks passed!
Success: no issues found in 17 source files
42 passed
```
