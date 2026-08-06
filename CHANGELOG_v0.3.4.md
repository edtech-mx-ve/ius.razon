# Changelog — IUS-Razón v0.3.4

## Sprint 3.2

### Motor 3.2.0

- añade resolución controlada de reglas rivales;
- compara reglas por prioridad numérica;
- en igualdad de prioridad, prefiere reglas estrictas;
- en nuevo empate, usa especificidad estructural;
- calcula especificidad como número de prerrequisitos distintos;
- suspende conclusiones opuestas ante empate exacto;
- registra reglas derrotadas y el criterio de derrota;
- reconstruye las conclusiones en cada iteración;
- retira conclusiones dependientes cuando desaparece su soporte;
- detecta oscilaciones y suspende reglas no convergentes;
- conserva la propagación del carácter provisional;
- mantiene el bloqueo de reglas provisionales por excepciones;
- mantiene el bloqueo por una premisa confirmada contraria.

### Trazabilidad

Se agregan los resultados:

```text
Derrotada por menor prioridad
Derrotada por regla estricta rival
Derrotada por menor especificidad
Empate entre reglas rivales
Retirada por dependencia derrotada
Ciclo no convergente
```

El resumen de cada ejecución incorpora:

```text
conflict_count
unresolved_conflict_count
defeated_rule_count
tied_rule_count
withdrawn_rule_count
non_convergent_rule_count
defeat_policy
```

### Interfaz

- muestra la especificidad de cada regla;
- explica la política de derrota;
- muestra métricas de derrotas, empates, retiradas y conflictos;
- advierte sobre conflictos no resueltos;
- reemplaza `use_container_width` por `width="stretch"` para Streamlit actual.

### Exportación y comparación

- el Markdown incluye una sección de resolución de conflictos;
- la comparación de ejecuciones incluye cambios en resultados de reglas.

### Compatibilidad

- no añade tablas;
- no transforma datos existentes;
- conserva expedientes, premisas, reglas, versiones y ejecuciones;
- las ejecuciones antiguas mantienen su versión de motor;
- las nuevas ejecuciones usan `3.2.0`.

### Pruebas

Se agregan pruebas para:

- derrota por prioridad;
- derrota por tipo de regla;
- derrota por especificidad;
- retirada dependiente;
- bloqueo por premisa contraria;
- determinismo y política del motor.

Resultado de construcción:

```text
42 pruebas aprobadas
```
