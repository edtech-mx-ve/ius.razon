# Reporte técnico — Sprint 4.3.1 v0.5.1

## Objetivo

Corregir la anonimización parcial observada en el borrador `IA-001`, donde el
alias `Compradora A` podía coincidir con el inicio de expresiones como
`compradora afirma` y `compradora acredita`, produciendo textos como
`PARTE-001firma` y `PARTE-001credita`.

## Diagnóstico

La versión 0.5.0 construía una expresión regular con el alias escapado, pero
sin límites léxicos. Como la coincidencia no distinguía palabras completas, el
alias `Compradora A` podía encontrar la secuencia `compradora a` formada por el
sustantivo `compradora`, el espacio y la primera letra de `afirma` o
`acredita`.

## Implementación

### Transformación funcional

`anonymize_text()` ahora:

1. sanea alias y sustituciones;
2. ordena alias por longitud para resolver solapamientos;
3. deduplica alias sin distinguir mayúsculas;
4. construye una única expresión regular;
5. exige límites léxicos antes y después del alias;
6. sustituye en una sola pasada;
7. protege identificadores ya anonimizados `PARTE-###`.

El procesamiento en una sola pasada evita que una sustitución recién creada
sea procesada nuevamente por otro alias.

### Integración

`anonymize_context_items()` conserva el contrato existente y ahora genera un
mapa determinista incluso cuando se registran variantes de mayúsculas del
mismo alias.

### Configuración de calidad

`pyproject.toml` conserva la comprobación mínima de Python 3.11 e incorpora la
exclusión localizada de los stubs externos de NumPy que usan sintaxis más
reciente. El código del proyecto continúa analizándose en modo estricto.

## Pruebas

Se añadieron seis pruebas de regresión:

- no consumir la primera letra de `afirma` o `acredita`;
- preservar el espacio después de un alias completo;
- reemplazar solo palabras completas;
- conservar puntuación y aceptar diferencias de mayúsculas;
- garantizar idempotencia con alias genéricos;
- deduplicar variantes de mayúsculas.

Resultado en el entorno de construcción:

```text
88 pruebas recopiladas
88 pruebas aprobadas
compilación sintáctica aprobada
líneas Python mayores de 100 caracteres: 0
```

Ruff y Mypy deben confirmarse en el entorno local del proyecto.

## Criterios de aceptación

| Criterio | Estado |
|---|---|
| No generar `PARTE-001firma` | Cumplido |
| No generar `PARTE-001credita` | Cumplido |
| Preservar espacios y puntuación | Cumplido |
| Sustituir alias completos | Cumplido |
| No sustituir fragmentos internos | Cumplido |
| Mantener idempotencia | Cumplido |
| No modificar SQLite | Cumplido |
| Mantener historial asistivo | Cumplido |
| Regresión automatizada | Cumplido |

## Seguridad

- No se agregan llamadas externas.
- No se aceptan ni almacenan claves.
- No se modifica el flujo de aprobación humana.
- No se reescriben borradores históricos.
- La corrección se limita a la transformación previa del contexto.

## Limitaciones

- La anonimización sustituye alias registrados, no todos los posibles datos
  personales.
- Expresiones de rol como `la parte compradora` no son alias y pueden
  mantenerse sin sustituir.
- Los borradores ya creados conservan su texto original para auditoría.
- Debe generarse un borrador nuevo para comprobar el hotfix.

## Implementación

Entorno previsto:

```text
Windows PowerShell
Python >= 3.11
Entorno virtual .venv
Aplicación Streamlit local
```

Comandos:

```powershell
Expand-Archive `
    .\IUS_Razon_Sprint_4_3_1_patch_v0.5.1.zip `
    -DestinationPath . `
    -Force

python -m pip install -e . --no-deps --no-cache-dir --force-reinstall

ruff check .
python -m mypy --config-file .\pyproject.toml src
pytest -v

streamlit run app.py
```

URL esperada:

```text
http://localhost:8501
```

Resultado esperado:

```text
Versión instalada: 0.5.1
Versión del módulo: 0.5.1
Ruff: aprobado
Mypy: aprobado
Pytest: 88 aprobadas
```
