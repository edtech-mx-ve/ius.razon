# IUS-Razón — Sprint 5.1 (v0.8.0)

Prototipo local para estructurar expedientes jurídicos, ejecutar razonamiento
simbólico, construir redes argumentales, generar informes trazables y preparar
borradores asistivos bajo control humano.

El motor determinista permanece en la versión 3.2.0. Sprint 5.1 añade un
centro de privacidad para preparar datos sintéticos de demostración: detecta
patrones sensibles sin conservar sus valores, oculta rutas y bloquea cargas en
modo público, y puede impedir exportaciones hasta obtener un análisis limpio.

> Uso experimental y académico. No constituye asesoría jurídica, dictamen,
> predicción judicial ni verificación automática de vigencia, autenticidad,
> obligatoriedad o aplicabilidad de fuentes.



## Incremento Sprint 5.1

La versión 0.8.0 incorpora una capa transversal de privacidad y preparación de
datos de demostración.

Controles principales:

- análisis determinista de correo, CURP, RFC, CLABE, tarjeta, teléfono,
  credenciales, rutas locales y posibles nombres reales;
- hallazgos sin el valor original: solo categoría, gravedad, ubicación y huella
  SHA-256 truncada;
- pestaña `Privacidad y demo` con métricas y reporte JSON seguro;
- modo público que bloquea cargas y oculta rutas locales;
- gate opcional para impedir exportaciones con hallazgos bloqueantes;
- cero cambios de esquema SQLite;
- pruebas unitarias para reglas, configuración, truncamiento y política de
  exportación.

Configuración local predeterminada:

```text
IUS_RAZON_PUBLIC_DEMO=false
IUS_RAZON_UPLOADS_ENABLED=true
IUS_RAZON_DISPLAY_STORAGE_PATHS=true
IUS_RAZON_REQUIRE_CLEAN_PRIVACY_SCAN_FOR_EXPORT=false
```

Configuración recomendada para una demostración pública:

```text
IUS_RAZON_PUBLIC_DEMO=true
IUS_RAZON_UPLOADS_ENABLED=false
IUS_RAZON_DISPLAY_STORAGE_PATHS=false
IUS_RAZON_REQUIRE_CLEAN_PRIVACY_SCAN_FOR_EXPORT=true
```

El modo público no convierte datos reales en datos anónimos. Debe utilizarse
únicamente con expedientes sintéticos y después de revisar el reporte de
privacidad.

## Incremento Sprint 4.4

La versión 0.6.0 añade un adaptador JSON HTTPS desacoplado. La aplicación puede
operar en dos modos:

```text
Simulado local      → sin red, sin clave y reproducible
Proveedor externo   → opt-in, HTTPS, anonimizado y auditado
```

Antes de cualquier llamada externa, la interfaz muestra los códigos exactos,
cantidad de caracteres, tokens estimados, costo máximo estimado y señales de
riesgo. La llamada solo se habilita cuando la persona confirma que revisó el
contexto, autoriza esa llamada específica y acepta el límite de costo.

El endpoint externo debe aceptar un objeto JSON con `model`,
`system_instruction`, `task`, `instructions`, `context`, `allowed_codes` y
`max_output_tokens`. Debe responder con `output_text` o `text`; opcionalmente
puede incluir `request_id` y `usage.input_tokens`/`usage.output_tokens`.

El sistema registra proveedor, modelo, estado, códigos seleccionados, huellas,
tokens, costo estimado, fallback y decisión humana. No registra la clave API,
el encabezado de autorización ni el prompt completo en la tabla de auditoría.

## Hotfix Sprint 4.3.1

La versión 0.5.1 corrige una coincidencia parcial del anonimizador. Un alias
como `Compradora A` ya no puede consumir la primera letra de palabras
posteriores como `afirma` o `acredita`.

Comportamiento verificado:

```text
La parte compradora afirma.  → La parte compradora afirma.
Compradora A afirma.         → PARTE-001 afirma.
COMPRADORA A, acredita.      → PARTE-001, acredita.
```

La sustitución ahora:

- exige límites léxicos completos;
- preserva espacios y puntuación;
- procesa alias solapados en una sola pasada;
- evita reanonimizar marcadores `PARTE-###`;
- deduplica variantes del mismo alias ignorando mayúsculas;
- mantiene resultados deterministas e idempotentes.

No se modifica el esquema SQLite ni los registros `IA-###` existentes. Para
comprobar la corrección debe generarse un borrador nuevo.

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

El modo activo con modelo generativo usa exclusivamente Ollama en
`http://127.0.0.1:11434/api/chat`. La configuración rechaza hosts remotos,
puertos distintos de `11434`, rutas diferentes y esquemas no locales.

Controles de Ollama:

- sin clave API ni encabezados de autorización;
- anonimización obligatoria de alias registrados;
- selección explícita de cada elemento;
- `stream=false` y `think=false`;
- temperatura determinista y cero reintentos;
- límites de entrada, salida, contexto y tiempo;
- costo registrado como USD 0;
- fallback al proveedor simulado si Ollama no responde;
- revisión humana obligatoria antes de aprobar;
- auditoría sin contenido sensible.

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
    .\IUS_Razon_Sprint_4_4_patch_v0.6.0.zip `
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
Instalada: 0.6.0
Módulo: 0.6.0
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
100 passed
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

- el adaptador externo usa un contrato JSON genérico y puede requerir un
  gateway para proveedores con esquemas propietarios;
- la estimación de tokens por caracteres es aproximada;
- el costo depende de tarifas configuradas por el usuario;
- la detección de inyección y de afirmaciones sin soporte es heurística;
- la cobertura de citas mide trazabilidad formal, no verdad jurídica;
- los borradores aprobados no se incorporan automáticamente al informe.

## Próximo incremento

Sprint 4.5 evaluará calidad del proveedor externo con un conjunto de casos,
métricas de fidelidad, regresiones, comparación de modelos y presupuesto
acumulado por expediente.

## Sprint 4.4.1 · Prueba externa controlada

La versión 0.6.1 añade un proveedor falso de integración que permite validar
el flujo externo sin red, sin clave API y sin costo. El perfil exige
anonimización, consentimiento, una sola invocación, cero reintentos, fallback
local y revisión humana.

```text
Entrada máxima: 2048 tokens
Salida máxima: 256 tokens
Costo máximo: USD 0.01
Tiempo máximo: 15 segundos
Red: desactivada
```

Este modo no sustituye una prueba con un adaptador comercial específico.

## Sprint 4.5 · Adaptador OpenAI archivado y no activo

La versión 0.7.0 incorporó un adaptador específico para OpenAI mediante el
endpoint fijo `https://api.openai.com/v1/responses`. El adaptador usa la
biblioteca estándar de Python, no añade dependencias y permanece desactivado
hasta que todas las variables requeridas estén configuradas.

> Estado actual: este adaptador se conserva solo como referencia histórica.
> `app.py` no lo instancia y la interfaz no ofrece OpenAI ni proveedores
> comerciales. La integración activa de v0.7.1 es Ollama local gratuito.

Controles obligatorios:

- anonimización de partes;
- selección exacta de contexto;
- tres confirmaciones de consentimiento;
- confirmación de una sola llamada real;
- cero reintentos;
- fallback local obligatorio;
- límite de entrada, salida, tiempo y costo;
- `store=false`;
- sin herramientas externas;
- auditoría sin prompt, respuesta o clave;
- revisión humana antes de aprobar.

La clave se obtiene exclusivamente desde `OPENAI_API_KEY`. Las tarifas se
declaran mediante variables de entorno para evitar costos hardcodeados y deben
revisarse antes de habilitar el proveedor.

La opción `OpenAI Responses API` solo aparece cuando la configuración es válida.
Los modos `Simulado local` y `Prueba externa controlada` continúan disponibles
sin red.

### Variables

Consulta `docs/OPENAI_ENV.example.txt`. No copies una clave real en archivos,
Git, capturas, logs o mensajes.

### Validación

```powershell
python -c "from importlib.metadata import version; import ius_razon; print(version('ius-razon')); print(ius_razon.__version__)"
ruff check .
python -m mypy --config-file .\pyproject.toml src
pytest -v
```

Resultado previsto:

```text
0.7.0
0.7.0
All checks passed!
Success: no issues found
128 passed
```

### Limitaciones

- la estimación previa de tokens se basa en caracteres y es aproximada;
- las tarifas deben actualizarse manualmente según el modelo elegido;
- una respuesta puede ser rechazada después de la llamada si el uso reportado
  supera el presupuesto autorizado;
- el adaptador no verifica la vigencia jurídica de las fuentes;
- el sprint no realiza llamadas reales durante pruebas automatizadas;
- una primera llamada real debe usar exclusivamente el expediente de
  demostración y un contexto reducido.

## Sprint 4.5.1 · Ollama local gratuito

La versión 0.7.1 activa un proveedor específico para Ollama con el modelo
predeterminado `qwen3:1.7b`.

```text
Proveedor: Ollama local gratuito
Endpoint: http://127.0.0.1:11434/api/chat
Modelo: qwen3:1.7b
Clave API: no requerida
Costo por solicitud: USD 0
Entrada máxima: 3072 tokens estimados
Salida máxima: 512 tokens
Ventana de contexto: 4096 tokens
Reintentos: 0
Razonamiento visible: desactivado
Streaming: desactivado
```

La interfaz solo ofrece:

```text
Simulado local
Ollama local gratuito
Prueba externa controlada
```

OpenAI y el proveedor externo genérico no forman parte del flujo activo.

### Variables opcionales

Consulta `docs/OLLAMA_ENV.example.txt`. Con la instalación estándar de Ollama
no es necesario configurar variables.

### Validación

```powershell
python -c "from importlib.metadata import version; import ius_razon; print(version('ius-razon')); print(ius_razon.__version__)"
ruff check .
python -m mypy --config-file .\pyproject.toml src
pytest -v
```

Resultado previsto:

```text
0.7.1
0.7.1
All checks passed!
Success: no issues found
142 passed
```

## Sprint 4.5.2 · Diagnóstico y robustez de Ollama

La versión 0.7.2 añade un preflight local antes de cada generación con Ollama:

```text
GET http://127.0.0.1:11434/api/version
GET http://127.0.0.1:11434/api/tags
```

Estas consultas no incluyen datos del expediente. Verifican únicamente:

- disponibilidad del servicio;
- versión informada por Ollama;
- modelos instalados;
- presencia exacta del modelo configurado;
- tiempo máximo de diagnóstico.

La configuración incorpora una allowlist explícita. El modelo activo debe
pertenecer a `IUS_RAZON_OLLAMA_ALLOWED_MODELS`. Los identificadores que declaran
ejecución cloud quedan rechazados aun cuando el endpoint sea `localhost`.

Perfil predeterminado:

```text
IUS_RAZON_OLLAMA_MODEL=qwen3:1.7b
IUS_RAZON_OLLAMA_ALLOWED_MODELS=qwen3:1.7b
IUS_RAZON_OLLAMA_HEALTH_TIMEOUT_SECONDS=5
```

El panel de Streamlit muestra estado, versión, instalación del modelo y código
de error seguro. Si el diagnóstico falla durante una generación y el fallback
está habilitado, se genera un borrador determinista local sin invocar el modelo.

Los fallos locales se clasifican sin exponer el cuerpo de la respuesta:

```text
ollama_unavailable
ollama_timeout
ollama_network_error
ollama_model_not_installed
ollama_model_not_found
ollama_overloaded
ollama_internal_error
ollama_incomplete_response
```

La salida local también normaliza exclusivamente declaraciones operativas sobre
la ausencia de una conclusión de inferencia. La forma final comienza con
`Control de contexto:` para que el validador no la confunda con una afirmación
jurídica sustantiva. Otras afirmaciones negativas continúan exigiendo cita.

### Diagnóstico por consola

```powershell
python .\scripts\diagnose_ollama.py
```

Resultado esperado:

```json
{
  "ready": true,
  "service_available": true,
  "model_installed": true,
  "configured_model": "qwen3:1.7b",
  "estimated_cost_usd": 0.0
}
```

### Validación v0.7.2

```powershell
python -c "from importlib.metadata import version; import ius_razon; print(version('ius-razon')); print(ius_razon.__version__)"
ruff check .
python -m mypy --config-file .\pyproject.toml src
pytest -q
```

Resultado previsto:

```text
0.7.2
0.7.2
All checks passed!
Success: no issues found
159 passed
```

