"""
Aplicación FastAPI principal.

Configura middleware, exception handlers y registra todos los routers.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config.settings import settings
from config.database import init_db
from src.utils.exceptions import AppError
from api.exception_handlers import app_error_handler, sqlalchemy_error_handler
from sqlalchemy.exc import DBAPIError
from api.routers import auth, users, menu, cart, orders, analytics


def create_app() -> FastAPI:
    """Factory de la aplicación FastAPI."""

    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        description=(
            "API REST del sistema de restaurante universitario DO Eat.\n\n"
            "## Funcionalidades\n"
            "- **Autenticación** JWT con access + refresh tokens\n"
            "- **Gestión de usuarios** con roles (admin, staff, user)\n"
            "- **Menú** con categorías, destacados y búsqueda\n"
            "- **Carrito** de compras por usuario\n"
            "- **Órdenes** con flujo de estados y descuento de cumpleaños\n"
            "- **Analytics** — rankings de productos y estadísticas\n"
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── CORS ────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ──────────────────────────────────
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(DBAPIError, sqlalchemy_error_handler)

    # ── Routers (prefijo /api/v1) ───────────────────────────
    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(menu.router, prefix=api_prefix)
    app.include_router(cart.router, prefix=api_prefix)
    app.include_router(orders.router, prefix=api_prefix)
    app.include_router(analytics.router, prefix=api_prefix)

    # ── Eventos de inicio ───────────────────────────────────
    @app.on_event("startup")
    def on_startup():
        """Inicializar BD al arrancar."""
        init_db()

    # ── Health check ────────────────────────────────────────
    @app.get("/health", tags=["Sistema"])
    def health_check():
        from src.integrations.supabase_client import check_supabase_connection

        supabase_status = check_supabase_connection()
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "database": "postgresql" if settings.uses_supabase_db else "sqlite",
            "supabase": supabase_status,
        }

    _setup_static_frontend(app)

    return app


def _setup_static_frontend(app: FastAPI) -> None:
    """
    Sirve el frontend solo si existe un build de Vite (frontend/dist).

    Evita montar carpetas inexistentes (p. ej. frontend/assets sin build),
    que provocan RuntimeError y impiden arrancar uvicorn.
    """
    backend_root = Path(__file__).resolve().parent.parent
    frontend_dir = backend_root / "frontend"
    dist_dir = frontend_dir / "dist"
    project_images_dir = backend_root / "imagenes proyecto"
    frontend_images_dir = frontend_dir / "imagenes proyecto"
    images_mount = frontend_images_dir if frontend_images_dir.is_dir() else project_images_dir

    if images_mount.is_dir():
        app.mount(
            "/imagenes-proyecto",
            StaticFiles(directory=str(images_mount)),
            name="imagenes-proyecto",
        )

    dist_index = dist_dir / "index.html"
    if not dist_index.is_file():
        @app.get("/", include_in_schema=False)
        def root_api_only():
            return {
                "message": f"{settings.APP_NAME} API en ejecución",
                "docs": "/docs",
                "health": "/health",
                "frontend_dev": "En frontend/: npm run dev → http://127.0.0.1:5173",
                "frontend_prod": "En frontend/: npm run build y reinicia la API",
            }

        return

    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="spa-assets",
        )

    public_dir = frontend_dir / "public"
    if public_dir.is_dir():
        app.mount(
            "/public",
            StaticFiles(directory=str(public_dir)),
            name="spa-public",
        )

    @app.get("/", include_in_schema=False)
    def root_frontend():
        return FileResponse(dist_index)

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        """Rutas del SPA (React Router)."""
        if full_path.startswith("api/"):
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not Found")
        file_path = dist_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_index)


# Instancia usada por uvicorn: `uvicorn api.main:app`
app = create_app()
