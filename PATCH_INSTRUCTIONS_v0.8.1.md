# Instalación — Sprint 5.2 v0.8.1

## Requisitos

- IUS-Razón `v0.8.0` integrado en `main`;
- Python 3.11 o posterior;
- entorno virtual activo;
- árbol Git limpio;
- parche `IUS_Razon_Sprint_5_2_patch_v0.8.1.zip` en la raíz.

## 1. Preparación

```powershell
git switch main
git status
git tag --list "v0.8.0"

git switch -c feature/sprint-5.2
```

## 2. Respaldo

```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "..\IUS_Razon_backups"

New-Item `
    -ItemType Directory `
    -Path $backupDir `
    -Force |
    Out-Null

$backupPath = Join-Path `
    $backupDir `
    "ius_razon_test_pre_sprint52_$timestamp.db"

Copy-Item `
    ".\data_test\ius_razon_test.db" `
    $backupPath

Get-Item $backupPath
Get-FileHash $backupPath -Algorithm SHA256
```

Sprint 5.2 no modifica el esquema, pero el respaldo protege la validación local.

## 3. Aplicar el parche

```powershell
Expand-Archive `
    ".\IUS_Razon_Sprint_5_2_patch_v0.8.1.zip" `
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

## 5. Verificar la versión

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Esperado:

```text
Instalada: 0.8.1
Módulo: 0.8.1
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

git diff --check
git status --short
```

Esperado:

```text
All checks passed!
Success: no issues found
194 passed
```

## 7. Ejecución

```powershell
streamlit run app.py
```

URL:

```text
http://localhost:8501
```

## 8. Validación funcional

- seleccione un expediente;
- recorra las seis áreas y las 19 secciones;
- confirme que solo se muestra una sección;
- pruebe navegación con teclado;
- pruebe 360, 768, 1024 y 1440 px;
- ejecute privacidad y Asistente IA;
- confirme que el modo público conserva sus restricciones.

## 9. Archivos excluidos

No agregue al repositorio:

```text
*.zip
*.db
.env
logs
backups
```

## 10. Cierre

Solo después de validar:

```powershell
git add `
    README.md `
    PATCH_INSTRUCTIONS.md `
    PATCH_INSTRUCTIONS_v0.8.1.md `
    CHANGELOG_v0.8.1.md `
    SPRINT_5_2_REPORT.md `
    app.py `
    pyproject.toml `
    docs/ACCESSIBILITY_CHECKLIST.md `
    docs/SPRINT_5_2_TEST_GUIDE.md `
    docs/SPRINT_5_BACKLOG.md `
    src/ius_razon/__init__.py `
    src/ius_razon/security/privacy_scanner.py `
    src/ius_razon/ui/accessibility.py `
    src/ius_razon/ui/app_shell.py `
    src/ius_razon/ui/llm_assistant_view.py `
    src/ius_razon/ui/navigation.py `
    src/ius_razon/ui/performance.py `
    src/ius_razon/ui/privacy_view.py `
    tests/test_sprint_52_ui_accessibility.py

git diff --cached --check

git commit `
    -m "feat: mejorar interfaz accesibilidad y rendimiento Sprint 5.2 v0.8.1"
```

No haga `merge` ni cree `v0.8.1` hasta completar la prueba visual.
