# Instrucciones del parche v0.7.1 — Ollama local gratuito

## Entorno esperado

```text
Rama: feature/sprint-4.5.1-ollama
Versión base: v0.7.0
Ollama: instalado
Modelo: qwen3:1.7b
```

## 1. Detener la aplicación

Presiona físicamente `Ctrl + C`.

## 2. Aplicar el parche

Coloca `IUS_Razon_Sprint_4_5_1_Ollama_patch_v0.7.1.zip` en la raíz:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_5_1_Ollama_patch_v0.7.1.zip `
    -DestinationPath . `
    -Force
```

## 3. Reinstalar el paquete

```powershell
python -m pip install `
    -e . `
    --no-deps `
    --no-cache-dir `
    --force-reinstall
```

## 4. Verificar Ollama

```powershell
ollama --version
ollama list
```

Debe aparecer `qwen3:1.7b`.

## 5. Verificar la versión

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Esperado:

```text
Instalada: 0.7.1
Módulo: 0.7.1
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

pytest -v
```

Esperado:

```text
All checks passed!
Success: no issues found
142 passed
```

## 7. Ejecutar

```powershell
streamlit run app.py
```

Abre `Asistente IA` y selecciona `Ollama local gratuito`.

## Resultado esperado

- no se solicita clave;
- no aparece OpenAI;
- endpoint local `127.0.0.1:11434`;
- costo USD 0;
- salida revisable y auditable;
- aprobación humana obligatoria.

## Rollback

```powershell
git reset --hard v0.7.0
python -m pip install -e . --no-deps --force-reinstall
```

La base SQLite no requiere rollback porque el parche no introduce migraciones
destructivas.
