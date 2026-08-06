# IUS-Razón — Reporte técnico Sprint 4.1

## Versión

- Aplicación: `0.4.1`
- Motor de razonamiento: `3.2.0`
- Incremento: grafo argumental y escenarios alternativos

## Objetivo

Permitir que una persona analista represente la estructura argumental como un
grafo dirigido, construya escenarios con subconjuntos de argumentos, compare
diferencias y exporte instantáneas reproducibles sin convertir las métricas en
predicciones jurídicas.

## Implementación

### Dominio

Se incorporaron:

- `ScenarioStatus`;
- `ArgumentScenarioCreate`;
- `ArgumentScenarioUpdate`;
- `ArgumentScenarioRecord`;
- `ArgumentGraphNode`;
- `ArgumentGraphEdge`;
- `ArgumentGraphSnapshot`;
- `ScenarioComparison`.

### Persistencia

La tabla `argument_scenarios` conserva:

- expediente y problema jurídico;
- código persistente `SCN-###`;
- nombre y descripción;
- estado;
- identificadores de argumentos;
- supuestos;
- fechas de creación y actualización.

La migración es aditiva. Los códigos se generan mediante `argument_sequences`,
por lo que no se reutilizan después de eliminar un escenario.

### Servicio

El servicio:

- valida que todos los argumentos pertenezcan al problema activo;
- crea respaldos antes de mutaciones;
- construye grafos completos o restringidos;
- incorpora una relación solo cuando ambos extremos pertenecen al escenario;
- calcula componentes como grafo no dirigido;
- detecta objeciones adversas sin réplica;
- detecta argumentos aislados;
- calcula soporte descriptivo promedio;
- genera DOT sin HTML ni recursos externos;
- genera huellas SHA-256 deterministas;
- compara escenarios;
- exporta JSON, Markdown y DOT.

### Interfaz

La pestaña `Argumentación` incorpora:

- creación de escenarios;
- tabla de escenarios;
- edición y eliminación segura;
- selector de vista;
- visualización Graphviz;
- métricas estructurales;
- advertencias;
- exportación;
- comparación entre escenarios.

## Política de seguridad

- no se ejecuta código externo;
- el texto se escapa antes de formar DOT;
- no se cargan imágenes ni URLs externas;
- los escenarios no aceptan argumentos de otro problema;
- un argumento incluido en un escenario no puede eliminarse hasta retirarlo;
- las mutaciones crean respaldo SQLite;
- la eliminación exige el código exacto.

## Métricas

Las métricas son estructurales:

- número de nodos;
- número de relaciones;
- apoyos;
- ataques;
- réplicas;
- objeciones pendientes;
- argumentos aislados;
- componentes;
- soporte descriptivo total y promedio.

No son una probabilidad, una recomendación procesal ni una predicción judicial.

## Verificación ejecutada

- 58 pruebas automatizadas aprobadas;
- compilación sintáctica correcta;
- líneas Python no superiores a 100 caracteres;
- migración desde una base real de Sprint 4.0 verificada;
- argumentos y relaciones anteriores preservados;
- creación posterior de `SCN-001` verificada;
- subgrafos verificados;
- comparación verificada;
- exportación determinista verificada;
- escape DOT verificado;
- bloqueo de dependencias verificado.

Ruff y Mypy no estaban instalados en el entorno de construcción. Deben
ejecutarse en el entorno local del usuario.

## Criterios de aceptación

- [x] crear escenario;
- [x] conservar código en edición;
- [x] eliminar con confirmación;
- [x] restringir argumentos por problema;
- [x] visualizar grafo;
- [x] filtrar relaciones internamente;
- [x] detectar objeciones y componentes;
- [x] comparar escenarios;
- [x] exportar JSON, Markdown y DOT;
- [x] preservar datos de Sprint 4.0;
- [x] aprobar pruebas automatizadas.

## Limitaciones

- no se calcula fuerza jurídica sustantiva;
- no se infiere causalidad;
- no se resuelve automáticamente un ataque argumental;
- no se genera imagen PNG o SVG en servidor;
- no existe colaboración concurrente;
- los escenarios son instantáneas configuradas por el usuario.
