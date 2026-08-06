# IUS-Razón v0.7.2 — Instrucciones del parche Sprint 4.5.2

## Objetivo

Robustecer Ollama local sin incorporar APIs comerciales:

- diagnóstico de disponibilidad, versión y modelos instalados;
- allowlist de modelos locales;
- bloqueo de identificadores cloud;
- clasificación segura de fallos;
- fallback determinista local;
- corrección de declaraciones de ausencia de conclusión;
- revisión humana y auditoría existentes.

No se modifica el esquema SQLite.

## Requisitos

- IUS-Razón v0.7.1 en `main`;
- entorno virtual activo;
- Ollama operativo en `http://127.0.0.1:11434`;
- modelo `qwen3:1.7b` instalado;
- archivo `IUS_Razon_Sprint_4_5_2_patch_v0.7.2.zip` en la raíz.

## Implementación

### 1. Detener Streamlit

Presiona `Ctrl + C` en la terminal donde se ejecuta.

### 2. Confirmar el punto de partida

```powershell
git switch main
git status
git tag --list "v0.7.1"
```

Esperado:

```text
On branch main
nothing to commit, working tree clean
v0.7.1
```

### 3. Crear la rama

```powershell
git switch -c feature/sprint-4.5.2
```

### 4. Respaldar la base activa

```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "..\IUS_Razon_backups"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

Copy-Item `
    ".\data_test\ius_razon_test.db" `
    "$backupDir\ius_razon_test_pre_sprint452_$timestamp.db"
```

No continúes si la ruta de la base activa es distinta; usa la ruta real de tu
configuración.

### 5. Aplicar el parche

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_5_2_patch_v0.7.2.zip `
    -DestinationPath . `
    -Force
```

### 6. Reinstalar el proyecto editable

```powershell
python -m pip install `
    -e . `
    --no-deps `
    --no-cache-dir `
    --force-reinstall
```

### 7. Verificar la versión

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Esperado:

```text
Instalada: 0.7.2
Módulo: 0.7.2
```

### 8. Confirmar Ollama y el modelo

```powershell
ollama --version
ollama list
```

Debe aparecer `qwen3:1.7b`.

### 9. Ejecutar el diagnóstico seguro

```powershell
python .\scripts\diagnose_ollama.py
```

Esperado:

```text
"ready": true
"service_available": true
"model_installed": true
"configured_model": "qwen3:1.7b"
```

El comando no envía datos del expediente.

### 10. Validar calidad

```powershell
ruff check .

Remove-Item .\.mypy_cache `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue

python -m mypy `
    --config-file .\pyproject.toml `
    src

pytest -q
```

Esperado:

```text
All checks passed!
Success: no issues found
159 passed
```

### 11. Iniciar Streamlit

```powershell
streamlit run app.py
```

URL esperada:

```text
http://localhost:8501
```

## Validación funcional

En `Asistente IA`:

1. Selecciona `Ollama local gratuito`.
2. Comprueba que el diagnóstico muestre servicio disponible, modelo instalado
   y versión de Ollama.
3. Selecciona un problema jurídico y únicamente códigos existentes.
4. Mantén `Anonimizar partes` activado.
5. Selecciona `Resumen del expediente`.
6. Genera con Ollama.
7. Verifica `Externa: No`, `Costo: USD 0.000000`, `Fallback: No`.
8. Revisa referencias y aprueba solo si la cobertura es 100 %.

Prueba de ausencia de conclusión: selecciona un contexto sin conclusión e
indica que se señale la información faltante. La salida debe usar:

```text
Control de contexto: no se proporcionó una conclusión de inferencia.
```

## Prueba de fallback

Detén Ollama desde el icono de la bandeja, actualiza el diagnóstico y genera
solo con datos de prueba. El borrador debe indicar fallback local y registrar
un código seguro como `ollama_unavailable`. Reinicia Ollama después.

## Criterios de aceptación

- versión 0.7.2;
- 159 pruebas aprobadas;
- diagnóstico sin contenido jurídico;
- modelo activo instalado y dentro de allowlist;
- nombres cloud rechazados;
- cero claves API y costo USD 0;
- cero reintentos;
- fallback determinista;
- auditoría y revisión humana conservadas;
- árbol Git limpio tras el commit.

## Limitaciones

- el diagnóstico confirma el servicio local y la presencia del modelo, no la
  calidad jurídica de la salida;
- la lista de modelos depende de `/api/tags`;
- la estimación de tokens sigue siendo aproximada;
- el bloqueo por nombre es una defensa adicional; para máxima separación puede
  deshabilitarse Ollama Cloud en la configuración de Ollama;
- el fallback no sustituye la generación del modelo.

## Cierre del sprint

No hagas merge ni etiqueta antes de completar la prueba funcional.

```powershell
git add .
git commit -m "feat: robustecer Ollama local Sprint 4.5.2 v0.7.2"

git switch main
git merge --no-ff feature/sprint-4.5.2 `
    -m "merge: Sprint 4.5.2 robustez Ollama local"

git tag -a v0.7.2 `
    -m "IUS-Razon v0.7.2 robustez Ollama local"
```
