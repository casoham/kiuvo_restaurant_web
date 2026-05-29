"""
Verifica conexión a Supabase: PostgreSQL (SQLAlchemy/psycopg2) y API REST.

Uso: python test_supabase.py
"""

from __future__ import annotations

import re
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def _mask_db_url(url: str) -> str:
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)


def test_packages() -> bool:
    print("1. Paquetes...")
    try:
        import psycopg2  # noqa: F401
        _ok("psycopg2")
    except ImportError:
        _fail("psycopg2 no instalado (pip install psycopg2-binary)")
        return False
    try:
        import sqlalchemy  # noqa: F401
        _ok("sqlalchemy")
    except ImportError:
        _fail("sqlalchemy no instalado")
        return False
    return True


def test_postgres() -> bool:
    import os

    print("2. PostgreSQL (DATABASE_URL)...")
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        _fail("DATABASE_URL no definida en .env")
        return False

    _ok(f"URL: {_mask_db_url(db_url)}")

    if "db." in db_url and ".supabase.co" in db_url:
        print(
            "  [AVISO] Usas host db.* (IPv6). Si falla DNS, cambia al pooler "
            "(aws-1-REGION.pooler.supabase.com:6543)."
        )

    try:
        import psycopg2

        conn = psycopg2.connect(db_url, connect_timeout=15)
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        table_count = cur.fetchone()[0]
        conn.close()
        _ok(f"Conexion PostgreSQL ({table_count} tablas public)")
        print(f"       {version[:70]}...")
        return True
    except Exception as exc:
        _fail(str(exc))
        parsed = urlparse(db_url)
        print(f"       host={parsed.hostname} port={parsed.port} user={parsed.username}")
        return False


def test_sqlalchemy() -> bool:
    print("3. SQLAlchemy (config.database)...")
    try:
        from sqlalchemy import text

        from config.database import engine

        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        _ok(f"Engine OK (users: {n} filas)")
        return True
    except Exception as exc:
        _fail(str(exc))
        return False


def test_supabase_api() -> bool:
    print("4. API REST Supabase...")
    try:
        from config.settings import settings
        from src.integrations.supabase_client import check_supabase_connection

        if not settings.supabase_configured:
            _fail("SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY vacios")
            return False

        result = check_supabase_connection()
        if result.get("connected"):
            _ok(result.get("message", "Conectado"))
            return True
        _fail(result.get("message", "Sin conexion"))
        return False
    except Exception as exc:
        _fail(str(exc))
        return False


def main() -> int:
    print("=== Prueba de conexion Supabase ===\n")
    steps = [
        test_packages,
        test_postgres,
        test_sqlalchemy,
        test_supabase_api,
    ]
    results = [fn() for fn in steps]
    print()
    if all(results):
        print("=== Todas las pruebas pasaron ===")
        return 0
    print("=== Algunas pruebas fallaron ===")
    return 1


if __name__ == "__main__":
    sys.exit(main())
