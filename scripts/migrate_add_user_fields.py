"""
Migración: Agregar campos student_id y birth_date a la tabla users.

Este script agrega los nuevos campos requeridos para el sistema de
carnet universitario y descuento por cumpleaños.

Uso:
    cd restaurant_app
    python scripts/migrate_add_user_fields.py
"""

import sys
from pathlib import Path

# Asegurar que el root del proyecto esté en el path
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from sqlalchemy import text, inspect
from config.database import engine


def migrate():
    """Ejecutar migración para agregar student_id y birth_date a users."""
    inspector = inspect(engine)

    # Verificar si la tabla 'users' existe
    if "users" not in inspector.get_table_names():
        print("⚠️  La tabla 'users' no existe. Ejecuta init_db() primero.")
        return

    existing_columns = {col["name"] for col in inspector.get_columns("users")}

    with engine.begin() as conn:
        # ── Agregar student_id si no existe ──
        if "student_id" not in existing_columns:
            print("➕ Agregando columna 'student_id' a users...")
            # Primero agregar como nullable para manejar datos existentes
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN student_id VARCHAR(50)"
            ))
            # Actualizar registros existentes con un valor por defecto único
            conn.execute(text(
                "UPDATE users SET student_id = 'LEGACY-' || CAST(id AS TEXT) "
                "WHERE student_id IS NULL"
            ))
            print("  ✅ Columna 'student_id' agregada y datos existentes actualizados.")
        else:
            print("  ℹ️  Columna 'student_id' ya existe.")

        # ── Agregar birth_date si no existe ──
        if "birth_date" not in existing_columns:
            print("➕ Agregando columna 'birth_date' a users...")
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN birth_date DATE"
            ))
            print("  ✅ Columna 'birth_date' agregada (nullable).")
        else:
            print("  ℹ️  Columna 'birth_date' ya existe.")

    # Verificar resultado
    inspector = inspect(engine)
    final_columns = {col["name"] for col in inspector.get_columns("users")}
    assert "student_id" in final_columns, "Error: student_id no se creó"
    assert "birth_date" in final_columns, "Error: birth_date no se creó"

    print("\n✅ Migración completada exitosamente.")
    print(f"   Columnas actuales en 'users': {sorted(final_columns)}")


if __name__ == "__main__":
    migrate()
