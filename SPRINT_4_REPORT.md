# Reporte técnico — Sprint 4.0

## Identificación

- Producto: IUS-Razón
- Versión de aplicación: 0.4.0
- Motor de inferencia: 3.2.0
- Incremento: argumentación jurídica y contraargumentación
- Persistencia: SQLite
- Interfaz: Streamlit

## Objetivo

Transformar conclusiones trazadas del motor en argumentos jurídicos
estructurados, conectados con hechos, pruebas, fuentes, premisas y reglas,
manteniendo separación entre razonamiento lógico y valoración profesional.

## Implementación

### Dominio

Se añadieron modelos Pydantic para:

- argumentos;
- posiciones;
- estados;
- relaciones dirigidas;
- evaluación descriptiva de soporte;
- expediente argumental reproducible.

### Persistencia

La migración aditiva crea:

- `legal_arguments`;
- `argument_relations`;
- `argument_sequences`.

Los códigos se generan mediante secuencias persistentes y no se reutilizan.

### Servicios

`ArgumentationService` implementa:

- creación manual;
- creación desde una conclusión;
- actualización con respaldo;
- eliminación protegida;
- relaciones de apoyo, ataque y réplica;
- validación de soportes;
- aislamiento por problema jurídico;
- diagnóstico de objeciones;
- evaluación descriptiva de soporte;
- exportación JSON, Markdown y DOCX.

### Interfaz

La pestaña `Argumentación` permite:

- seleccionar el problema jurídico;
- crear argumentos desde conclusiones;
- crear argumentos manuales;
- relacionar argumentos;
- revisar la red argumental;
- consultar métricas y vacíos;
- descargar reportes.

## Decisiones técnicas

- La conclusión inferida se vincula por identificador interno y conserva sus
  códigos de premisas, reglas y fuentes.
- Las relaciones son dirigidas y no admiten autorrelaciones.
- Los soportes fácticos y documentales son de expediente.
- Las premisas y reglas se restringen al problema jurídico seleccionado.
- El soporte descriptivo mide completitud de trazabilidad, no probabilidad.
- La huella excluye la hora de generación y usa contenido ordenado.
- La fecha de instantánea se deriva de las últimas modificaciones, por lo que
  la exportación permanece estable mientras no cambien los datos.

## Validación

```text
50 pruebas aprobadas
Migración aditiva: aprobada
Registros previos preservados: aprobado
Creación desde conclusión: aprobada
Código inexistente: rechazado
Soporte de otro problema: rechazado
Ataque y réplica: aprobados
Relación entre problemas: bloqueada
Exportación JSON reproducible: aprobada
Exportación Markdown: aprobada
Exportación DOCX: aprobada
Actualización conserva código: aprobada
Eliminación con relaciones: bloqueada
```

## Seguridad

- validación Pydantic;
- consultas parametrizadas;
- claves foráneas activas;
- confirmación exacta;
- respaldo antes de mutaciones sensibles;
- aislamiento por expediente y problema;
- advertencias de uso en interfaz y reportes.

## Limitaciones

- no existe clasificación automática del mérito jurídico;
- el soporte es descriptivo;
- no se verifica el contenido de documentos;
- no hay grafo visual interactivo;
- no se genera una estrategia procesal automática;
- no se reemplaza revisión profesional.

## Criterios de aceptación

- [x] crear argumento desde conclusión;
- [x] crear argumento manual;
- [x] asociar hechos, pruebas, fuentes, premisas y reglas;
- [x] registrar apoyo, ataque y réplica;
- [x] identificar objeciones sin respuesta;
- [x] detectar referencias inexistentes;
- [x] impedir cruces entre problemas;
- [x] exportar JSON, Markdown y DOCX;
- [x] preservar datos existentes;
- [x] aprobar pruebas automatizadas.

## Próximo sprint

Sprint 4.1: grafo argumental, escenarios alternativos y navegación visual.
