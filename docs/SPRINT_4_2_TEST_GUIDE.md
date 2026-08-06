# Guía de prueba funcional — Sprint 4.2

## Precondiciones

- IUS-Razón v0.4.2 instalado;
- base activa conservada;
- `PJ-001` disponible;
- al menos una ejecución con conclusión;
- `ARG-001`, `ARG-002` y `ARG-003` registrados;
- `SCN-001` y `SCN-002` registrados.

## 1. Validación técnica

```powershell
ruff check .
mypy src
pytest -v
```

Resultado esperado:

```text
All checks passed!
Success: no issues found
66 passed
```

## 2. Generación del informe

Abre:

```text
Informe integral
```

Selecciona:

```text
Problema:
PJ-001

Ejecución:
una ejecución con incumplimiento_entrega=Verdadero

Escenario base:
SCN-001 · Escenario sin réplica acreditada

Escenario comparado:
SCN-002 · Escenario con réplica argumental
```

Título:

```text
Informe jurídico integral sobre incumplimiento de entrega
```

Objeto y alcance:

```text
Integrar los hechos, pruebas, fuentes, inferencia, argumentos y escenarios
registrados para apoyar una revisión jurídica humana del problema PJ-001.
```

Deja vacío el resumen ejecutivo para probar la generación automática.

Activa:

```text
Incluir desarrollo completo
Incluir detalle de fuentes
Incluir matriz de trazabilidad
```

Pulsa:

```text
Generar informe integral
```

## 3. Vista previa

Verifica:

- conclusiones mayor o igual a 1;
- argumentos igual a 3;
- relaciones igual a 2;
- objeciones pendientes igual a 0 para la red completa;
- huella SHA-256 visible;
- hallazgos descriptivos;
- comparación narrativa disponible.

La narrativa esperada debe mencionar:

```text
ARG-003
REL-002
Las objeciones pendientes disminuyen en 1.
```

## 4. JSON

Descarga el JSON y comprueba:

```text
report_version = 4.2.0
reasoning.run.engine_version = 3.2.0
scenario_comparison.added_argument_codes contiene ARG-003
scenario_comparison.added_relation_codes contiene REL-002
input_hash está presente
```

## 5. Markdown

Comprueba estas secciones:

```text
7. Inferencia y trazabilidad
8. Argumentación jurídica
9. Escenarios alternativos
10. Hallazgos y conclusiones
Anexo A. Matriz de trazabilidad
Anexo B. Huellas y reproducibilidad
```

## 6. DOCX

Abre el documento y revisa:

- portada;
- índice sin numeración duplicada;
- encabezado;
- pie con número de página;
- identificación del expediente;
- tabla de fuentes;
- conclusiones de inferencia;
- argumentos y relaciones;
- comparación de escenarios;
- limitaciones;
- matriz de trazabilidad;
- huellas SHA-256;
- ausencia de texto recortado.

## 7. Prueba de validación

Selecciona el mismo escenario como base y comparado. El sistema debe mostrar:

```text
Los escenarios base y comparado deben ser distintos.
```

## 8. Prueba sin resumen manual

Deja vacío el resumen ejecutivo y genera. El sistema debe redactar un resumen
descriptivo usando únicamente la ejecución y la red registradas.

## 9. Prueba con resumen manual

Escribe:

```text
Resumen preparado por el analista para revisión humana.
```

Genera nuevamente. El texto debe conservarse en JSON, Markdown y DOCX.

## Cierre

Sprint 4.2 queda validado cuando:

```text
66 pruebas aprobadas
Ruff sin errores
Mypy sin errores
JSON correcto
Markdown correcto
DOCX legible
huellas visibles
comparación narrativa correcta
```
