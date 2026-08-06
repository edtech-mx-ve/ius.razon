# Implementación — Sprint 5.1 v0.8.0

## Entorno

- Windows PowerShell.
- Python 3.11 o superior.
- Proyecto base IUS-Razón `v0.7.2`.
- Rama recomendada `feature/sprint-5.1`.

## 1. Preparar la rama

```powershell
git switch main
git status
git tag --list "v0.7.2"
git switch -c feature/sprint-5.1
```

El árbol debe estar limpio antes de aplicar el parche.

## 2. Respaldo

```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "..\IUS_Razon_backups"

New-Item -ItemType Directory -Path $backupDir -Force |
    Out-Null

$backupPath = Join-Path `
    $backupDir `
    "ius_razon_test_pre_sprint51_$timestamp.db"

Copy-Item ".\data_test\ius_razon_test.db" $backupPath

Get-Item $backupPath
Get-FileHash $backupPath -Algorithm SHA256
```

## 3. Aplicar el parche

Coloque el ZIP en la raíz del proyecto:

```powershell
Expand-Archive `
    ".\IUS_Razon_Sprint_5_1_patch_v0.8.0.zip" `
    -DestinationPath . `
    -Force
```

## 4. Reinstalar

```powershell
python -m pip install `
    -e . `
    --no-deps `
    --no-cache-dir `
    --force-reinstall
```

## 5. Verificar versión

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Esperado:

```text
Instalada: 0.8.0
Módulo: 0.8.0
```

## 6. Calidad

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
176 passed
```

## 7. Ejecución

Modo local:

```powershell
streamlit run app.py
```

URL esperada:

```text
http://localhost:8501
```

Modo público de prueba:

```powershell
$env:IUS_RAZON_PUBLIC_DEMO = "true"
streamlit run app.py
```

## 8. Validación funcional

Abra `Privacidad y demo` y pulse `Ejecutar análisis de privacidad`.

Resultado esperado en modo público:

```text
Cargas: Bloqueadas
Rutas: Ocultas
Gate de exportación: Activo
```

No haga `commit`, `merge` ni etiqueta hasta completar las pruebas locales.
