# Aplicación del hotfix v0.3.1

1. Detén Streamlit con `Ctrl+C`.
2. Respalda la base activa.
3. Extrae el parche en la raíz del proyecto con reemplazo.
4. Reinstala el proyecto: `python -m pip install -e ".[dev]"`.
5. Ejecuta:
   - `pytest -v`
   - `ruff check .`
   - `mypy src`
6. Inicia: `streamlit run app.py`.

El hotfix no cambia el esquema de la base de datos.
