"""
Repositorio de Órdenes.
"""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.models.order import Order, OrderStatus
from src.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):

    def __init__(self, session: Session) -> None:
        super().__init__(Order, session)

    def get_with_items(self, order_id: int) -> Order | None:
        """Obtener orden con sus items cargados (eager)."""
        return (
            self._session.query(Order)
            .options(joinedload(Order.items))
            .filter(Order.id == order_id)
            .first()
        )

    def get_by_user(self, user_id: int) -> list[Order]:
        """Obtener órdenes de un usuario específico."""
        return (
            self._session.query(Order)
            .filter(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_by_status(self, status: OrderStatus) -> list[Order]:
        """Obtener órdenes por estado."""
        return (
            self._session.query(Order)
            .filter(Order.status == status)
            .order_by(Order.created_at.asc())
            .all()
        )

    def get_active_orders(self) -> list[Order]:
        """Obtener órdenes activas (no entregadas ni canceladas)."""
        return (
            self._session.query(Order)
            .filter(
                Order.status.notin_([OrderStatus.DELIVERED, OrderStatus.CANCELLED])
            )
            .order_by(Order.created_at.asc())
            .all()
        )

    def update_status(self, order: Order, new_status: OrderStatus) -> Order:
        """Actualizar estado de una orden."""
        return self.update(order, {"status": new_status})

    def count_scheduled_in_range(
        self, start: datetime, end: datetime
    ) -> int:
        """Contar órdenes programadas (no canceladas) en un rango de tiempo."""
        return (
            self._session.query(func.count(Order.id))
            .filter(
                Order.scheduled_time >= start,
                Order.scheduled_time < end,
                Order.status != OrderStatus.CANCELLED,
            )
            .scalar()
            or 0
        )

    def get_scheduled_slots_load(
        self,
        date_start: datetime,
        date_end: datetime,
        slot_minutes: int = 30,
    ) -> dict[datetime, int]:
        """
        Devuelve un dict {slot_inicio: cantidad_pedidos} para cada franja
        de `slot_minutes` minutos entre date_start y date_end.
        """
        load: dict[datetime, int] = {}
        current = date_start
        while current < date_end:
            next_slot = current + timedelta(minutes=slot_minutes)
            load[current] = self.count_scheduled_in_range(current, next_slot)
            current = next_slot
        return load

