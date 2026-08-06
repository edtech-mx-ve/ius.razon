# Instalación del parche Sprint 4.4.1 v0.6.1

## Alcance

Este parche añade una prueba externa controlada sin red y sin clave API.
No modifica el esquema SQLite ni elimina datos existentes.

## 1. Punto de partida

Ejecuta desde la raíz del proyecto:

```powershell
git branch --show-current
git status
```

Esperado:

```text
feature/sprint-4.4.1
nothing to commit, working tree clean
```

## 2. Detén Streamlit

Presiona físicamente `Ctrl + C`.

## 3. Aplica el parche

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_4_1_patch_v0.6.1.zip `
    -DestinationPath . `
    -Force
```

## 4. Reinstala

```powershell
python -m pip install `
    -e . `
    --no-deps `
    --no-cache-dir `
    --force-reinstall
```

## 5. Verifica versión

```powershell
python -c "from importlib.metadata import version; import ius_razon; print('Instalada:', version('ius-razon')); print('Módulo:', ius_razon.__version__); print('Ruta:', ius_razon.__file__)"
```

Esperado:

```text
Instalada: 0.6.1
Módulo: 0.6.1
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
112 passed
```

## 7. Ejecución

```powershell
streamlit run app.py
```

Abre `http://localhost:8501`, entra a **Asistente IA** y selecciona
**Prueba externa controlada**.

## Seguridad

- No configures una clave API para esta prueba.
- No habilites todavía el proveedor externo real.
- La prueba usa un proveedor falso local.
- No hay migraciones SQLite.
- El borrador requiere aprobación humana.

## Reversión de código

Antes de confirmar cambios:

```powershell
git restore .
```

Después de un commit local, regresa a la etiqueta estable anterior en una rama
separada:

```powershell
git switch -c recovery/v0.6.0 v0.6.0
```
