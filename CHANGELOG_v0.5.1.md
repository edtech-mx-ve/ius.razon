# CHANGELOG — IUS-Razón v0.5.1

## Sprint 4.3.1

### Corregido

- Coincidencia parcial de alias al anonimizar.
- Pérdida de la primera letra en `afirma` y `acredita`.
- Sustituciones en fragmentos internos de palabras.
- Posible reanonimización de identificadores `PARTE-###`.
- Duplicación lógica de alias que solo difieren en mayúsculas.

### Mejorado

- Sustitución de alias en una sola pasada.
- Límites léxicos Unicode.
- Orden determinista de alias solapados.
- Preservación de espacios y puntuación.
- Idempotencia del anonimizador.
- Configuración localizada de Mypy para stubs externos de NumPy.

### Pruebas

- Se agregaron seis pruebas de regresión.
- Total esperado: 88 pruebas.

### Compatibilidad

- Sin migraciones SQLite.
- Sin cambios destructivos.
- Sin llamadas externas.
- Los borradores históricos se conservan.
