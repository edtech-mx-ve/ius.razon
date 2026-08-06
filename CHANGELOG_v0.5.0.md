# Changelog — IUS-Razón v0.5.0

## Sprint 4.3 · Asistente IA controlado

### Añadido

- Contrato `LLMProvider` desacoplado.
- Proveedor determinista `ius-razon-mock-v1`.
- Modelos tipados de solicitud, contexto, evaluación, borrador y revisión.
- Selección explícita de hechos, pruebas, fuentes, conclusiones y argumentos.
- Inclusión trazable del problema jurídico.
- Anonimización reproducible de alias de partes.
- Límite configurable de contexto y salida.
- Detección heurística de instrucciones incrustadas.
- Extracción y validación de referencias internas.
- Métrica de cobertura de citas.
- Detección de afirmaciones sustantivas sin referencia.
- Flujo `Generado → Aprobado/Rechazado`.
- Persistencia local de texto original, texto revisado, huellas y decisión.
- Pestaña Streamlit `Asistente IA`.
- Historial asistivo por problema jurídico.
- Doce pruebas automatizadas nuevas.

### Seguridad

- Sin llamadas externas en v0.5.0.
- Sin claves API.
- Sin secretos en código, SQLite o logs.
- Logging limitado a identificadores, proveedor, modelo y huellas.
- Contexto tratado como datos, no como instrucciones.
- Aprobación bloqueada ante citas inválidas o afirmaciones sin respaldo.

### Persistencia

Migración aditiva:

```text
llm_draft_sequences
llm_drafts
```

No se modifica ninguna tabla previa.

### Compatibilidad

- Python: `>=3.11`.
- Streamlit: `>=1.40,<2`.
- Pydantic: `>=2.8,<3`.
- Motor determinista: `3.2.0`.
- Informe integral: `4.2.1`.
- Aplicación: `0.5.0`.
