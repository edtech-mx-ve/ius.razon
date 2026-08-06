# Aplicación del parche Sprint 2

Desde la carpeta actual `ius_razon_sprint1`:

```powershell
Ctrl+C
Get-ChildItem . -Filter "*.db" -Recurse | ForEach-Object {
    Copy-Item $_.FullName "$($_.FullName).pre-sprint2.bak" -Force
}

Expand-Archive `
    .\IUS_Razon_Sprint_2_patch_v0.2.0.zip `
    -DestinationPath . `
    -Force

python -m pip install -e ".[dev]"
pytest -v
ruff check .
mypy src
streamlit run app.py
```

El parche no contiene `data`, `data_test`, bases SQLite, archivos cargados ni el archivo de
selección de persistencia. La inicialización añade tablas nuevas con
`CREATE TABLE IF NOT EXISTS`.

Verifica en la barra lateral que la ruta de SQLite siga apuntando a tu base recuperada.
