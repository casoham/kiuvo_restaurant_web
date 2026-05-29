"""
Normalización de DATABASE_URL para Supabase (pooler).

El pooler exige usuario `postgres.<project_ref>`. Si se copia la URI del
dashboard con solo `postgres`, la conexión falla.
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from sqlalchemy.engine import URL, make_url


def extract_supabase_project_ref(supabase_url: str) -> str | None:
    """Extrae el project ref desde https://xxxx.supabase.co."""
    if not supabase_url:
        return None
    match = re.search(
        r"https?://([a-z0-9]+)\.supabase\.co",
        supabase_url.strip(),
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def normalize_database_url(database_url: str, supabase_url: str = "") -> str:
    """
    Devuelve una URL PostgreSQL válida para Supabase.

    - Corrige usuario `postgres` → `postgres.<project_ref>` en hosts pooler.
    - Usa componentes explícitos para evitar ambigüedad con el punto en el usuario.
    """
    raw = (database_url or "").strip()
    if not raw or raw.startswith("sqlite"):
        return raw

    if not raw.startswith("postgresql"):
        return raw

    try:
        parsed = make_url(raw)
    except Exception:
        return raw

    host = (parsed.host or "").lower()
    username = parsed.username or ""
    password = parsed.password or ""
    database = parsed.database or "postgres"
    port = parsed.port or 5432

    project_ref = extract_supabase_project_ref(supabase_url)
    if not project_ref and username.startswith("postgres."):
        project_ref = username.split(".", 1)[1]

    if "pooler.supabase.com" in host and username == "postgres" and project_ref:
        username = f"postgres.{project_ref}"

    # Usar dialecto "postgresql" (no +psycopg2): el driver +psycopg2 rompe
    # usuarios con punto (postgres.project_ref) al armar el DSN.
    normalized = URL.create(
        drivername="postgresql",
        username=username,
        password=password,
        host=parsed.host,
        port=port,
        database=database,
        query={"sslmode": "require"},
    )
    return str(normalized)


def get_psycopg2_dsn(database_url: str) -> str | None:
    """
    DSN para psycopg2.connect(dsn).

    En Windows, psycopg2.connect(user='postgres.ref') trunca el usuario a
    'postgres'. La URI con usuario codificado (%2E) evita ese bug.
    """
    raw = (database_url or "").strip()
    if not raw.startswith("postgresql"):
        return None
    try:
        parsed = make_url(raw)
    except Exception:
        return None
    if not parsed.host:
        return None

    sslmode = (parsed.query or {}).get("sslmode", "require")
    user = quote_plus(parsed.username or "", safe="")
    password = quote_plus(parsed.password or "", safe="")
    port = parsed.port or 5432
    dbname = parsed.database or "postgres"
    return (
        f"postgresql://{user}:{password}@{parsed.host}:{port}/{dbname}"
        f"?sslmode={sslmode}"
    )
