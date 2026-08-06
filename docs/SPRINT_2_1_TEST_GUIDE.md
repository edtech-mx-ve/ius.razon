# Guía de prueba funcional — Sprint 2.1

## Preparación

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
pytest -v
ruff check .
mypy src
streamlit run app.py
```

Abre `http://localhost:8501` y selecciona el expediente usado en Sprint 2.

## Caso 1: corregir una norma

1. Abre **Corrección segura**.
2. Selecciona `Norma`.
3. Selecciona `N-001`.
4. Corrige `Notas de aplicabilidad`.
5. No cargues otro PDF si deseas conservar el actual.
6. Pulsa **Guardar corrección**.

Resultado esperado:

- aparece confirmación;
- el código sigue siendo `N-001`;
- la matriz conserva sus vínculos;
- en Resumen aparece `norm.updated`;
- se crea un respaldo en `backups/`.

## Caso 2: corregir un vínculo

1. Selecciona `Vínculo problema–fuente`.
2. Selecciona `PJ-001 ↔ N-001`.
3. Corrige orientación, aplicabilidad o notas.
4. Guarda.

Resultado esperado:

- el contador de vínculos no aumenta;
- la fila existente cambia;
- aparece `issue_source.updated`.

## Caso 3: comprobar protección

1. Selecciona `Norma`.
2. Selecciona una norma todavía vinculada.
3. Abre **Eliminar norma**.
4. Escribe exactamente su código.
5. Intenta eliminar.

Resultado esperado:

```text
No se puede eliminar la fuente porque conserva problemas jurídicos vinculados.
```

## Caso 4: desvincular y eliminar

1. Selecciona `Vínculo problema–fuente`.
2. Selecciona el vínculo.
3. Abre **Eliminar vínculo**.
4. Confirma con el código de la fuente.
5. Vuelve a `Norma`.
6. Selecciona la fuente ya desvinculada.
7. Confirma su eliminación.

Resultado esperado:

- el vínculo desaparece;
- la fuente desaparece;
- el archivo, si existía, se mueve a `archived_uploads/`;
- se registran `issue_source.unlinked` y `legal_source.deleted`.

## Caso 5: persistencia

Detén y reinicia:

```powershell
Ctrl+C
streamlit run app.py
```

Resultado esperado:

- las correcciones permanecen;
- los registros eliminados no reaparecen;
- los registros no modificados de Sprint 1 y Sprint 2 permanecen;
- al crear una nueva entidad no se reutiliza un código eliminado.
