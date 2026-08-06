# Sprint 5.2 — Interfaz, accesibilidad y rendimiento

## Resultado

IUS-Razón `v0.8.1` sustituye la barra de 19 pestañas por una navegación
agrupada. Cada interacción ejecuta una sola vista funcional, en lugar de
renderizar simultáneamente formularios, consultas y tablas de todas las
secciones.

## Arquitectura

La implementación separa responsabilidades:

- `navigation.py`: registro inmutable y funciones puras de navegación;
- `accessibility.py`: contrato CSS responsivo y accesible;
- `app_shell.py`: integración visual con Streamlit;
- `performance.py`: clasificación y logging de tiempos de render;
- `app.py`: despacho explícito de la vista activa.

La programación estructurada organiza el despacho; las dataclasses modelan
navegación y presupuestos; las funciones puras resuelven grupos, rutas y
clasificación; el logging registra únicamente identificador de vista, tiempo y
nivel técnico.

## Accesibilidad

Se incorporaron:

- enlace para saltar al contenido principal;
- foco visible de tres píxeles;
- controles con altura mínima de 44 px;
- apilamiento de columnas bajo 48 rem;
- tipografía fluida para encabezados;
- desplazamiento horizontal seguro en tablas;
- reducción de animaciones cuando el sistema lo solicita;
- etiquetas visibles para área y sección.

## Rendimiento

El cambio principal es arquitectónico: se eliminó el render simultáneo de 19
pestañas. El monitor clasifica cada vista con umbrales predeterminados:

- normal: menos de 1500 ms;
- advertencia: desde 1500 ms;
- crítico: desde 5000 ms.

Los logs no contienen títulos, hechos, pruebas, prompts ni valores personales.

## Validación ejecutada

- compilación de `src` y `tests`: aprobada;
- Pytest: 194 pruebas aprobadas;
- pruebas nuevas: 18;
- líneas Python mayores de 100 caracteres en archivos modificados: 0;
- llamadas reales de red durante pruebas: 0;
- cambios de esquema SQLite: 0;
- dependencias nuevas: 0.

Ruff y Mypy deben confirmarse en el entorno local del proyecto.

## Limitaciones

- las reglas CSS usan atributos internos estables de Streamlit y deben
  revisarse al actualizar la versión mayor del framework;
- la validación manual en 360, 768, 1024 y 1440 px requiere navegador;
- los objetivos de Core Web Vitals se medirán en el despliegue de Sprint 5.3;
- la página de bienvenida y el acceso protegido se implementarán en Sprint 5.4.

## Criterios de aceptación

1. Las 19 funciones siguen disponibles.
2. Solo la vista seleccionada se ejecuta.
3. La navegación funciona con teclado.
4. El foco es visible.
5. Las columnas se apilan en pantalla estrecha.
6. Las tablas no fuerzan el ancho de la página.
7. Los estados de carga aparecen en operaciones prolongadas.
8. No se modifica el esquema ni los datos jurídicos.
9. Ruff, Mypy y Pytest aprueban localmente.
10. La aplicación funciona en modo local y demostración pública.
