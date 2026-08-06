# Reporte técnico — Sprint 4.3 v0.5.0

## Objetivo

Incorporar un asistente de redacción controlado que utilice únicamente
contexto seleccionado del expediente, conserve referencias internas y exija
revisión humana antes de aprobar cualquier texto.

## Supuestos

- La primera integración debe operar sin servicios externos ni costo.
- La base activa ya contiene las migraciones de expedientes, razonamiento y
  argumentación.
- La revisión humana es obligatoria.
- Un borrador asistivo no es una conclusión del motor ni una fuente jurídica.
- Las referencias internas verifican trazabilidad estructural, no verdad.

## Implementación

### Dominio

`llm_models.py` define tareas, categorías, estados, solicitudes, vistas
previas, respuestas, evaluaciones y registros persistidos.

### Proveedor

`LLMProvider` separa la orquestación del proveedor. La versión 0.5.0 incluye
`DeterministicMockProvider`, reproducible y sin red.

### Transformaciones puras

`llm_guardrails.py` implementa:

- saneamiento de caracteres;
- detección heurística de instrucciones incrustadas;
- anonimización de alias;
- truncamiento determinista;
- serialización delimitada;
- huellas SHA-256;
- extracción de referencias;
- evaluación de cobertura y respaldo.

### Servicio

`LLMAssistantService`:

1. valida expediente y problema;
2. construye el catálogo de contexto;
3. filtra categorías y códigos;
4. detecta riesgos;
5. anonimiza;
6. limita el contexto;
7. calcula la huella de entrada;
8. invoca al proveedor;
9. evalúa citas y afirmaciones;
10. persiste el borrador;
11. exige revisión humana;
12. registra aprobación o rechazo.

### Persistencia

`LLMRepository` crea tablas aditivas y usa transacciones, claves foráneas,
WAL, códigos `IA-###` y control de conflicto durante la revisión.

### Interfaz

La pestaña `Asistente IA` ofrece selección granular, controles de privacidad,
métricas de trazabilidad, edición, aprobación, rechazo e historial.

## Pruebas

Se añadieron 12 pruebas para:

- validación de solicitudes;
- detección de inyección;
- anonimización;
- límite determinista;
- reproducibilidad del proveedor;
- referencias inválidas;
- catálogo completo;
- huella y anonimización de vista previa;
- persistencia;
- bloqueo de aprobación sin citas;
- aprobación y conflicto;
- rechazo y preservación del original.

Resultado en el entorno de construcción:

```text
82 pruebas recopiladas
82 pruebas aprobadas
compilación sintáctica aprobada
líneas Python mayores de 100 caracteres: 0
```

Ruff y Mypy no estaban instalados en el entorno de construcción. Deben
confirmarse en el entorno local del proyecto.

## Criterios de aceptación

| Criterio | Estado |
|---|---|
| No modificar datos jurídicos | Cumplido |
| Selección explícita de contexto | Cumplido |
| Referencias internas verificadas | Cumplido |
| Detección de afirmaciones sin respaldo | Cumplido |
| Revisión humana obligatoria | Cumplido |
| Anonimización disponible | Cumplido |
| Sin secretos o llamadas externas | Cumplido |
| Persistencia reproducible | Cumplido |
| Modo simulado | Cumplido |
| Pruebas de regresión | Cumplido en construcción |

## Seguridad

- Los textos no se escriben en logs.
- No se aceptan ni guardan claves.
- La entrada se sanea antes de procesarse.
- El contexto tiene límites estrictos.
- Los códigos citados deben pertenecer a la selección.
- La aprobación exige cobertura completa según la heurística.
- Se crea respaldo antes de registrar una decisión humana.

## Limitaciones

- La salida simulada usa plantillas deterministas.
- La detección de inyección no es una garantía absoluta.
- Una cita válida puede respaldar inadecuadamente una afirmación; la revisión
  sustantiva continúa siendo humana.
- No se integran borradores aprobados automáticamente en argumentos o informes.
- No existe proveedor real en esta versión.

## Backlog

1. Sprint 4.3.1: proveedor remoto opcional y seguro.
2. Presupuesto de tokens, tiempo y costo.
3. Reintentos limitados y cancelación.
4. Pruebas contractuales de proveedores.
5. Evaluación semántica de fidelidad.
6. Promoción manual de borrador aprobado a argumento o sección de informe.
7. Exportación de historial asistivo.
