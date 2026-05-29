"""
Configuración de base de datos con SQLAlchemy.

Soporta SQLite (desarrollo) y PostgreSQL/Supabase (producción)
cambiando solo DATABASE_URL en .env.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config.settings import settings


def _build_engine():
    """Crea el engine; usa kwargs explícitos en Supabase pooler."""
    connect_args: dict = {}
    engine_kwargs: dict = {}
    db_url = settings.DATABASE_URL

    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(
            db_url,
            connect_args=connect_args,
            echo=settings.is_development and settings.APP_DEBUG,
        )

    if db_url.startswith("postgresql"):
        engine_kwargs.update(
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        pooler_dsn = settings.database_dsn_for_psycopg2
        if "pooler.supabase.com" in pooler_dsn:
            import psycopg2

            def _creator():
                return psycopg2.connect(pooler_dsn)

            return create_engine(
                "postgresql+psycopg2://",
                creator=_creator,
                echo=settings.is_development and settings.APP_DEBUG,
                **engine_kwargs,
            )

        return create_engine(
            make_url(db_url),
            connect_args=connect_args,
            echo=settings.is_development and settings.APP_DEBUG,
            **engine_kwargs,
        )

    return create_engine(
        db_url,
        connect_args=connect_args,
        echo=settings.is_development and settings.APP_DEBUG,
    )


engine = _build_engine()

# Activar foreign keys en SQLite (deshabilitadas por defecto)
if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ── Session ─────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Base declarativa ────────────────────────────────────────
class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""

    pass


# ── Helpers ─────────────────────────────────────────────────
def get_session():
    """Genera una sesión de BD."""
    return SessionLocal()


def init_db():
    """Crea todas las tablas definidas en los modelos."""
    import src.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
