"""
Modelo de Item del Menú (plato / producto).
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import String, Float, Boolean, Enum, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from config.database import Base


class MenuCategory(str, enum.Enum):
    """Categorías del menú."""

    APPETIZER = "appetizer"       # Entrada
    MAIN_COURSE = "main_course"   # Plato fuerte
    DESSERT = "dessert"           # Postre
    BEVERAGE = "beverage"         # Bebida
    SIDE = "side"                 # Acompañamiento
    SPECIAL = "special"           # Especial del día


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[MenuCategory] = mapped_column(
        Enum(
            MenuCategory,
            name="menu_category",
            values_callable=lambda e: [i.value for i in e],
            create_type=False,
        ),
        nullable=False,
        index=True,
    )

    # URL o ruta local de imagen — preparado para cloud storage
    # TODO: Cloud storage integration — guardar en S3/GCS en lugar de ruta local
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_new: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # TODO: Sistema de promociones y descuentos
    # discount_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    # promo_start: Mapped[datetime | None] = ...
    # promo_end: Mapped[datetime | None] = ...

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MenuItem(id={self.id}, name={self.name!r}, ${self.price:.2f})>"
