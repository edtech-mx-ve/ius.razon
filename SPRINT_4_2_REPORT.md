# Sprint 4.2 — Informe jurídico integral

## Objetivo

Integrar en un solo artefacto reproducible la información del expediente, la
inferencia determinista, la red argumental y la comparación de escenarios.

## Incremento funcional

La versión `0.4.2` incorpora una nueva capa de reporte sin modificar el motor
de razonamiento ni el esquema de persistencia.

### Entradas

- expediente y problema jurídico;
- ejecución de inferencia seleccionada;
- escenario base;
- escenario comparado opcional;
- título y objeto del informe;
- resumen ejecutivo opcional;
- conclusiones del analista;
- recomendaciones;
- limitaciones adicionales;
- opciones de detalle.

### Salidas

- JSON integral;
- Markdown integral;
- DOCX integral.

### Secciones del informe

1. Identificación y alcance.
2. Resumen ejecutivo.
3. Metodología y advertencias.
4. Antecedentes del expediente.
5. Hechos y pruebas.
6. Fuentes jurídicas vinculadas.
7. Inferencia y trazabilidad.
8. Argumentación jurídica.
9. Escenarios alternativos.
10. Hallazgos y conclusiones.
11. Limitaciones e información faltante.
12. Recomendaciones de revisión.
13. Matriz de trazabilidad.
14. Huellas y reproducibilidad.

## Arquitectura

### Programación estructurada

La interfaz organiza el flujo:

```text
selección → validación → construcción → vista previa → exportación
```

### Programación orientada a objetos

`LegalReportService` coordina servicios existentes sin acceder directamente a
variables globales ni duplicar reglas de dominio.

### Programación funcional

Las transformaciones deterministas se delegan a funciones para:

- normalización de líneas;
- cálculo de huellas;
- generación de hallazgos;
- construcción de limitaciones;
- comparación narrativa;
- matriz de trazabilidad.

### Robustez

- validación Pydantic;
- rechazo de ejecución perteneciente a otro problema;
- rechazo de escenarios base y comparado idénticos;
- degradación controlada cuando no hay argumentos o fuentes;
- exportaciones sin ejecución de contenido externo;
- advertencias jurídicas visibles;
- sin sobrescritura de la base de datos.

## Reproducibilidad

La huella del informe se calcula sobre:

- solicitud;
- expediente;
- problema;
- partes;
- hechos;
- pruebas;
- fuentes;
- inferencia;
- argumentos;
- relaciones;
- escenarios;
- hallazgos;
- limitaciones;
- matriz de trazabilidad.

La hora de descarga no forma parte de la huella.

## Pruebas

Se agregaron ocho pruebas para:

- integración de todas las capas;
- comparación narrativa;
- reproducibilidad del hash y JSON;
- secciones Markdown;
- validez y estructura del DOCX;
- preservación de textos del analista;
- aislamiento entre problemas;
- rechazo de escenarios iguales.

Resultado de construcción:

```text
66 pruebas aprobadas
compilación sintáctica correcta
líneas Python dentro de 100 caracteres
DOCX renderizado en 7 páginas
inspección visual completa sin recortes ni solapamientos
```

Ruff y Mypy no estaban disponibles en el entorno de construcción. Deben
ejecutarse en el entorno local del proyecto.

## Criterios de aceptación

- la versión visible es `0.4.2`;
- la base activa se conserva;
- una ejecución puede convertirse en informe integral;
- `SCN-001` y `SCN-002` pueden compararse;
- la narrativa detecta argumentos y relaciones añadidas;
- el DOCX contiene índice, secciones, tablas, pie y numeración;
- JSON y Markdown conservan la misma huella;
- las 66 pruebas se aprueban;
- Ruff y Mypy se aprueban localmente.

## Limitaciones

- no existe firma electrónica;
- no se verifica vigencia de fuentes;
- no se genera opinión jurídica autónoma;
- no se consulta un LLM;
- no se genera PDF desde la interfaz;
- el índice del DOCX es estático.
