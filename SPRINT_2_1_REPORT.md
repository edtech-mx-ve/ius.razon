# Reporte técnico — Sprint 2.1

## Objetivo

Permitir corregir errores de captura y eliminar registros jurídicos de forma controlada,
sin perder trazabilidad ni comprometer la persistencia validada en Sprint 2.

## Incremento funcional

### Edición

Se implementaron operaciones de actualización para:

- `LegalIssue`
- `Norm`
- `Jurisprudence`
- `Doctrine`
- `IssueSourceLink`

Las actualizaciones conservan el identificador interno, el código visible y la fecha de
creación. La auditoría registra el tipo de evento y el identificador de la entidad.

### Eliminación protegida

La eliminación requiere confirmación exacta del código. El repositorio rechaza:

- eliminar una fuente que conserve vínculos;
- eliminar un problema jurídico que conserve vínculos;
- eliminar entidades pertenecientes a otro expediente;
- desvincular una relación inexistente.

### Respaldo previo

`CaseService` crea un respaldo SQLite antes de:

- actualizar una entidad;
- eliminar una entidad;
- crear o actualizar un vínculo;
- desvincular una fuente.

Si el respaldo no puede crearse, la operación sensible se cancela.

### Archivos

Cuando se reemplaza el documento de una fuente:

- el nuevo archivo se valida y almacena;
- la base se actualiza;
- el documento anterior se mueve a `archived_uploads/`.

Al eliminar una fuente, su archivo también se archiva. Esto mantiene coherencia con los
respaldos históricos de la base.

### Códigos

La tabla `code_sequences` conserva el último número utilizado por expediente y tipo de
entidad. Un código eliminado no se reutiliza. Ejemplo:

```text
N-001, N-002
eliminar N-002
nueva norma → N-003
```

## Seguridad

- validación Pydantic antes de actualizar;
- transacciones SQLite;
- claves foráneas activas;
- confirmación explícita;
- respaldo previo;
- restricción por expediente;
- validación de rutas;
- logs sin contenido jurídico sensible;
- archivos anteriores archivados, no destruidos.

## Pruebas

Resultado:

```text
20 passed
```

Cobertura funcional añadida:

- edición de problema y norma;
- conservación de códigos;
- creación de respaldos;
- bloqueo de fuente vinculada;
- bloqueo de problema vinculado;
- corrección de vínculo sin duplicación;
- desvinculación y eliminación posterior;
- rechazo por confirmación incorrecta;
- reemplazo y archivo de documentos;
- auditoría de actualización y eliminación;
- edición y eliminación de jurisprudencia y doctrina;
- no reutilización de códigos.

## Migración

Se creó una base con v0.2.0 que contenía:

- un expediente;
- un problema jurídico;
- una norma;
- un vínculo problema–fuente.

Después de inicializar v0.2.1, los registros permanecieron disponibles con conteos `1, 1, 1`.
