# IUS-Razón — Reporte técnico Sprint 3.2

## Versión

```text
Aplicación: 0.3.4
Motor de razonamiento: 3.2.0
```

## Objetivo

Incorporar resolución reproducible de reglas rivales y retirada de conclusiones
dependientes, sin alterar los expedientes ni las reglas existentes.

## Alcance implementado

### 1. Reglas rivales

Dos reglas son rivales cuando:

- están activas;
- sus prerrequisitos están satisfechos;
- tienen la misma clave de conclusión;
- producen valores opuestos.

Las reglas con claves distintas no compiten aunque estén relacionadas
conceptualmente.

### 2. Política de derrota

La comparación usa este orden:

```text
prioridad numérica > tipo de regla > especificidad estructural
```

- prioridad: gana el valor numérico mayor;
- tipo: con igual prioridad, estricta gana sobre provisional;
- especificidad: con igual prioridad y tipo, gana la regla con más
  prerrequisitos distintos;
- empate exacto: ambas conclusiones se suspenden.

La política es determinista y aparece en el resumen y la traza.

### 3. Retirada dependiente

El motor reconstruye las conclusiones desde las premisas base en cada iteración.
Cuando una regla queda derrotada, se elimina su conclusión. Si otra regla
dependía exclusivamente de esa conclusión, también se retira.

La traza identifica:

```text
Retirada por dependencia derrotada
```

y enumera las dependencias que dejaron de estar disponibles.

### 4. Conflictos no resueltos

Cuando las reglas rivales empatan en prioridad, tipo y especificidad:

- no se acepta ninguna conclusión rival;
- el conflicto se registra;
- se incrementa `unresolved_conflict_count`;
- la interfaz muestra una advertencia;
- se requiere revisión humana.

### 5. Ciclos

El motor limita las iteraciones. Cuando detecta una oscilación:

- conserva únicamente reglas estables;
- suspende las reglas inestables;
- registra `Ciclo no convergente`;
- evita presentar una conclusión inestable como vigente.

### 6. Interfaz

Se añadieron:

- explicación visible de la política de derrota;
- columna de especificidad en reglas;
- especificidad actual en gestión de reglas;
- métricas de derrotas, empates, retiradas y conflictos;
- advertencia de conflicto no resuelto;
- compatibilidad con el parámetro `width` de Streamlit.

### 7. Exportación

El reporte Markdown incluye una sección de resolución de conflictos.

La comparación de ejecuciones añade:

```text
changed_rule_outcomes
```

para mostrar cambios como:

```text
R-001: Regla provisional aplicada → Derrotada por menor prioridad
```

## Arquitectura

La lógica se concentra en funciones y componentes con responsabilidades claras:

```text
ReasoningEngine
├── evaluación de prerrequisitos
├── evaluación de excepciones
├── construcción de candidatos
├── resolución de conflictos
├── reconstrucción de conclusiones
├── detección de retirada
├── detección de no convergencia
└── construcción de trazas y resumen
```

Las transformaciones de ranking, firmas y soporte se mantienen sin estado
global mutable.

## Decisiones

### Prioridad antes que tipo

Una prioridad explícita mayor prevalece incluso cuando la regla ganadora es
provisional. Esto permite que el usuario modele jerarquía jurídica de forma
controlada. El tipo solo resuelve empates de prioridad.

### Especificidad estructural

La especificidad cuenta prerrequisitos distintos. Es una aproximación
transparente y reproducible. No representa calidad de prueba ni jerarquía
normativa.

### Empate conservador

El motor no elige por código, fecha ni orden de registro. Un empate exacto
suspende las conclusiones opuestas.

### Recalcular, no parchear

Las conclusiones no se modifican incrementalmente sobre un estado persistente.
Cada ejecución y cada iteración reconstruyen el estado derivado para permitir
retirada segura.

## Pruebas

Resultado:

```text
42 pruebas aprobadas
```

Cobertura funcional agregada:

- prioridad;
- regla estricta frente a provisional;
- especificidad;
- empate exacto;
- retirada en una cadena;
- premisa confirmada contraria;
- determinismo;
- política reportada.

También se ejecutó:

- análisis sintáctico de todos los archivos Python;
- comprobación de líneas de máximo 100 caracteres;
- prueba de compatibilidad con los 34 casos anteriores.

Ruff y Mypy no estaban instalados en el entorno de construcción. Deben
confirmarse localmente.

## Compatibilidad

No se añade ni modifica ninguna tabla. No se incluyen bases de datos de usuario
en los paquetes.

Se preservan:

- expedientes;
- partes;
- hechos;
- pruebas;
- fuentes;
- premisas;
- reglas;
- versiones;
- ejecuciones anteriores;
- conclusiones y trazas históricas.

## Criterios de aceptación

- una regla con prioridad mayor derrota a su rival;
- una regla estricta derrota a una provisional con igual prioridad;
- una regla más específica derrota a su rival con igual prioridad y tipo;
- un empate exacto no produce conclusión rival;
- una conclusión dependiente desaparece cuando pierde su soporte;
- la traza identifica regla ganadora, derrotada y criterio;
- la ejecución conserva huella, instantánea y versión de motor;
- las pruebas anteriores continúan aprobadas.

## Limitaciones

- la prioridad debe configurarse manualmente;
- no se deduce jerarquía normativa;
- no existe relación manual de superioridad entre reglas;
- la especificidad no mide calidad jurídica;
- los ciclos se suspenden, no se resuelven con semánticas argumentativas
  avanzadas;
- el motor no verifica fuentes ni sustituye revisión profesional.

## Implementación

Desde la raíz del proyecto en Windows PowerShell:

```powershell
# Detén Streamlit presionando físicamente Ctrl + C.

Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint32.bak" -Force
}

Expand-Archive `
    .\IUS_Razon_Sprint_3_2_patch_v0.3.4.zip `
    -DestinationPath . `
    -Force

python -m pip install -e ".[dev]"

ruff check .
mypy src
pytest -v

streamlit run app.py
```

URL:

```text
http://localhost:8501
```

Resultado esperado:

```text
All checks passed!
Success: no issues found in 17 source files
42 passed
```
