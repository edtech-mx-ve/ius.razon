# Reporte técnico — Sprint 5.1

## Objetivo

Preparar IUS-Razón para demostraciones con datos sintéticos sin exponer
accidentalmente datos personales, credenciales o rutas locales.

## Incremento

La versión `0.8.0` incorpora:

- `PrivacySettings`: configuración inmutable y validada.
- `privacy_scanner.py`: transformaciones puras de extracción y detección.
- `PrivacyService`: orquestación sobre el expediente.
- `privacy_view.py`: interfaz de revisión y exportación segura.
- gate de exportación para JSON, Markdown, DOCX y DOT.
- bloqueo de cargas y rutas cuando `IUS_RAZON_PUBLIC_DEMO=true`.

## Arquitectura

```text
security/privacy_config.py
security/privacy_scanner.py
services/privacy_service.py
ui/privacy_view.py
tests/test_sprint_51_privacy.py
```

La arquitectura usa funciones puras para detección y serialización, una clase de
servicio para orquestación y un flujo estructurado en la interfaz.

## Datos y persistencia

- No hay migraciones.
- No se modifica la base SQLite.
- No se guardan valores detectados.
- No se escriben hallazgos en tablas.
- El reporte JSON contiene categoría, gravedad, ubicación y huella.

## Política de demostración pública

Con `IUS_RAZON_PUBLIC_DEMO=true`:

- las cargas quedan deshabilitadas;
- las rutas locales no se muestran;
- el gate de exportación queda activo;
- solo un reporte sin hallazgos críticos, altos o medios habilita exportaciones.

## Criterios de aceptación

- El modo local mantiene el comportamiento existente.
- El modo público bloquea cargas incluso si otra variable intenta habilitarlas.
- Un correo o identificador sensible no aparece en el reporte exportado.
- Un posible nombre real de parte bloquea la exportación pública.
- Un alias genérico de demostración no se clasifica como nombre real.
- El límite de hallazgos produce un reporte marcado como truncado.
- La aplicación compila y la suite automatizada pasa.

## Validación ejecutada en el artefacto

- `compileall`: aprobado.
- `pytest`: 176 pruebas aprobadas.
- construcción de wheel `0.8.0`: aprobada.
- Llamadas de red durante pruebas: 0.
- Cambios de esquema: 0.

Ruff y Mypy deben confirmarse en el entorno local del proyecto.

## Limitaciones

La detección por expresiones regulares no garantiza anonimización. Antes de una
publicación debe revisarse manualmente el expediente y utilizarse solo
información sintética.

## Backlog siguiente

Sprint 5.2:

- optimización móvil;
- accesibilidad por teclado;
- jerarquía visual;
- rendimiento de la interfaz;
- header y footer institucionales;
- pruebas de anchos y contraste.
