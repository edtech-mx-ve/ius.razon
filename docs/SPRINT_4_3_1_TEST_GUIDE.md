# Guía de prueba funcional — Sprint 4.3.1 v0.5.1

## Preparación

```powershell
python -m pip install -e . --no-deps --no-cache-dir --force-reinstall
ruff check .
python -m mypy --config-file .\pyproject.toml src
pytest -v
streamlit run app.py
```

## Caso de regresión

1. Abre `Asistente IA`.
2. Selecciona el expediente `Incumplimiento de entrega de equipo`.
3. Selecciona `PJ-001`.
4. Selecciona la ejecución `3385ccd1` o la ejecución vigente con una
   conclusión.
5. Conserva las categorías disponibles.
6. Elige `Resumen del expediente`.
7. Mantén `Anonimizar partes` activado.
8. Escribe:

```text
Prioriza la relación entre el pago, el vencimiento del plazo y la conclusión
provisional de incumplimiento.
```

9. Pulsa `Generar borrador controlado`.

## Resultado esperado

Debe crearse un nuevo registro `IA-###` con:

```text
Estado: Generado
Cobertura: 100 %
Referencias inválidas: 0
Afirmaciones sin respaldo: 0
```

No debe contener:

```text
PARTE-001firma
PARTE-001credita
```

La salida correcta depende del texto almacenado:

```text
La parte compradora afirma...
La parte compradora acredita...
```

cuando se trata de una descripción de rol, o:

```text
PARTE-001 afirma...
PARTE-001 acredita...
```

cuando aparece exactamente el alias registrado.

## Revisión humana

1. Comprueba que no haya palabras pegadas.
2. No elimines referencias como `[PJ-001]`, `[H-001]` o `[N-001]`.
3. Registra una nota:

```text
Validación Sprint 4.3.1: anonimización sin coincidencias parciales ni pérdida
de espacios.
```

4. Pulsa `Aprobar versión revisada`.
5. Abre `Historial asistivo`.

Resultado:

```text
Estado: Aprobado
Cobertura: 100 %
Texto original: conservado
Texto revisado: guardado
```

## Regresión general

Confirma que continúan funcionando:

- inferencia;
- argumentos y relaciones;
- escenarios;
- informe jurídico integral;
- exportación JSON, Markdown y DOCX;
- historial asistivo existente.
