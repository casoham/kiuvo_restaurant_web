#!/usr/bin/env python3
"""
Script de inicio de la API REST.

Uso:
    python run_api.py              # modo desarrollo (reload)
    python run_api.py --prod       # modo producción
    python run_api.py --port 8080  # puerto custom
"""

import argparse
import uvicorn

from config.settings import settings


def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="🍽️ Do Eat — API REST")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto (default: 8000)")
    parser.add_argument("--prod", action="store_true", help="Modo producción (sin reload)")
    args = parser.parse_args()

    reload_mode = not args.prod and settings.is_development

    print(f"\n🍽️  {settings.APP_NAME} API v{settings.APP_VERSION}")
    print(f"   Entorno: {settings.APP_ENV}")
    print(f"   URL: http://{args.host}:{args.port}")
    print(f"   Docs: http://{args.host}:{args.port}/docs")
    print(f"   Reload: {'✅' if reload_mode else '❌'}\n")

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=reload_mode,
        log_level="info",
    )


if __name__ == "__main__":
    main()
