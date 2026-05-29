"""
Cliente Supabase para operaciones auxiliares (health check, Storage, etc.).

La API principal usa SQLAlchemy + DATABASE_URL (Postgres de Supabase).
El cliente Python se usa para verificar conectividad y extensiones futuras.
"""

from __future__ import annotations

from functools import lru_cache

from config.settings import settings
from src.utils.logger import logger

_client = None


def get_supabase_client():
    """
    Obtener cliente Supabase (lazy singleton).

    Returns:
        Cliente supabase o None si no está configurado.
    """
    global _client
    if _client is not None:
        return _client

    if not settings.supabase_configured:
        return None

    try:
        from supabase import create_client

        _client = create_client(
            settings.SUPABASE_URL.strip(),
            settings.SUPABASE_SERVICE_ROLE_KEY.strip(),
        )
        return _client
    except ImportError:
        logger.warning("Paquete 'supabase' no instalado.")
        return None
    except Exception as exc:
        logger.error(f"Error al crear cliente Supabase: {exc}")
        return None


def check_supabase_connection() -> dict:
    """
    Verificar conectividad con el proyecto Supabase.

    Returns:
        dict con status y mensaje.
    """
    if not settings.supabase_configured:
        return {
            "configured": False,
            "connected": False,
            "message": "Variables SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY no configuradas",
        }

    client = get_supabase_client()
    if client is None:
        return {
            "configured": True,
            "connected": False,
            "message": "No se pudo inicializar el cliente Supabase",
        }

    try:
        # Consulta ligera para validar credenciales
        client.table("users").select("id").limit(1).execute()
        return {
            "configured": True,
            "connected": True,
            "message": "Conexión Supabase OK",
        }
    except Exception as exc:
        return {
            "configured": True,
            "connected": False,
            "message": str(exc),
        }
