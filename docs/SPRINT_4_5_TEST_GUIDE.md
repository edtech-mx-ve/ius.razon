# Guía de prueba — Sprint 4.5

## A. Validación técnica

```powershell
ruff check .
python -m mypy --config-file .\pyproject.toml src
pytest -v
```

Esperado: 128 pruebas aprobadas.

## B. Validación sin clave

1. Inicia Streamlit.
2. Abre `Asistente IA`.
3. Confirma que `Simulado local` funciona.
4. Confirma que `Prueba externa controlada` funciona.
5. Confirma que `OpenAI Responses API` no aparece.

## C. Validación de configuración, sin llamada

Configura temporalmente las variables no secretas y una clave de prueba no
válida solo en un entorno aislado de desarrollo. No pulses el botón de llamada.
Verifica:

- modelo visible;
- host `api.openai.com`;
- clave mostrada únicamente como “configurada”;
- límites fijos;
- costo estimado;
- contexto anonimizado;
- códigos autorizados;
- cuatro confirmaciones.

Después elimina la variable de clave.

## D. Primera llamada real

Solo después de cerrar la validación técnica:

- usa `PJ-001`;
- selecciona 4 a 7 elementos;
- conserva menos de 2048 tokens estimados;
- salida máxima 256 tokens;
- cero reintentos;
- fallback local activado;
- presupuesto máximo pequeño;
- confirma una sola llamada;
- revisa y aprueba manualmente.

## E. Auditoría

La fila debe incluir:

- modo OpenAI;
- proveedor;
- modelo;
- estado;
- códigos seleccionados;
- tokens;
- costo estimado;
- externa sí/no;
- fallback sí/no.

No debe contener clave, prompt, respuesta ni nombres de partes.

## F. Criterio de cierre

El sprint se cierra cuando la validación técnica pasa y la configuración segura
se confirma. La primera llamada real puede registrarse como evidencia separada.
