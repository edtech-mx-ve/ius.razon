# Reporte técnico — Sprint 4.5.2

## Versión

IUS-Razón `0.7.2`.

## Objetivo

Asegurar que el proveedor Ollama se encuentre disponible, que el modelo
configurado exista realmente en el equipo y que una configuración aparentemente
local no seleccione modelos cloud.

## Incremento funcional

El flujo queda:

```text
configuración
→ validación de endpoint y allowlist
→ diagnóstico local sin datos jurídicos
→ disponibilidad del servicio
→ versión de Ollama
→ modelos instalados
→ verificación del modelo configurado
→ generación o fallback
→ saneamiento
→ evaluación de citas
→ persistencia
→ revisión humana
```

## Arquitectura

### Configuración

`OllamaProviderSettings` valida:

- endpoint exacto `/api/chat`;
- loopback y puerto `11434`;
- modelo mediante patrón restringido;
- pertenencia a `allowed_models`;
- ausencia del marcador `cloud`;
- cero reintentos;
- límites de contexto;
- timeout de diagnóstico entre 1 y 15 segundos.

### Diagnóstico

`OllamaHealthProbe` usa un transporte GET separado. Solo permite:

```text
/api/version
/api/tags
```

No envía instrucciones, códigos, contexto ni texto del expediente.

### Proveedor

`OllamaLocalProvider`:

- mantiene `stream=false` y `think=false`;
- exige `done=true`;
- clasifica errores locales;
- registra costo `0.0`;
- no usa autorización;
- conserva fallback determinista.

### Transformación funcional

`normalize_context_control_statements()` transforma únicamente frases
restringidas sobre ausencia de una conclusión de inferencia. No transforma
afirmaciones jurídicas negativas generales.

Ejemplo:

```text
No se proporcionó una conclusión de inferencia.
```

se convierte en:

```text
Control de contexto: no se proporcionó una conclusión de inferencia.
```

La transformación evita el falso positivo observado en IA-010 sin debilitar el
control de citas para frases como `No se acreditó el incumplimiento.`

## Manejo de errores

Códigos principales:

| Código | Significado |
|---|---|
| `ollama_unavailable` | puerto local no disponible |
| `ollama_timeout` | tiempo agotado |
| `ollama_network_error` | fallo local de transporte |
| `ollama_model_not_installed` | modelo ausente en `/api/tags` |
| `ollama_model_not_found` | respuesta HTTP 404 |
| `ollama_overloaded` | respuesta HTTP 503 |
| `ollama_internal_error` | error HTTP 5xx |
| `ollama_incomplete_response` | respuesta sin finalización |

Los mensajes no incluyen cuerpos HTTP ni contenido jurídico.

## Pruebas

Cobertura nueva:

- allowlist y parsing de varios modelos;
- rechazo de modelos fuera de allowlist;
- rechazo parametrizado de nombres cloud;
- endpoint de versión y modelos;
- diagnóstico listo, modelo ausente e indisponibilidad;
- rechazo de respuesta incompleta;
- requisito de prefijo de control;
- normalización segura y no generalizada;
- cobertura de cita posterior a normalización;
- fallback antes de la llamada cuando falla el diagnóstico;
- integración de aplicación, vista y script.

Resultado:

```text
159 pruebas aprobadas
```

## Criterios de aceptación

- no hay API comercial activa;
- no hay clave;
- costo por solicitud USD 0;
- el modelo debe estar instalado;
- modelos cloud bloqueados;
- diagnóstico seguro visible;
- fallback controlado;
- cobertura de citas conservada;
- aprobación humana obligatoria;
- sin migración destructiva.

## Limitaciones

- el nombre del modelo es una señal de seguridad, no una prueba criptográfica
  del origen del modelo;
- la aplicación no puede verificar por API si Ollama Cloud está deshabilitado
  globalmente;
- `/api/tags` informa instalación, no disponibilidad suficiente de RAM o VRAM;
- una carrera entre diagnóstico y generación puede producir fallback;
- la calidad del texto requiere evaluación humana.

## Backlog

Sprint 4.5.3:

- métricas locales de latencia y tokens por segundo;
- presupuesto de tiempo por tarea;
- evaluación reproducible de fidelidad y citas;
- conjunto de regresión jurídica sintética;
- comparación segura entre modelos locales permitidos.

## Perfil limitado para laptop

- Ejecución por CPU, sin GPU dedicada.
- Modelo permitido: qwen3:1.7b.
- Una solicitud simultánea.
- Contexto Ollama: 2048 tokens.
- Entrada máxima: 1536 tokens.
- Salida máxima: 256 tokens.
- Reintentos: 0.
- Prioridad del proceso: BelowNormal.
- Cloud e historial desactivados.
- Descarga inmediata mediante OLLAMA_KEEP_ALIVE=0.
- ollama ps confirmó que no quedó un modelo residente.
- Servidor en reposo observado: aproximadamente 31,7 MB.
- IA-014 fue aprobada tras revisión humana con cobertura del 100 %.
