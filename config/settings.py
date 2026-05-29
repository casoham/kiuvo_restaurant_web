"""
Configuración centralizada de la aplicación.

Carga variables de entorno desde .env y provee acceso tipado
a toda la configuración del sistema.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from config.db_url import normalize_database_url

# ── Rutas base ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

# Cargar .env si existe, sobreescribiendo variables cacheadas
load_dotenv(dotenv_path=ENV_FILE, override=True)


class Settings:
    """Configuración centralizada — singleton de facto."""

    # ── Aplicación ──────────────────────────────────────────
    APP_NAME: str = os.getenv("APP_NAME", "DO Eat")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "true").lower() == "true"
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")

    # ── Base de datos ───────────────────────────────────────
    # SQLite (desarrollo) o PostgreSQL Supabase (producción)
    _RAW_DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'restaurant.db'}",
    ).strip()
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
    DATABASE_URL: str = normalize_database_url(
        _RAW_DATABASE_URL,
        SUPABASE_URL,
    )

    @property
    def database_dsn_for_psycopg2(self) -> str:
        """URI cruda del .env (mejor compatibilidad con psycopg2 en Windows)."""
        if self._RAW_DATABASE_URL.startswith("postgresql"):
            return self._RAW_DATABASE_URL
        return self.DATABASE_URL

    # ── Supabase ────────────────────────────────────────────
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "").strip()
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY", ""
    ).strip()

    # ── Seguridad ───────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

    # ── JWT ────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

    # ── SMTP (recuperación de contraseña) ───────────────────
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", SMTP_USER)

    # ── CORS ────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
    ]

    # ── Logging ─────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    LOG_FILE: str = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "restaurant.log"))

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def uses_supabase_db(self) -> bool:
        url = self.DATABASE_URL.lower()
        return url.startswith("postgresql") or "supabase" in url

    @property
    def supabase_configured(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_ROLE_KEY)

    def __repr__(self) -> str:
        return (
            f"Settings(app={self.APP_NAME!r}, env={self.APP_ENV!r}, "
            f"db={self.DATABASE_URL[:40]!r}...)"
        )


# Instancia global
settings = Settings()
