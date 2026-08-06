# Guía de prueba funcional — Sprint 4.1

## Objetivo

Validar el grafo argumental, los escenarios alternativos, la comparación y las
exportaciones sin modificar el motor de razonamiento 3.2.0.

## Preparación

1. Inicia la aplicación.
2. Abre el expediente que contiene `PJ-001`.
3. Deja activa la conclusión provisional de incumplimiento.
4. Abre la pestaña `Argumentación`.
5. Comprueba que existen al menos dos argumentos y una relación.

## Escenario sugerido

Crea un escenario con:

```text
Nombre:
Escenario sin réplica acreditada

Descripción:
Incluye el argumento favorable principal y la objeción adversa, pero excluye
la réplica para observar el efecto estructural de una objeción pendiente.

Estado:
Activo
```

Selecciona:

```text
ARG-001
ARG-002
```

Supuestos:

```text
No se incorporan comunicaciones posteriores.
La causa justificante permanece sin acreditación suficiente.
```

El código esperado es:

```text
SCN-001
```

## Validación del grafo

Selecciona `SCN-001` en `Vista argumental`.

Comprueba:

```text
Argumentos: 2
Relaciones: depende de las relaciones registradas entre ambos nodos
Objeciones pendientes: al menos 1 si ARG-002 es adverso y no recibe réplica
Componentes: 1 si existe una relación entre ambos argumentos
```

La visualización debe mostrar:

```text
argumento favorable → caja
argumento adverso   → octágono
ataque              → arista dirigida
```

## Comparación

Compara:

```text
Escenario base: SCN-001
Escenario comparado: Vista completa
```

Verifica que el resultado identifique:

```text
argumentos añadidos
relaciones añadidas
cambio en objeciones pendientes
cambio en componentes
cambio en soporte descriptivo
huellas distintas
```

## Exportación

Descarga:

```text
JSON
Markdown
DOT
```

Comprueba que los tres archivos contienen:

```text
código del escenario
nombre del escenario
argumentos
relaciones
métricas
supuestos
huella SHA-256
advertencia jurídica
```

## Edición segura

1. Abre `Editar o eliminar escenario`.
2. Cambia el nombre o añade un argumento.
3. Guarda.
4. Confirma que el código sigue siendo `SCN-001`.

## Eliminación segura

1. Intenta eliminar sin escribir el código.
2. Debe rechazarse.
3. Escribe exactamente `SCN-001`.
4. El escenario debe eliminarse.

## Protección de dependencias

1. Crea de nuevo un escenario que incluya `ARG-001`.
2. Intenta eliminar `ARG-001`.
3. La operación debe bloquearse e indicar el escenario dependiente.
4. Retira `ARG-001` del escenario o elimina el escenario antes de eliminar el
   argumento.

## Validación técnica

```powershell
ruff check .
mypy src
pytest -v
```

Resultado esperado:

```text
All checks passed!
Success: no issues found
58 passed
```

## Criterio de cierre

Sprint 4.1 queda validado cuando:

- el escenario se crea y conserva su código;
- el grafo se renderiza;
- las relaciones externas al escenario se excluyen;
- las advertencias son coherentes;
- la comparación detecta diferencias;
- las exportaciones se descargan;
- la protección de dependencias funciona;
- Ruff, Mypy y Pytest concluyen sin errores.
