"""
Servicio de Analytics / Rankings.

Proporciona estadísticas de productos más vendidos, mejor calificados
y tendencias recientes.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from src.models.order import Order, OrderItem, OrderStatus
from src.models.menu_item import MenuItem
from src.utils.logger import logger


class AnalyticsService:
    """Servicio de analytics — dependency injection vía constructor."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_most_popular_items(self, limit: int = 10) -> list[dict]:
        """
        Obtener productos más vendidos por cantidad total de unidades.

        Solo cuenta órdenes no canceladas.

        Args:
            limit: Cantidad máxima de resultados.

        Returns:
            Lista de dicts con menu_item_id, name, category, total_sold, price.
        """
        results = (
            self._session.query(
                OrderItem.menu_item_id,
                MenuItem.name,
                MenuItem.category,
                MenuItem.price,
                func.sum(OrderItem.quantity).label("total_sold"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
            .filter(Order.status != OrderStatus.CANCELLED)
            .group_by(
                OrderItem.menu_item_id,
                MenuItem.name,
                MenuItem.category,
                MenuItem.price,
            )
            .order_by(desc("total_sold"))
            .limit(limit)
            .all()
        )

        items = [
            {
                "menu_item_id": r.menu_item_id,
                "name": r.name,
                "category": r.category.value if hasattr(r.category, "value") else str(r.category),
                "total_sold": int(r.total_sold),
                "price": float(r.price),
            }
            for r in results
        ]

        logger.debug(f"Rankings — Productos más populares: {len(items)} resultados")
        return items

    def get_top_rated_items(self, limit: int = 10) -> list[dict]:
        """
        Obtener productos mejor calificados.

        NOTA: Este método está preparado para cuando exista un sistema
        de reviews/calificaciones. Actualmente retorna los más vendidos
        como proxy.

        Args:
            limit: Cantidad máxima de resultados.

        Returns:
            Lista de dicts con datos de los items.
        """
        # TODO: Implementar cuando exista modelo de Review con rating
        # Por ahora, usar popularidad como proxy de calificación
        logger.debug("Rankings — Top rated (proxy: most popular)")
        return self.get_most_popular_items(limit=limit)

    def get_trending_items(self, limit: int = 10, days: int = 7) -> list[dict]:
        """
        Obtener items con más ventas en los últimos N días (tendencias).

        Args:
            limit: Cantidad máxima de resultados.
            days: Ventana de tiempo en días (default: 7).

        Returns:
            Lista de dicts con datos de los items trending.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        results = (
            self._session.query(
                OrderItem.menu_item_id,
                MenuItem.name,
                MenuItem.category,
                MenuItem.price,
                func.sum(OrderItem.quantity).label("total_sold"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
            .filter(
                Order.status != OrderStatus.CANCELLED,
                Order.created_at >= cutoff,
            )
            .group_by(
                OrderItem.menu_item_id,
                MenuItem.name,
                MenuItem.category,
                MenuItem.price,
            )
            .order_by(desc("total_sold"))
            .limit(limit)
            .all()
        )

        items = [
            {
                "menu_item_id": r.menu_item_id,
                "name": r.name,
                "category": r.category.value if hasattr(r.category, "value") else str(r.category),
                "total_sold": int(r.total_sold),
                "price": float(r.price),
            }
            for r in results
        ]

        logger.debug(
            f"Rankings — Trending (últimos {days} días): {len(items)} resultados"
        )
        return items

    def get_top_revenue_items(self, limit: int = 10) -> list[dict]:
        """
        Obtener items que generan más ingresos (precio × cantidad vendida).

        Solo cuenta órdenes no canceladas.

        Args:
            limit: Cantidad máxima de resultados.

        Returns:
            Lista de dicts con menu_item_id, name, category, total_sold, price, total_revenue.
        """
        results = (
            self._session.query(
                OrderItem.menu_item_id,
                MenuItem.name,
                MenuItem.category,
                MenuItem.price,
                func.sum(OrderItem.quantity).label("total_sold"),
                func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_revenue"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
            .filter(Order.status != OrderStatus.CANCELLED)
            .group_by(
                OrderItem.menu_item_id,
                MenuItem.name,
                MenuItem.category,
                MenuItem.price,
            )
            .order_by(desc("total_revenue"))
            .limit(limit)
            .all()
        )

        items = [
            {
                "menu_item_id": r.menu_item_id,
                "name": r.name,
                "category": r.category.value if hasattr(r.category, "value") else str(r.category),
                "total_sold": int(r.total_sold),
                "price": float(r.price),
                "total_revenue": float(r.total_revenue),
            }
            for r in results
        ]

        logger.debug(f"Rankings — Top revenue: {len(items)} resultados")
        return items

    def get_total_orders_count(self) -> int:
        """Obtener el total de órdenes (no canceladas)."""
        return (
            self._session.query(func.count(Order.id))
            .filter(Order.status != OrderStatus.CANCELLED)
            .scalar()
            or 0
        )

    def get_total_revenue(self) -> float:
        """Obtener ingresos totales (de órdenes entregadas)."""
        result = (
            self._session.query(func.sum(Order.total_price))
            .filter(Order.status == OrderStatus.DELIVERED)
            .scalar()
        )
        return float(result) if result else 0.0
