# Reporte técnico — Sprint 4.2.1

## Objetivo

Pulir la calidad semántica y editorial del informe jurídico integral sin
modificar el motor de inferencia ni el esquema de persistencia.

## Correcciones

### Argumentos manuales

La evaluación de soporte reconoce dos orígenes válidos:

- conclusión inferida por el motor;
- tesis manual explícita registrada por el usuario.

Por tanto, un argumento manual completo no se presenta como carente de una
conclusión inferida. El informe lo identifica expresamente como `Manual`.

### Concordancia

Los resúmenes y hallazgos generan formas correctas como:

```text
1 argumento adverso
2 argumentos favorables
1 objeción pendiente
0 objeciones pendientes
```

### Puntuación

Los propósitos de vínculos hecho–prueba se normalizan para evitar cierres como
`..`.

### Trazabilidad

La matriz integral incorpora:

```text
Origen: Manual
```

o:

```text
Origen: Derivado de una conclusión del motor
```

Cuando el argumento manual no tiene una conclusión `C-###`, el reporte muestra:

```text
No aplica (argumento manual)
```

## Arquitectura

- `argumentation_service.py`: evaluación funcional de completitud.
- `legal_report_service.py`: redacción, origen y puntuación.
- `report_models.py`: origen en filas de trazabilidad.
- `test_sprint_42.py`: pruebas de regresión editorial y semántica.

## Seguridad y compatibilidad

- Sin acceso a Internet.
- Sin verificación automática de fuentes.
- Sin cambios destructivos.
- Sin secretos ni datos del usuario incluidos en los paquetes.
- Motor de inferencia conservado en `3.2.0`.

## Verificación

En el entorno de construcción:

```text
70 pruebas automatizadas aprobadas
Compilación sintáctica correcta
Líneas Python de hasta 100 caracteres
DOCX válido mediante python-docx
```

Ruff y Mypy deben ejecutarse en el entorno local del proyecto.
