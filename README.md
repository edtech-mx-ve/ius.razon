# IUS-Razón — Sprint 4.3 (v0.5.0)

Prototipo local para estructurar expedientes jurídicos, ejecutar razonamiento
simbólico, construir redes argumentales, generar informes trazables y preparar
borradores asistivos bajo control humano.

El motor determinista permanece en la versión 3.2.0. Sprint 4.3 incorpora un
asistente desacoplado con proveedor simulado local, selección explícita de
contexto, anonimización, referencias internas, evaluación de respaldo y flujo
de aprobación o rechazo.

> Uso experimental y académico. No constituye asesoría jurídica, dictamen,
> predicción judicial ni verificación automática de vigencia, autenticidad,
> obligatoriedad o aplicabilidad de fuentes.

## Incremento Sprint 4.3

La pestaña `Asistente IA` permite:

- seleccionar el problema jurídico y una ejecución de inferencia;
- elegir categorías y elementos exactos del expediente;
- anonimizar alias de partes antes de construir el contexto;
- limitar el tamaño de contexto y de salida;
- generar cinco clases de borrador:
  - resumen del expediente;
  - argumento;
  - explicación de conclusión;
  - información faltante;
  - sección de informe;
- conservar referencias como `[H-001]`, `[P-001]`, `[N-001]`, `[C-001]`
  y `[ARG-001]`;
- detectar referencias no permitidas y afirmaciones sin cita;
- detectar señales heurísticas de instrucciones incrustadas;
- editar el texto antes de aprobarlo;
- aprobar o rechazar sin sobrescribir el texto original;
- guardar huellas SHA-256, proveedor, modelo, contexto y decisión humana.

## Seguridad y privacidad

La versión 0.5.0 funciona exclusivamente con:

```text
Proveedor: Simulado local
Modelo: ius-razon-mock-v1
Llamadas externas: ninguna
Clave API: no requerida ni aceptada
```

El sistema no envía datos por red. Los logs registran identificadores,
proveedor, modelo y huellas, pero no registran el texto del expediente ni el
borrador. La anonimización es opcional y está activada por defecto.

Las instrucciones encontradas dentro de hechos, pruebas o fuentes se tratan
como datos. La detección es heurística y no reemplaza la revisión humana.

## Arquitectura

```text
app.py
src/ius_razon/
├── domain/
│   └── llm_models.py
├── persistence/
│   └── llm_repository.py
├── security/
│   └── llm_guardrails.py
├── services/
│   ├── llm_assistant_service.py
│   └── llm_provider.py
└── ui/
    └── llm_assistant_view.py
tests/
└── test_sprint_43.py
```

Responsabilidades:

- `llm_models.py`: contratos tipados y estados.
- `llm_guardrails.py`: transformaciones puras de saneamiento, anonimización,
  límites, huellas y evaluación de citas.
- `llm_provider.py`: protocolo intercambiable y proveedor simulado.
- `llm_repository.py`: persistencia aditiva de borradores y revisiones.
- `llm_assistant_service.py`: orquestación, validación y logging seguro.
- `llm_assistant_view.py`: flujo Streamlit de generación y revisión.

## Persistencia

La inicialización crea, si no existen:

```text
llm_draft_sequences
llm_drafts
```

La migración es aditiva. No elimina ni modifica expedientes, hechos, pruebas,
fuentes, reglas, inferencias, argumentos, escenarios o informes.

Cada registro `IA-###` conserva:

```text
solicitud
contexto seleccionado
texto original
texto aprobado, cuando exista
referencias
afirmaciones sin respaldo
señales de riesgo
cobertura de citas
huellas de entrada y salida
estado de revisión
fecha de creación y revisión
```

## Implementación

Detén Streamlit presionando físicamente `Ctrl + C`.

Respalda la base activa:

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item `
        $_.FullName `
        "$($_.FullName).pre-sprint43.bak" `
        -Force
}
```

Aplica el parche:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_3_patch_v0.5.0.zip `
    -DestinationPath . `
    -Force
```

Reinstala únicamente el proyecto editable:

```powershell
python -m pip install `
    -e . `
    --no-deps `
    --no-cache-dir `
    --force-reinstall
```

Comprueba la versión:

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Resultado esperado:

```text
Instalada: 0.5.0
Módulo: 0.5.0
Ruta: ...\src\ius_razon\__init__.py
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
82 passed
```

Inicia la interfaz:

```powershell
streamlit run app.py
```

URL esperada:

```text
http://localhost:8501
```

## Prueba funcional mínima

1. Abre `Asistente IA`.
2. Selecciona `PJ-001`.
3. Selecciona la ejecución `3385ccd1`.
4. Conserva todas las categorías disponibles.
5. Conserva todos los elementos seleccionados.
6. Elige `Resumen del expediente`.
7. Mantén activada `Anonimizar partes`.
8. Pulsa `Generar borrador controlado`.
9. Verifica:
   - código `IA-###`;
   - estado `Generado`;
   - cobertura de citas `100 %`;
   - ausencia de referencias no permitidas;
   - alias reemplazados por `PARTE-###`.
10. Revisa el texto y pulsa `Aprobar versión revisada`.
11. Confirma que el estado cambie a `Aprobado`.
12. Revisa el registro en `Historial asistivo`.

## Criterios de aceptación

- el proveedor no modifica entidades jurídicas;
- el contexto se selecciona explícitamente;
- las respuestas usan solo códigos permitidos;
- las afirmaciones sin cita se detectan;
- la aprobación exige trazabilidad completa;
- el texto original se preserva;
- las partes pueden anonimizarse;
- no existen llamadas externas ni secretos;
- la migración SQLite es aditiva;
- las pruebas anteriores continúan aprobadas.

## Limitaciones

- el proveedor simulado no realiza razonamiento generativo real;
- la detección de inyección y de afirmaciones sin soporte es heurística;
- la cobertura de citas mide forma de trazabilidad, no verdad jurídica;
- la anonimización sustituye alias registrados, no entidades no registradas;
- no existe todavía conexión con un proveedor remoto o modelo local real;
- los borradores aprobados no se incorporan automáticamente al informe
  jurídico integral.

## Próximo incremento

Sprint 4.3.1 conectará un proveedor real opcional mediante variables de
entorno, consentimiento explícito, vista previa exacta del contexto, control
de tiempo y costo, reintentos limitados y pruebas contractuales. El modo
simulado seguirá disponible para desarrollo y pruebas.
