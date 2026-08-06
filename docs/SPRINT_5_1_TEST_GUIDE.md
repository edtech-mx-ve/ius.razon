# Guía de prueba — Sprint 5.1

## Prueba A: modo local

1. Mantenga `IUS_RAZON_PUBLIC_DEMO=false`.
2. Inicie Streamlit.
3. Abra `Privacidad y demo`.
4. Ejecute el análisis del expediente sintético.
5. Verifique que las cargas continúan habilitadas.
6. Verifique que el reporte no muestra valores sensibles.

Resultado esperado:

```text
Modo: Local
Gate de exportación: Informativo
```

## Prueba B: modo público

Antes de iniciar Streamlit:

```powershell
$env:IUS_RAZON_PUBLIC_DEMO = "true"
$env:IUS_RAZON_UPLOADS_ENABLED = "true"
$env:IUS_RAZON_DISPLAY_STORAGE_PATHS = "true"
$env:IUS_RAZON_REQUIRE_CLEAN_PRIVACY_SCAN_FOR_EXPORT = "false"
```

La aplicación debe forzar:

```text
Cargas: Bloqueadas
Rutas: Ocultas
Gate de exportación: Activo
```

## Prueba C: hallazgo controlado

Cree un expediente de prueba con un correo ficticio claramente identificable,
por ejemplo `demo@example.com`, y ejecute el análisis.

Resultado esperado:

- categoría `Correo electrónico`;
- gravedad `Alta`;
- ninguna tabla o exportación muestra el correo completo;
- exportaciones bloqueadas en modo público.

Elimine después el expediente de prueba conforme al flujo de gestión definido.

## Prueba D: expediente sintético limpio

Use alias como:

```text
Parte compradora A
Parte vendedora B
```

No use nombres de personas, correos, teléfonos, identificadores oficiales ni
rutas locales. El reporte debe indicar que no existen hallazgos bloqueantes.

## Limpieza de variables

```powershell
Remove-Item Env:IUS_RAZON_PUBLIC_DEMO -ErrorAction SilentlyContinue
Remove-Item Env:IUS_RAZON_UPLOADS_ENABLED -ErrorAction SilentlyContinue
Remove-Item Env:IUS_RAZON_DISPLAY_STORAGE_PATHS -ErrorAction SilentlyContinue
Remove-Item Env:IUS_RAZON_REQUIRE_CLEAN_PRIVACY_SCAN_FOR_EXPORT `
    -ErrorAction SilentlyContinue
Remove-Item Env:IUS_RAZON_PRIVACY_MAX_FINDINGS `
    -ErrorAction SilentlyContinue
```
