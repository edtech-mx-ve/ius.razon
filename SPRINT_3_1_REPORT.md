# IUS-Razón — Reporte técnico Sprint 3.1

## Versión

- Aplicación: `0.3.2`
- Motor lógico: `3.0.0`
- Persistencia: SQLite
- Interfaz: Streamlit
- Compatibilidad: actualización aditiva desde `0.3.1`

## Objetivo

Robustecer el mantenimiento del conocimiento jurídico registrado sin alterar la
semántica del motor. El incremento permite corregir premisas y reglas, conservar
trazabilidad histórica, proteger eliminaciones y reproducir ejecuciones posteriores
a una modificación.

## Implementación

### Dominio

Se incorporaron modelos de actualización y versionado:

- `ReasoningAssertionUpdate`;
- `ReasoningRuleUpdate`;
- `ReasoningVersionRecord`;
- `VersionAction`.

Los modelos preservan validación de claves lógicas, longitudes, valores y
condiciones.

### Persistencia

Se añadieron las tablas:

```text
reasoning_assertion_versions
reasoning_rule_versions
```

También se añadió de forma aditiva:

```text
reasoning_runs.input_snapshot_json
```

Cada actualización almacena el estado anterior completo. Cada eliminación
almacena el último estado antes de borrar el registro principal.

### Integridad

- cambio de clave de premisa bloqueado cuando la clave es usada por reglas;
- eliminación de premisa bloqueada cuando existe una condición dependiente;
- cambio o eliminación de conclusión de regla bloqueado cuando otras reglas la
  utilizan;
- código visible preservado durante las ediciones;
- código eliminado no reutilizado;
- confirmación exacta obligatoria para eliminar;
- respaldo SQLite consistente antes de toda edición o eliminación.

### Servicio

`ReasoningService` centraliza:

- validación de códigos;
- respaldo previo;
- edición y eliminación;
- consulta del historial;
- generación de instantáneas;
- huella SHA-256;
- comparación de ejecuciones;
- exportación JSON y Markdown.

### Interfaz

La pestaña `Gestión razonamiento` ofrece:

- corrección de premisas;
- corrección y activación de reglas;
- eliminación segura;
- versiones por entidad;
- historial global de cambios.

La pestaña `Inferencia` ofrece:

- entrada exacta de cada ejecución nueva;
- descarga JSON;
- descarga Markdown;
- comparación entre dos ejecuciones.

## Decisiones

1. Se mantuvo el motor `3.0.0` porque este sprint no cambia su algoritmo.
2. Se guardan instantáneas completas, no diferencias parciales, para facilitar
   auditoría y restauración manual.
3. Las migraciones son aditivas.
4. No se modifica una dependencia de forma implícita; la operación se bloquea
   para exigir una corrección consciente.
5. Los respaldos se realizan en el servicio, antes de la mutación.

## Verificación

```text
34 pruebas aprobadas
Compilación de archivos Python correcta
Migración desde tabla reasoning_runs de v0.3.1 verificada
Edición y versionado verificados
Bloqueo por dependencias verificado
Instantánea, exportación y comparación verificadas
```

Ruff y Mypy no estaban instalados en el entorno de construcción. Deben
confirmarse en el entorno local.

## Criterios de aceptación

- [x] una premisa puede corregirse sin cambiar su código;
- [x] una regla puede corregirse o desactivarse sin cambiar su código;
- [x] cada edición crea historial;
- [x] una eliminación exige el código exacto;
- [x] una dependencia lógica impide una eliminación insegura;
- [x] una nueva ejecución conserva sus entradas completas;
- [x] dos ejecuciones pueden compararse;
- [x] una ejecución puede exportarse;
- [x] datos v0.3.1 permanecen compatibles.

## Limitaciones

- no hay restauración automática de una versión;
- no hay derrota completa por prioridad o especificidad;
- no hay firma criptográfica externa del reporte;
- las fuentes jurídicas siguen requiriendo verificación humana.

## Backlog

Sprint 3.2:

- derrota controlada entre reglas rivales;
- precedencia por tipo, prioridad y especificidad;
- retirada de conclusiones dependientes;
- explicación de la regla derrotada;
- casos de prueba de conflicto jurídico.
