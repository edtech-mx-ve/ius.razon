# Guía de prueba — Sprint 4.4 v0.6.0

## Prerrequisitos

- rama `feature/sprint-4.4`;
- respaldo SQLite verificado;
- entorno virtual activo;
- parche aplicado;
- versión instalada 0.6.0.

## Validación técnica

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

Resultado esperado:

```text
All checks passed!
Success: no issues found in 30 source files
100 passed
```

El número exacto de archivos de Mypy puede variar si el entorno incluye
módulos auxiliares; no debe haber errores.

## Prueba funcional A — modo simulado

1. Ejecuta `streamlit run app.py`.
2. Abre `Asistente IA`.
3. Selecciona `Simulado local`.
4. Selecciona `PJ-001` y la ejecución `3385ccd1`.
5. Conserva las categorías y elementos.
6. Elige `Resumen del expediente`.
7. Genera un borrador.
8. Verifica cobertura, referencias y anonimización.
9. Aprueba la versión revisada.
10. Comprueba el historial y la auditoría.

Esperado:

```text
Modo: Simulado local
Proveedor: Simulado local
Estado de auditoría: Completada
Externa: No
Fallback: No
```

## Prueba funcional B — proveedor externo

Esta prueba es opcional y requiere un endpoint HTTPS compatible.

Configura las variables solo en la sesión actual de PowerShell:

```powershell
$env:IUS_RAZON_LLM_EXTERNAL_ENABLED = "true"
$env:IUS_RAZON_LLM_ENDPOINT = "https://SU-GATEWAY/generate"
$env:IUS_RAZON_LLM_API_KEY = "SU-CLAVE"
$env:IUS_RAZON_LLM_MODEL = "SU-MODELO"
$env:IUS_RAZON_LLM_MAX_COST_USD = "0.10"
```

Reinicia Streamlit. En `Asistente IA`:

1. selecciona `Proveedor externo`;
2. revisa host, modelo y códigos;
3. conserva `Anonimizar partes`;
4. revisa caracteres, tokens y costo;
5. marca las tres confirmaciones;
6. genera;
7. revisa referencias inválidas y afirmaciones sin cita;
8. aprueba o rechaza;
9. abre `Auditoría de proveedores`.

No pegues la clave en la interfaz, archivos o mensajes de revisión.

## Prueba de fallback

Con `Fallback al modo local` activado, usa un endpoint temporalmente no
disponible. El borrador debe indicar:

```text
Fallback local utilizado
Proveedor final: Simulado local
Estado de auditoría: Fallback local
```

## Cierre

Después de aprobar las pruebas:

```powershell
git add .
git commit -m "feat: proveedor LLM externo controlado Sprint 4.4 v0.6.0"
git tag -a v0.6.0 -m "IUS-Razon v0.6.0 Sprint 4.4 validado"
```
