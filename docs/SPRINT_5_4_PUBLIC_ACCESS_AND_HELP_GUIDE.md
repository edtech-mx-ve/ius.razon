# Sprint 5.4 — Página pública, acceso protegido y ayuda

## Objetivo

Separar la presencia pública de IUS-Razón de su área operativa y ofrecer
orientación funcional consistente.

## Flujo

1. Página pública de bienvenida.
2. Manual de usuario público.
3. Formulario de acceso protegido.
4. Área de trabajo autenticada.
5. Manual disponible también desde el área protegida.
6. Ayuda contextual en cada sección.

## Seguridad

Los servicios y la persistencia se inicializan únicamente después del control
de acceso. La contraseña se obtiene mediante `IUS_RAZON_ACCESS_PASSWORD` desde
el entorno de despliegue o `.streamlit/secrets.toml` local.

El valor secreto no debe versionarse, registrarse ni imprimirse. La comparación
usa `hmac.compare_digest`. Si el secreto falta o es demasiado corto, el área
protegida permanece cerrada.

## Manual y ayuda contextual

El manual y la ayuda por sección comparten una sola fuente estructurada. Todas
las vistas registradas en `navigation.py` deben disponer de ayuda contextual.

## Persistencia

Este cambio no modifica PostgreSQL Neon ni introduce fallback SQLite.
