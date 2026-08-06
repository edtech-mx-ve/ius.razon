# Changelog v0.7.2 — Sprint 4.5.2

Fecha: 2026-08-06

## Añadido

- `OllamaHealthProbe` para consultar `/api/version` y `/api/tags`.
- transporte GET limitado a loopback, puerto `11434` y rutas permitidas;
- panel de diagnóstico en Streamlit;
- script `scripts/diagnose_ollama.py`;
- allowlist `IUS_RAZON_OLLAMA_ALLOWED_MODELS`;
- tiempo de diagnóstico `IUS_RAZON_OLLAMA_HEALTH_TIMEOUT_SECONDS`;
- 17 pruebas de robustez para Sprint 4.5.2.

## Cambiado

- versión del paquete a `0.7.2`;
- preflight de generación con disponibilidad y modelo instalado;
- `User-Agent` local actualizado a `IUS-Razon/0.7.2`;
- respuesta no finalizada (`done != true`) tratada como fallo;
- clasificación específica de timeout, indisponibilidad, sobrecarga,
  modelo ausente y error interno;
- declaraciones operativas sobre ausencia de conclusión se normalizan con
  `Control de contexto:` antes de evaluar citas.

## Seguridad

- rechazo de hosts remotos, redirecciones, credenciales y puertos distintos;
- rechazo de identificadores de modelo que declaran `cloud`;
- el modelo activo debe pertenecer a una allowlist explícita;
- el diagnóstico no contiene contexto, prompts ni respuestas;
- no se añaden claves, APIs comerciales ni costos por solicitud;
- fallback determinista local y revisión humana permanecen obligatorios.

## Compatibilidad

- sin cambios de esquema SQLite;
- conserva borradores, auditorías y expedientes existentes;
- conserva `qwen3:1.7b` como modelo predeterminado;
- conserva cero reintentos, `stream=false` y `think=false`.

## Validación realizada en el artefacto

- compilación Python: aprobada;
- pruebas automatizadas: 159 aprobadas;
- líneas Python mayores de 100 caracteres: 0;
- llamadas de red durante pruebas: 0.

Ruff y Mypy deben confirmarse en el entorno local del proyecto.
