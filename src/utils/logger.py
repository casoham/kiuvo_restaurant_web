"""
Sistema de logging profesional.

Configura un logger con:
- Salida a consola (coloreada según nivel)
- Salida a archivo rotativo
- Formato consistente con timestamp, módulo y nivel
"""

import logging
import sys
from pathlib import Path

from config.settings import settings


def setup_logger(name: str = "restaurant") -> logging.Logger:
    """
    Crear y configurar un logger.

    Args:
        name: Nombre del logger (normalmente el módulo).

    Returns:
        Logger configurado.
    """
    logger = logging.getLogger(name)

    # Evitar duplicación de handlers si se llama varias veces
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG))

    # ── Formato ─────────────────────────────────────────────
    fmt = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(name)-20s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Handler: Consola ────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.DEBUG if settings.is_development else logging.INFO)
    logger.addHandler(console_handler)

    # ── Handler: Archivo ────────────────────────────────────
    try:
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        logger.warning(f"No se pudo crear archivo de log: {e}")

    return logger


# Logger global de la aplicación
logger = setup_logger("restaurant")
