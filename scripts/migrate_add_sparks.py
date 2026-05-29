"""
Migración: Agregar campo sparks a la tabla users.

Este script agrega el campo de puntos de fidelidad (Sparks)
al modelo de usuario existente.

Uso:
    cd restaurant_app
    python scripts/migrate_add_sparks.py
"""

import sys
from pathlib import Path

# Asegurar que el root del proyecto esté en el path
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from sqlalchemy import text, inspect
from config.database import engine


def migrate():
    """Ejecutar migración para agregar sparks a users."""
    inspector = inspect(engine)

    # Verificar si la tabla 'users' existe
    if "users" not in inspector.get_table_names():
        print("La tabla 'users' no existe. Ejecuta init_db() primero.")
        return

    existing_columns = {col["name"] for col in inspector.get_columns("users")}

    with engine.begin() as conn:
        # ── Agregar sparks si no existe ──
        if "sparks" not in existing_columns:
            print("Agregando columna 'sparks' a users...")
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN sparks INTEGER NOT NULL DEFAULT 0"
            ))
            print("  Columna 'sparks' agregada (default: 0).")
        else:
            print("  Columna 'sparks' ya existe.")

    # Verificar resultado
    inspector = inspect(engine)
    final_columns = {col["name"] for col in inspector.get_columns("users")}
    assert "sparks" in final_columns, "Error: sparks no se creó"

    print("\nMigración completada exitosamente.")
    print(f"   Columnas actuales en 'users': {sorted(final_columns)}")


if __name__ == "__main__":
    migrate()
