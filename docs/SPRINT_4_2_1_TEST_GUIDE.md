# Guía de prueba funcional — Sprint 4.2.1

## Preparación

Deja activa la base habitual y ejecuta una inferencia válida para `PJ-001`.

```powershell
Write-Host $env:IUS_RAZON_DB_PATH
streamlit run app.py
```

## Prueba 1 — Informe básico

En `Informe integral` selecciona:

```text
Problema: PJ-001
Ejecución: una ejecución con incumplimiento_entrega=Verdadero
Escenario base: Vista completa
Escenario comparado: Sin comparación
```

Genera el informe con las tres opciones de detalle activas.

## Resultado esperado

En los hallazgos debe aparecer una redacción equivalente a:

```text
La red argumental base contiene 2 argumentos favorables y
1 argumento adverso; registra 0 objeciones pendientes.
```

Para `ARG-003` debe aparecer una nota equivalente a:

```text
ARG-003 es un argumento manual sin conclusión inferida asociada;
su tesis y trazabilidad fueron registradas por el usuario.
```

No debe aparecer:

```text
ARG-003: faltan conclusión inferida.
```

## Prueba 2 — Exportaciones

Descarga JSON, Markdown y DOCX.

Comprueba:

```text
Versión del informe: 4.2.1
Origen de ARG-003: Manual
Conclusión de ARG-003: No aplica (argumento manual)
```

En el vínculo hecho–prueba no debe existir puntuación duplicada.

## Prueba 3 — Calidad estática

```powershell
ruff check .
mypy src
pytest -v
```

Resultado esperado:

```text
All checks passed!
Success: no issues found
70 passed
```

## Criterios de aceptación

- Los argumentos manuales no generan falsos vacíos.
- La concordancia singular/plural es correcta.
- No existen dobles puntos al final de vínculos.
- JSON, Markdown y DOCX se generan correctamente.
- La huella del informe permanece determinista.
- La base existente se conserva.
