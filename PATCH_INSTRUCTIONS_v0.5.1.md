# Instrucciones del parche — IUS-Razón Sprint 4.3.1 v0.5.1

## 1. Detener Streamlit

Presiona físicamente `Ctrl + C` en la terminal donde corre la aplicación.

## 2. Confirmar el punto de partida

Desde la raíz del proyecto:

```powershell
Get-Location
git status
git tag --list
Test-Path .\data_test\ius_razon_test.db
```

La etiqueta `v0.4.4` y el respaldo previo de la base pueden conservarse. Este
hotfix no necesita migración de datos.

## 3. Respaldo adicional opcional

```powershell
$backupDir = Join-Path `
    (Split-Path (Get-Location) -Parent) `
    "IUS_Razon_backups"

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

$backupFile = Join-Path `
    $backupDir `
    "ius_razon_test_pre_sprint431_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"

Copy-Item .\data_test\ius_razon_test.db $backupFile -Force
Get-Item $backupFile | Select-Object FullName, Length, LastWriteTime
```

## 4. Aplicar el parche

Copia `IUS_Razon_Sprint_4_3_1_patch_v0.5.1.zip` a la raíz y ejecuta:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_3_1_patch_v0.5.1.zip `
    -DestinationPath . `
    -Force
```

## 5. Reinstalar el paquete editable

```powershell
python -m pip install `
    -e . `
    --no-deps `
    --no-cache-dir `
    --force-reinstall
```

## 6. Verificar versión

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Esperado:

```text
Instalada: 0.5.1
Módulo: 0.5.1
Ruta: ...\src\ius_razon\__init__.py
```

## 7. Calidad y pruebas

```powershell
ruff check .

Remove-Item .\.mypy_cache -Recurse -Force -ErrorAction SilentlyContinue
python -m mypy --config-file .\pyproject.toml src

pytest -v
```

Esperado:

```text
All checks passed!
Success: no issues found in 29 source files
88 passed
```

## 8. Iniciar la aplicación

```powershell
streamlit run app.py
```

Abre:

```text
http://localhost:8501
```

## 9. Validación funcional

En `Asistente IA`:

1. selecciona `PJ-001`;
2. selecciona la ejecución con una conclusión;
3. conserva la anonimización activada;
4. elige `Resumen del expediente`;
5. usa la misma indicación de la prueba anterior;
6. genera un borrador nuevo.

No debe aparecer:

```text
PARTE-001firma
PARTE-001credita
```

Son resultados válidos, según el texto original:

```text
La parte compradora afirma
La parte compradora acredita
PARTE-001 afirma
PARTE-001 acredita
```

Las expresiones de rol permanecen sin anonimizar; las menciones exactas del
alias se sustituyen por `PARTE-001`.

## 10. Registro de versión

Después de aprobar Ruff, Mypy, Pytest y la prueba funcional:

```powershell
git add .
git commit -m "fix: anonimización segura Sprint 4.3.1 v0.5.1"
git tag -a v0.5.1 -m "IUS-Razon v0.5.1 Sprint 4.3.1 validado"
```

## Recuperación

Para regresar al código anterior:

```powershell
git switch --detach v0.4.4
```

Para continuar trabajando en `main`:

```powershell
git switch main
```

El historial `IA-001` debe conservarse como evidencia; no lo elimines.
