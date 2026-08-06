# IUS-Razón — Sprint 4.2.1 (v0.4.4)

Prototipo local para estructurar expedientes jurídicos, ejecutar razonamiento
simbólico, construir redes argumentales y generar un informe jurídico integral
trazable sobre controversias contractuales civiles y mercantiles.

El motor de inferencia permanece en la versión 3.2.0. Sprint 4.2.1 pule la
capa de reporte integral: distingue argumentos manuales, mejora concordancia,
normaliza puntuación y conserva la reproducibilidad sin cambiar el motor.

> Uso experimental y académico. No constituye asesoría jurídica, dictamen,
> predicción judicial ni verificación automática de vigencia, autenticidad,
> obligatoriedad o aplicabilidad de fuentes.

## Funciones principales

- expedientes, partes, hechos, pruebas y vínculos probatorios;
- problemas jurídicos, normas, jurisprudencia, doctrina y matriz de fuentes;
- premisas, reglas, excepciones, prioridad, derrota, empate y trazas;
- argumentos favorables, adversos y neutrales;
- relaciones `Apoya`, `Ataca` y `Responde`;
- grafos argumentales y escenarios `SCN-###`;
- comparación estructural entre escenarios;
- informe jurídico integral con:
  - identificación y alcance;
  - resumen ejecutivo automático o redactado por el analista;
  - antecedentes, hechos y pruebas;
  - fuentes jurídicas vinculadas;
  - inferencia y traza de reglas;
  - argumentación y relaciones;
  - comparación narrativa de escenarios;
  - hallazgos, limitaciones y recomendaciones;
  - matriz de trazabilidad;
  - huellas SHA-256 para reproducibilidad;
- exportación integral a JSON, Markdown y DOCX;
- encabezado, pie de página, índice estático y numeración de páginas en DOCX;
- origen explícito de argumentos manuales y derivados del motor;
- concordancia singular/plural y puntuación normalizada en hallazgos;
- validación para impedir mezclar ejecuciones o escenarios de otros problemas.

## Informe jurídico integral

La pestaña `Informe integral` permite seleccionar:

```text
problema jurídico
ejecución de inferencia
escenario base
escenario comparado
título
objeto y alcance
resumen ejecutivo opcional
conclusiones del analista
recomendaciones
limitaciones adicionales
```

El reporte no inventa hechos ni consulta fuentes externas. Solo organiza los
datos persistidos en la base SQLite activa.

## Reproducibilidad

Cada informe incluye:

```text
huella del informe
huella de la ejecución de inferencia
huella del grafo base
huella del grafo comparado
fecha de la instantánea
versión del reporte
```

El hash se calcula a partir del contenido de entrada y no de la hora de descarga.

## Compatibilidad

Sprint 4.2.1 no modifica el esquema SQLite. Conserva:

```text
expedientes
partes
hechos
pruebas
fuentes
premisas
reglas
ejecuciones
conclusiones
argumentos
relaciones
escenarios
```

## Estructura relevante

```text
app.py
src/ius_razon/
├── domain/
│   ├── argumentation_models.py
│   └── report_models.py
└── services/
    ├── argumentation_service.py
    └── legal_report_service.py
tests/
├── test_sprint_4.py
├── test_sprint_41.py
└── test_sprint_42.py
```

## Implementación

Detén Streamlit presionando físicamente `Ctrl + C`.

Respalda la base:

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint421.bak" -Force
}
```

Aplica el parche:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_2_1_patch_v0.4.4.zip `
    -DestinationPath . `
    -Force
```

Reinstala:

```powershell
python -m pip install -e ".[dev]"
```

Comprueba versión:

```powershell
python -c "from importlib.metadata import version; import ius_razon; print(version('ius-razon')); print(ius_razon.__version__); print(ius_razon.__file__)"
```

Valida:

```powershell
ruff check .
mypy src
pytest -v
```

Resultado esperado:

```text
All checks passed!
Success: no issues found
66 passed
```

Inicia:

```powershell
streamlit run app.py
```

Abre:

```text
http://localhost:8501
```

## Prueba funcional mínima

1. Deja activa la regla principal y selecciona una ejecución válida.
2. Abre `Informe integral`.
3. Selecciona `SCN-001` como escenario base.
4. Selecciona `SCN-002` como escenario comparado.
5. Genera el informe.
6. Verifica que la comparación mencione `ARG-003`, `REL-002` y la reducción
   de objeciones pendientes.
7. Descarga JSON, Markdown y DOCX.
8. Abre el DOCX y revisa índice, tablas, numeración, trazabilidad y huellas.

## Limitaciones

- El reporte no verifica la verdad ni suficiencia jurídica de sus entradas.
- La comparación de escenarios es estructural, no predictiva.
- Las conclusiones del analista son texto registrado por el usuario.
- No hay firma electrónica, colaboración multiusuario ni publicación web.
- La revisión humana continúa siendo obligatoria.
