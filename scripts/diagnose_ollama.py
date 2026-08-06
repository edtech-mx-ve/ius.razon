from __future__ import annotations

import json
import logging
from collections.abc import Sequence

from ius_razon.security.llm_ollama_config import (
    OllamaProviderConfigurationError,
    OllamaProviderSettings,
)
from ius_razon.services.llm_ollama_health import OllamaHealthProbe

LOGGER = logging.getLogger("ius_razon.ollama_diagnostic")


def run_diagnostic() -> tuple[dict[str, object], int]:
    """Ejecuta un diagnóstico local sin enviar contenido jurídico."""

    try:
        settings = OllamaProviderSettings.from_env()
        report = OllamaHealthProbe(settings).check()
    except OllamaProviderConfigurationError as exc:
        LOGGER.error("Configuración de Ollama inválida.")
        return (
            {
                "ready": False,
                "error_code": "ollama_invalid_configuration",
                "message": str(exc),
            },
            2,
        )
    return report.safe_summary(), 0 if report.ready else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada de consola."""

    del argv
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )
    summary, exit_code = run_diagnostic()
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
