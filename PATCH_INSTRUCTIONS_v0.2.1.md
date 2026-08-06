# Instrucciones del parche v0.2.1

Este parche debe aplicarse sobre IUS-Razón v0.2.0. No contiene bases de datos,
expedientes ni documentos del usuario.

## 1. Detener la aplicación

```powershell
Ctrl+C
```

## 2. Respaldar las bases

```powershell
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint21.bak" -Force
}
```

## 3. Aplicar el parche

Coloca `IUS_Razon_Sprint_2_1_patch_v0.2.1.zip` en la carpeta raíz actual:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_2_1_patch_v0.2.1.zip `
    -DestinationPath . `
    -Force
```

## 4. Reinstalar

```powershell
python -m pip install -e ".[dev]"
```

## 5. Verificar persistencia

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
```

Debe mostrar la misma base usada en Sprint 2, por ejemplo:

```text
...\data_test\ius_razon_test.db
```

## 6. Validar

```powershell
pytest -v
ruff check .
mypy src
```

Resultado esperado:

```text
20 passed
All checks passed!
Success: no issues found
```

## 7. Ejecutar

```powershell
streamlit run app.py
```

URL: `http://localhost:8501`

## Recuperación

Si fuera necesario volver a la base previa:

1. detén Streamlit;
2. conserva una copia de la base actual;
3. reemplaza la base activa por el archivo `.pre-sprint21.bak`;
4. reinicia la aplicación.

No elimines `data`, `data_test` ni `.ius_razon_persistence.json`.
