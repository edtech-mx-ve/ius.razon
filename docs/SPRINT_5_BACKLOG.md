# Backlog Sprint 5

## Sprint 5.1 — Privacidad y datos demo

Estado: implementado en `v0.8.0`.

- análisis determinista;
- modo público;
- bloqueo de cargas;
- ocultamiento de rutas;
- gate de exportación;
- reporte seguro.

## Sprint 5.2 — Interfaz, accesibilidad y rendimiento

- layout móvil primero;
- navegación más corta;
- foco visible;
- etiquetas y ayudas;
- header y footer;
- medición de tiempos de render;
- pruebas en 360, 768, 1024 y 1440 px.

## Sprint 5.3 — Despliegue reproducible

- configuración para Streamlit;
- base sintética;
- secretos ausentes;
- despliegue gratuito;
- verificación de URLs;
- health check;
- checklist de privacidad.

## Sprint 5.4 — Landing, documentación y cierre MVP

- landing informativa;
- guía de usuario;
- arquitectura final;
- demo guiada;
- pruebas de aceptación;
- release candidate;
- versión MVP.

## Sprint 5.4 — Página de bienvenida y acceso protegido

- Crear una página pública que explique el propósito de IUS-Razón.
- Mostrar alcance, trazabilidad, revisión humana y privacidad.
- No cargar expedientes ni repositorios antes de autenticar.
- Proteger el acceso mediante un proveedor de identidad.
- Aplicar autorización explícita para usuarios permitidos.
- Incluir cierre de sesión y pantalla de acceso denegado.
- No almacenar contraseñas propias en SQLite.
- Mantener expedientes, rutas, almacenar contraseñas propias en SQLite.
- Mant auditorías y configuración fuera de la página pública.
- Validar acceso permitido, acceso denegado y cierre de sesión.
