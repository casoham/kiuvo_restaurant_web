"""
Servicio de Órdenes / Pedidos.

Gestión completa del ciclo de vida de una orden:
crear desde carrito, cambiar estados, consultar historial.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.models.order import Order, OrderItem, OrderStatus
from src.models.user import User, UserRole
from src.repositories.order_repository import OrderRepository
from src.repositories.user_repository import UserRepository
from src.services.cart_service import CartService
from src.services.promotion_service import PromotionService
from src.utils.logger import logger
from src.utils.exceptions import (
    NotFoundError,
    AuthorizationError,
    BusinessLogicError,
    ValidationError,
)


# Transiciones de estado válidas
_VALID_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.READY, OrderStatus.CANCELLED],
    OrderStatus.READY: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
}


class OrderService:
    """Servicio de órdenes — dependency injection vía constructor."""

    def __init__(self, session: Session) -> None:
        self._repo = OrderRepository(session)
        self._cart_service = CartService(session)
        self._user_repo = UserRepository(session)
        self._session = session

    # ── Lectura ─────────────────────────────────────────────
    def get_by_id(self, order_id: int) -> Order:
        """Obtener orden por ID (con items)."""
        order = self._repo.get_with_items(order_id)
        if order is None:
            raise NotFoundError("Orden", order_id)
        return order

    def get_user_orders(self, user_id: int) -> list[Order]:
        """Obtener todas las órdenes de un usuario."""
        return self._repo.get_by_user(user_id)

    def get_by_status(self, status: OrderStatus) -> list[Order]:
        """Obtener órdenes por estado (para staff/admin)."""
        return self._repo.get_by_status(status)

    def get_active_orders(self) -> list[Order]:
        """Obtener órdenes activas (no entregadas ni canceladas)."""
        return self._repo.get_active_orders()

    def get_all_orders(self, *, skip: int = 0, limit: int = 100) -> list[Order]:
        """Listar todas las órdenes (admin/staff)."""
        return self._repo.get_all(skip=skip, limit=limit)

    # ── Slots de programación ───────────────────────────────
    # Máximo de pedidos permitidos por franja horaria
    MAX_ORDERS_PER_SLOT = 15

    # Horario de operación
    OPENING_HOUR = 6   # 6:00 AM
    CLOSING_HOUR = 17  # 5:00 PM

    def get_schedule_slots(
        self,
        base_date: datetime,
        hours_ahead: int = 8,
        slot_minutes: int = 15,
    ) -> list[dict]:
        """
        Devuelve los slots horarios disponibles a partir de base_date.

        Cada slot indica la hora, cuántos pedidos ya existen y si hay cupo.

        Args:
            base_date: Momento desde el que se generan los slots (normalmente 'ahora').
            hours_ahead: Cuántas horas hacia adelante mostrar.
            slot_minutes: Duración de cada franja en minutos.

        Returns:
            Lista de dicts con keys: start, label, count, available, full.
        """
        # Convertir base_date a la hora local de El Salvador (UTC-6)
        from datetime import timezone, timedelta
        if base_date.tzinfo is not None:
            local_base = base_date.astimezone(timezone(timedelta(hours=-6)))
        else:
            local_base = base_date - timedelta(hours=6)

        # Si la hora local actual está fuera del horario de operación o después del cierre:
        # Ajustamos local_base al inicio del período operacional válido
        if local_base.hour >= self.CLOSING_HOUR:
            # Siguiente día a las 6:00 AM
            tomorrow = local_base + timedelta(days=1)
            local_base = tomorrow.replace(hour=self.OPENING_HOUR, minute=0, second=0, microsecond=0)
        elif local_base.hour < self.OPENING_HOUR:
            # Mismo día a las 6:00 AM
            local_base = local_base.replace(hour=self.OPENING_HOUR, minute=0, second=0, microsecond=0)

        # Redondear local_base al próximo slot
        minutes = (local_base.minute // slot_minutes + 1) * slot_minutes
        start_local = local_base.replace(second=0, microsecond=0) + timedelta(
            minutes=minutes - local_base.minute
        )
        end_local = start_local + timedelta(hours=hours_ahead)

        # Convertir a UTC para realizar la consulta en la base de datos (que almacena en UTC/naive)
        start_utc = start_local + timedelta(hours=6)
        end_utc = end_local + timedelta(hours=6)

        load = self._repo.get_scheduled_slots_load(start_utc, end_utc, slot_minutes)

        slots = []
        for slot_start_utc, count in load.items():
            # Convertir a local para mostrar la etiqueta y filtrar por horario de operación
            slot_start_local = slot_start_utc - timedelta(hours=6)
            if self.OPENING_HOUR <= slot_start_local.hour < self.CLOSING_HOUR:
                remaining = max(0, self.MAX_ORDERS_PER_SLOT - count)
                slots.append(
                    {
                        "start": slot_start_utc,  # Se envía en UTC para compatibilidad de guardado
                        "label": slot_start_local.strftime("%H:%M"),  # Se muestra la hora local al alumno
                        "count": count,
                        "remaining": remaining,
                        "full": remaining == 0,
                    }
                )
        return slots

    # ── Creación ────────────────────────────────────────────
    def create_from_cart(
        self,
        user: User,
        notes: str | None = None,
        scheduled_time: datetime | None = None,
    ) -> Order:
        """
        Crear una orden a partir del carrito del usuario.

        Args:
            user: Usuario que realiza el pedido.
            notes: Notas adicionales.
            scheduled_time: Hora programada (para pedidos diferidos).

        Returns:
            La orden creada.

        Raises:
            BusinessLogicError: Si el carrito está vacío.
        """
        cart_summary = self._cart_service.get_cart_summary(user.id)
        if not cart_summary:
            raise BusinessLogicError("El carrito está vacío")

        # Validar horario de operación si el pedido es programado
        if scheduled_time is not None:
            # Convertir a la hora local de El Salvador (UTC-6)
            from datetime import timezone, timedelta
            if scheduled_time.tzinfo is not None:
                local_scheduled = scheduled_time.astimezone(timezone(timedelta(hours=-6)))
            else:
                local_scheduled = scheduled_time - timedelta(hours=6)

            hour = local_scheduled.hour
            if hour < self.OPENING_HOUR or hour >= self.CLOSING_HOUR:
                raise ValidationError(
                    f"El horario de operacion es de {self.OPENING_HOUR}:00 a "
                    f"{self.CLOSING_HOUR}:00. No se pueden programar pedidos fuera "
                    "de este rango."
                )

        # Validar cupo del slot si el pedido es programado
        if scheduled_time is not None:
            slot_end = scheduled_time + timedelta(minutes=15)
            count = self._repo.count_scheduled_in_range(scheduled_time, slot_end)
            if count >= self.MAX_ORDERS_PER_SLOT:
                raise BusinessLogicError(
                    f"El horario {scheduled_time.strftime('%H:%M')} ya esta lleno "
                    f"({self.MAX_ORDERS_PER_SLOT}/{self.MAX_ORDERS_PER_SLOT} pedidos). "
                    "Por favor elige otro horario."
                )

        subtotal = self._cart_service.get_total(user.id)

        # Aplicar descuento de cumpleaños si corresponde
        total, birthday_discount = PromotionService.apply_birthday_discount(
            user, subtotal
        )

        # Construir notas con info de descuento
        final_notes = notes or ""
        if birthday_discount > 0:
            discount_note = (
                f"Descuento cumpleanos ({PromotionService.get_birthday_discount():.0f}%): "
                f"-${birthday_discount:.2f}"
            )
            final_notes = f"{final_notes}\n{discount_note}".strip() if final_notes else discount_note

        # Crear la orden
        order = Order(
            user_id=user.id,
            total_price=total,
            status=OrderStatus.PENDING,
            notes=final_notes or None,
            scheduled_time=scheduled_time,
        )
        self._session.add(order)
        self._session.flush()  # Para obtener order.id

        # Crear líneas de detalle (snapshot de precios al momento del pedido)
        for item_data in cart_summary:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item_data["menu_item_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["price"],
                item_name=item_data["name"],
            )
            self._session.add(order_item)

        self._session.commit()
        self._session.refresh(order)

        # Vaciar el carrito después de crear la orden
        self._cart_service.clear_cart(user.id)

        logger.info(
            f"Orden #{order.id} creada por {user.username} - "
            f"Subtotal: ${subtotal:.2f}, Descuento: ${birthday_discount:.2f}, "
            f"Total: ${total:.2f}, Items: {len(cart_summary)}"
        )

        # TODO: Sistema de pagos — procesar pago aquí
        # payment_result = payment_service.charge(user, total)
        # if not payment_result.success:
        #     raise BusinessLogicError("Error al procesar el pago")

        return order

    # ── Cambio de estado ────────────────────────────────────
    def update_status(
        self, user: User, order_id: int, new_status: OrderStatus
    ) -> Order:
        """
        Cambiar el estado de una orden.

        Solo ADMIN/STAFF pueden cambiar estados (excepto cancelar,
        que también puede el usuario dueño si está pendiente).
        """
        order = self.get_by_id(order_id)

        # Verificar permisos
        is_manager = user.role in {UserRole.ADMIN, UserRole.STAFF}
        is_owner = order.user_id == user.id

        if new_status == OrderStatus.CANCELLED:
            # El usuario puede cancelar su propia orden si está pendiente
            if not is_manager and not (
                is_owner and order.status == OrderStatus.PENDING
            ):
                raise AuthorizationError(
                    "Solo puedes cancelar tus propias ordenes pendientes"
                )
        elif not is_manager:
            raise AuthorizationError(
                "Solo ADMIN o STAFF pueden cambiar el estado de las ordenes"
            )

        # Validar transición
        valid_next = _VALID_TRANSITIONS.get(order.status, [])
        if new_status not in valid_next:
            raise BusinessLogicError(
                f"No se puede cambiar de '{order.status.value}' a '{new_status.value}'. "
                f"Transiciones validas: {[s.value for s in valid_next]}"
            )

        updated = self._repo.update_status(order, new_status)
        logger.info(
            f"Orden #{order.id}: {order.status.value} -> {new_status.value} "
            f"(por: {user.username})"
        )

        # ── Sparks: otorgar puntos cuando la orden es entregada ──
        if new_status == OrderStatus.DELIVERED:
            sparks_earned = int(order.total_price) * 2
            order_user = self._user_repo.get(order.user_id)
            if order_user is not None:
                new_sparks = order_user.sparks + sparks_earned
                self._user_repo.update(order_user, {"sparks": new_sparks})
                logger.info(
                    f"Sparks otorgados a {order_user.username}: "
                    f"+{sparks_earned} (total: {new_sparks})"
                )

        return updated

    # ── Cancelación ─────────────────────────────────────────
    def cancel_order(self, user: User, order_id: int) -> Order:
        """Atajo para cancelar una orden."""
        return self.update_status(user, order_id, OrderStatus.CANCELLED)
