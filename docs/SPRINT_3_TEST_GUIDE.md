# Guía de prueba funcional — Sprint 3

## Preparación

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
pytest -v
ruff check .
mypy src
streamlit run app.py
```

Abre `http://localhost:8501` y selecciona el expediente ya utilizado.

## Premisas sugeridas para PJ-001

### A-001

```text
Clave: pago_acreditado
Valor: Verdadero
Enunciado: La compradora acreditó el pago total del precio.
Justificación: El comprobante registrado respalda inicialmente el pago.
Soportes: H-001, P-001, N-004
```

### A-002

```text
Clave: obligacion_entrega_valida
Valor: Verdadero
Enunciado: Existía una obligación contractual válida de entregar el equipo.
Justificación: El contrato y las normas registradas describen la obligación.
Soportes: N-002
```

### A-003

```text
Clave: plazo_vencido
Valor: Verdadero
Enunciado: El plazo pactado de entrega se encuentra vencido.
Justificación: La fecha de entrega registrada ya transcurrió.
Soportes: H-002, N-003
```

### A-004

```text
Clave: entrega_realizada
Valor: Falso
Enunciado: La entrega del equipo no se realizó.
Justificación: El hecho se mantiene controvertido, pero no hay entrega acreditada.
Soportes: H-002
```

### A-005

```text
Clave: causa_justificante
Valor: Desconocido
Enunciado: Existe una causa jurídicamente relevante que justifique la falta de entrega.
Justificación: La contraparte la menciona, pero todavía no está acreditada.
Soportes:
```

## Regla provisional R-001

```text
Nombre: Incumplimiento provisional de entrega
Tipo: Provisional
Prioridad: 100
Conclusión: incumplimiento_entrega
Valor: Verdadero
Enunciado: Existe soporte inicial para sostener un incumplimiento de entrega.

Prerrequisitos:
obligacion_entrega_valida=Verdadero
pago_acreditado=Verdadero
plazo_vencido=Verdadero
entrega_realizada=Falso

Excepciones:
causa_justificante=Verdadero

Fundamentos:
N-001, N-003, J-001, D-001

Explicación:
Si la obligación era válida y exigible, el pago fue acreditado, venció el plazo y
no se realizó la entrega, puede inferirse provisionalmente incumplimiento, salvo
causa justificante acreditada.
```

## Regla estricta R-002

```text
Nombre: Indicio fáctico de falta de entrega
Tipo: Estricta
Prioridad: 90
Conclusión: indicio_factual_incumplimiento
Valor: Verdadero
Enunciado: Dentro del modelo existe un indicio fáctico de incumplimiento.

Prerrequisitos:
pago_acreditado=Verdadero
plazo_vencido=Verdadero
entrega_realizada=Falso

Excepciones:

Fundamentos:
N-003, N-004

Explicación:
La concurrencia de pago, vencimiento y falta de entrega constituye un indicio
fáctico dentro del modelo, sin decidir todavía la consecuencia jurídica final.
```

## Ejecución esperada

En `Inferencia`, selecciona PJ-001 y ejecuta.

Resultado esperado:

- R-001 aplicada como regla provisional;
- R-002 aplicada como regla estricta;
- dos conclusiones;
- cero contradicciones;
- traza completa;
- fuentes y premisas visibles.

## Prueba de excepción

Agrega otra premisa:

```text
Clave: causa_justificante
Valor: Verdadero
Enunciado: Se acreditó una causa justificante.
Justificación: Prueba de funcionamiento del bloqueo.
Soportes:
```

Ejecuta de nuevo.

Resultado esperado:

- R-001 bloqueada por excepción;
- R-002 sigue aplicándose;
- la corrida anterior permanece disponible.

## Prueba de contradicción

Agrega una premisa opuesta:

```text
Clave: entrega_realizada
Valor: Verdadero
Enunciado: La entrega sí se realizó.
Justificación: Premisa deliberadamente contradictoria para probar el motor.
Soportes:
```

Ejecuta de nuevo.

Resultado esperado:

- `entrega_realizada` aparece como premisa contradictoria;
- las reglas que dependan de esa clave no se aplican;
- la traza indica `Premisas contradictorias`;
- el resumen informa al menos una contradicción.

## Persistencia

Detén y reinicia Streamlit. Deben seguir disponibles:

- premisas;
- reglas;
- todas las ejecuciones;
- conclusiones;
- trazas.
