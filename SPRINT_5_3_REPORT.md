# Sprint 5.3 — Demo pública reproducible y despliegue

## Resultado

IUS-Razón `v0.8.1` quedó desplegada como demostración pública reproducible en:

`https://ius-razon.streamlit.app`

La aplicación se ejecuta desde la rama `main`, utiliza datos exclusivamente sintéticos y conserva separado el entorno local. El expediente `DEMO-001 | Incumplimiento contractual sintético` permite comprobar las funciones principales sin exponer expedientes reales, archivos adjuntos, secretos ni rutas privadas.

## Implementación

El Sprint 5.3 incorporó:

- configuración reproducible para Streamlit Community Cloud;
- generador determinista de base sintética;
- modo demo activado mediante `IUS_RAZON_DEMO_MODE=true`;
- creación o reparación automática de `data/ius_razon_demo.db`;
- compatibilidad con una ruta demo personalizada;
- separación entre persistencia local y demostración pública;
- instalación del paquete local mediante `-e .` en `requirements.txt`;
- inclusión de una base sintética inicial para el despliegue web;
- documentación y pruebas específicas del modo demo;
- despliegue final desde `main` con `app.py`.

## Base sintética

La base de demostración contiene:

- 1 expediente;
- 2 partes;
- 3 hechos;
- 3 pruebas;
- 3 vínculos hecho-prueba;
- 2 problemas jurídicos;
- 2 normas;
- 1 referencia jurisprudencial;
- 1 referencia doctrinal;
- 4 vínculos problema-fuente.

Todos los datos están identificados como sintéticos. Las referencias normativas no se presentan como legislación vigente y las pruebas no contienen archivos adjuntos ni metadatos de archivos reales.

## Persistencia y privacidad

El modo demo:

- no lee `.ius_razon_persistence.json`;
- no modifica la ubicación persistente de la base local;
- usa `data/ius_razon_demo.db`;
- conserva el funcionamiento normal de `data/ius_razon.db` fuera del modo demo;
- evita incluir datos personales, expedientes reales, claves, rutas absolutas o adjuntos;
- reconstruye la base sintética cuando no existe o no contiene expedientes.

La base local del usuario permanece fuera del repositorio mediante las reglas de `.gitignore`.

## Configuración del despliegue

- repositorio: `edtech-mx-ve/ius.razon`;
- rama: `main`;
- archivo principal: `app.py`;
- versión de Python: `3.14`;
- secreto de ejecución: `IUS_RAZON_DEMO_MODE = "true"`;
- URL pública: `https://ius-razon.streamlit.app`.

## Validación ejecutada

- Ruff: aprobado;
- Mypy: aprobado sobre 45 archivos fuente;
- Pytest: 203 pruebas aprobadas;
- pruebas nuevas del Sprint 5.3: 9;
- `git diff --check`: aprobado;
- instalación del paquete local: aprobada;
- importación de `ius_razon` en Streamlit: aprobada;
- generación de base sintética en Windows y Linux: aprobada;
- despliegue desde `main`: aprobado;
- revisión manual de las funcionalidades públicas: aprobada;
- revisión visual del expediente sintético: aprobada;
- exposición de rutas o datos locales: no detectada.

## Incidencias resueltas

Durante el despliegue se corrigieron:

1. bloqueo de archivos SQLite en Windows por conexiones no cerradas;
2. ausencia del paquete local `ius_razon` en Streamlit Community Cloud;
3. ejecución inicial sin el modo demo activado;
4. ausencia de una base inicial dentro del despliegue;
5. recreación del despliegue para utilizar la rama `main`.

## Commits principales

- `2edd495` — iniciar despliegue reproducible Sprint 5.3;
- `9a83346` — agregar base sintética reproducible Sprint 5.3;
- `3015612` — integrar modo demo público Sprint 5.3;
- `c7e1d47` — instalar paquete local en Streamlit Cloud;
- `bb72b00` — incluir base sintética inicial para demo web.

## Limitaciones

- Streamlit Community Cloud no garantiza persistencia permanente del sistema de archivos del contenedor.
- Las modificaciones realizadas por visitantes pueden perderse después de un reinicio o redespliegue.
- La base sintética incluida en el repositorio actúa como estado inicial reproducible.
- Una versión web con persistencia permanente requerirá una base de datos externa.
- La aplicación continúa siendo un prototipo académico y no constituye asesoría jurídica, dictamen ni predicción judicial.

## Criterios de aceptación

1. La aplicación se despliega desde `main`.
2. La URL pública abre correctamente.
3. El expediente sintético aparece al iniciar.
4. Las funcionalidades principales están disponibles.
5. El modo demo no utiliza la persistencia local.
6. La base sintética puede reconstruirse automáticamente.
7. No se publican expedientes reales ni archivos privados.
8. Ruff, Mypy y Pytest aprueban.
9. La configuración de Streamlit es reproducible.
10. Las limitaciones de persistencia están documentadas.

## Cierre

El Sprint 5.3 queda completado el 6 de agosto de 2026. IUS-Razón dispone de una demostración pública funcional, segura y reproducible, integrada en `main` y disponible para revisión mediante Streamlit Community Cloud.
