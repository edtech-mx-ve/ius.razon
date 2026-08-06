# Guía de pruebas — Sprint 5.4 branding institucional

## Validación automática

```powershell
ruff check .
python -m mypy --config-file .\pyproject.toml src scripts
pytest -q
git diff --check
```

## Validación visual

1. Ejecutar `streamlit run .\app.py`.
2. Confirmar que solo aparece el logo de IUS-Razón.
3. Confirmar que el logo ocupa aproximadamente el 50 % del ancho disponible.
4. Confirmar que el logo permanece centrado.
5. Confirmar que no aparece el logo de Sképsis Apps.
6. Confirmar al final la firma textual:
   `Powered by Sképsis Apps · © 2026 Sképsis Apps`.
7. Revisar la interfaz en escritorio y pantalla estrecha.