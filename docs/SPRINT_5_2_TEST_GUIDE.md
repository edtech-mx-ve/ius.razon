# Guía de prueba — Sprint 5.2 v0.8.1

## 1. Validación técnica

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

Resultado esperado:

```text
All checks passed!
Success: no issues found
194 passed
```

## 2. Arranque local

```powershell
Remove-Item Env:IUS_RAZON_PUBLIC_DEMO `
    -ErrorAction SilentlyContinue

streamlit run app.py
```

URL esperada:

```text
http://localhost:8501
```

## 3. Navegación

Confirme seis áreas:

```text
Inicio
Expediente
Fuentes jurídicas
Razonamiento
Argumentación e informes
Seguridad
```

Recorra las 19 secciones. La sección activa debe mostrarse en el contenido y
las demás no deben ejecutar formularios ni consultas visibles.

## 4. Teclado

1. Presione `Tab` desde el inicio.
2. Active `Saltar al contenido principal` con `Enter`.
3. Recorra área, sección, expediente y botones.
4. Confirme foco visible.
5. Active un botón con `Enter` o `Espacio`.

No debe existir un bloqueo de teclado.

## 5. Anchos de pantalla

Use las herramientas de desarrollo del navegador y pruebe:

```text
360 px
768 px
1024 px
1440 px
```

En 360 y 768 px:

- las métricas y columnas deben apilarse;
- no debe existir desplazamiento horizontal de toda la página;
- las tablas pueden desplazarse dentro de su propio contenedor;
- botones y campos deben conservar una altura táctil adecuada.

## 6. Operaciones prolongadas

En `Privacidad y demo`, ejecute un análisis y compruebe el estado de carga.

En `Asistente IA`, genere un borrador local y compruebe el estado de carga,
la auditoría, el costo cero y la revisión humana.

## 7. Modo público

```powershell
$env:IUS_RAZON_PUBLIC_DEMO = "true"
streamlit run app.py
```

Confirme cargas bloqueadas, rutas ocultas y gate activo. La navegación y los
estilos deben mantenerse.

Al terminar:

```powershell
Remove-Item Env:IUS_RAZON_PUBLIC_DEMO `
    -ErrorAction SilentlyContinue
```

## 8. Regresión

Verifique como mínimo:

- resumen;
- alta de un registro sintético;
- privacidad;
- inferencia;
- argumentación;
- informe integral;
- Asistente IA con Ollama local.
