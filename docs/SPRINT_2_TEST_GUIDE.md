# Guía de prueba funcional — Sprint 2

## Caso de demostración

Usa un expediente mercantil ficticio con pago acreditado y entrega pendiente.

## 1. Problema jurídico

```text
Título: Exigibilidad de la entrega
Pregunta: ¿La obligación de entrega era exigible en la fecha pactada?
Contexto: Determinar si existía una obligación válida, vencida y no cumplida.
Estado: En análisis
```

Resultado: `PJ-001`.

## 2. Norma

```text
Jurisdicción: México
Materia: Mercantil
Instrumento: Código de prueba para demostración
Artículo: 100
Texto: La obligación pactada deberá cumplirse en el tiempo convenido.
Jerarquía: Ley federal
Versión: Versión ficticia 2026
Inicio de vigencia: 2026-01-01
Fuente: Caso sintético; no es una cita oficial.
```

Resultado: `N-001`.

## 3. Jurisprudencia

```text
Órgano: Tribunal de demostración
Identificador: DEMO-JUR-001
Hechos relevantes: Una parte pagó y la otra no entregó en la fecha convenida.
Problema jurídico: Exigibilidad de una obligación de entrega.
Criterio: El vencimiento y el cumplimiento de la contraprestación son relevantes.
Carácter: Pendiente de verificar
Similitudes: Pago y fecha de entrega.
Diferencias: El precedente es enteramente ficticio.
```

Resultado: `J-001`.

## 4. Doctrina

```text
Autor: Autora de demostración
Obra: Teoría ficticia de las obligaciones
Año: 2026
Concepto: Exigibilidad
Síntesis: La exigibilidad requiere obligación válida y vencida.
Referencia: Autora de demostración. (2026). Teoría ficticia de las obligaciones.
Función: Definir el concepto central.
```

Resultado: `D-001`.

## 5. Matriz

Vincula las tres fuentes con `PJ-001` y explica separadamente su aplicabilidad.

Resultado esperado:

```text
Problemas jurídicos: 1
Normas: 1
Jurisprudencia: 1
Doctrina: 1
Vínculos problema–fuente: 3
```

## 6. Persistencia

Detén y reinicia Streamlit. Los cinco contadores y los registros deben permanecer.

## 7. Automatización

```powershell
pytest -v
ruff check .
mypy src
```
