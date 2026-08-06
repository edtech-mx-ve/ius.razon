# Sprint 1 — Núcleo de expediente (v0.1.2)

## Objetivo

Entregar un incremento local, ejecutable y probado que implemente el núcleo fáctico y
probatorio de IUS-Razón.

## Funcionalidad entregada

- creación y listado de expedientes;
- ficha del expediente;
- registro de partes;
- registro de hechos con estado jurídico explícito;
- registro de pruebas;
- carga segura de archivos permitidos;
- hash SHA-256;
- vinculación entre hechos y pruebas;
- resumen cuantitativo;
- bitácora de auditoría;
- persistencia SQLite;
- interfaz Streamlit;
- configuración por variables de entorno;
- pruebas unitarias e integración.

## Decisiones técnicas

- SQLite es la fuente de verdad del prototipo local.
- Streamlit ofrece la interfaz del MVP.
- Pydantic valida los modelos de entrada.
- `sqlite3` evita añadir una capa ORM antes de validar el dominio.
- Redis y WebSockets no son dependencias del Sprint 1.
- Los archivos cargados se almacenan fuera del repositorio y no se ejecutan.
- La bitácora registra identificadores y tipos de evento, no el contenido jurídico.

## Pruebas ejecutadas

Resultado verificado:

```text
6 passed
```

También se validó la compilación sintáctica de todo el proyecto.

## Criterios de aceptación

- [x] Crear y recuperar expedientes.
- [x] Registrar partes, hechos y pruebas.
- [x] Separar alegación, acreditación, controversia y desconocimiento mediante estados.
- [x] Relacionar hechos con pruebas.
- [x] Validar modelos, tamaños y extensiones.
- [x] Rechazar archivos ejecutables.
- [x] Generar identificadores H-001 y P-001 por expediente.
- [x] Mantener una bitácora de operaciones.
- [x] Ejecutar pruebas automatizadas.
- [x] Proporcionar instrucciones de instalación local.

## Limitaciones

- No incluye todavía normas, jurisprudencia ni doctrina.
- No implementa inferencia jurídica.
- No permite editar o eliminar registros desde la interfaz.
- No incorpora autenticación.
- No debe utilizarse para expedientes confidenciales en despliegues públicos.
- La aplicación aún no fue validada por especialistas jurídicos.

## Backlog inmediato

1. Entidades `Norma`, `Jurisprudencia`, `Doctrina` y `ProblemaJuridico`.
2. Versionado y vigencia de normas.
3. Matriz problema–fuente.
4. Importación básica de texto desde PDF, TXT y DOCX.
5. Edición y eliminación controlada con confirmación.
6. Exportación JSON y Markdown.
7. Casos sintéticos de demostración.

# Implementación

## Windows PowerShell

```powershell
cd ius_razon_sprint1

py -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

pytest -v
ruff check .
mypy src
streamlit run app.py
```

## URL

```text
http://localhost:8501
```

## Resultado esperado

1. La página muestra el título `IUS-Razón`.
2. El usuario crea un expediente civil o mercantil.
3. La app permite agregar partes, hechos y pruebas.
4. La pestaña `Hecho–prueba` permite vincular una prueba a un hecho.
5. El resumen muestra los conteos y los eventos recientes.
6. Los datos quedan en `data/ius_razon.db`.
7. Los archivos quedan en `data/uploads/<case_id>/`.
8. Los logs quedan en `data/logs/ius_razon.log`.

## Validación funcional

```powershell
pytest
python -m compileall app.py src tests
```

Resultado esperado:

```text
6 passed
```


## Mantenimiento v0.1.2

Se corrigieron las 19 observaciones reportadas por Ruff:

- `F401`: importaciones no utilizadas;
- `E402`: orden de importaciones;
- `UP037`: anotación futura innecesariamente entrecomillada;
- `UP042`: migración de `str, Enum` a `StrEnum`;
- `UP017`: uso de `datetime.UTC`;
- `UP035`: importación de `Iterator` desde `collections.abc`;
- `E501`: línea superior a 100 caracteres.

La suite funcional continúa con 6 pruebas aprobadas y el modelo de datos no cambió.


## Hotfix v0.1.2 — persistencia estable

Se corrigió un problema de continuidad de datos causado por el uso temporal de variables
de entorno en PowerShell. La aplicación ahora:

- memoriza la ruta absoluta de la base SQLite;
- detecta bases previas en `data` y `data_test`;
- muestra la ruta activa en la barra lateral;
- genera un respaldo automático al iniciar;
- mantiene compatibilidad con el esquema existente.
