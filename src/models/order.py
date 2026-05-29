"""
Modelo de Orden/Pedido y sus items.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    String, Float, Integer, ForeignKey, Enum, Text, DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class OrderStatus(str, enum.Enum):
    """Estados posibles de una orden."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            name="order_status",
            values_callable=lambda e: [i.value for i in e],
            create_type=False,
        ),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Hora programada (para pedidos diferidos / reservas)
    scheduled_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # TODO: Sistema de pagos — placeholder
    # payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # payment_status: Mapped[str] = mapped_column(String(50), default="pending")
    # transaction_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

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

    # ── Relaciones ──────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="orders")  # noqa: F821
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Order(id={self.id}, user_id={self.user_id}, "
            f"status={self.status.value}, total=${self.total_price:.2f})>"
        )


class OrderItem(Base):
    """Línea de detalle de una orden (many-to-many entre Order y MenuItem)."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    item_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )  # snapshot del nombre al momento del pedido

    # ── Relaciones ──────────────────────────────────────────
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship("MenuItem")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<OrderItem(id={self.id}, item={self.item_name!r}, "
            f"qty={self.quantity}, ${self.unit_price:.2f})>"
        )
