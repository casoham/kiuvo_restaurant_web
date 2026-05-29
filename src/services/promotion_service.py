"""
Servicio de Promociones y Descuentos.

Detecta cumpleaños y aplica descuentos automáticos.
"""

from datetime import date

from src.models.user import User
from src.utils.logger import logger


# Porcentaje de descuento por cumpleaños
BIRTHDAY_DISCOUNT_PERCENT: float = 20.0


class PromotionService:
    """Servicio de promociones — stateless, no requiere sesión de BD."""

    @staticmethod
    def is_birthday(user: User) -> bool:
        """
        Verificar si hoy es el cumpleaños del usuario.

        Compara solo mes y día, ignorando el año.

        Args:
            user: Usuario a verificar.

        Returns:
            True si hoy es su cumpleaños, False si no tiene fecha o no es hoy.
        """
        if user.birth_date is None:
            return False

        today = date.today()
        return (
            user.birth_date.month == today.month
            and user.birth_date.day == today.day
        )

    @staticmethod
    def get_birthday_discount() -> float:
        """Retorna el porcentaje de descuento por cumpleaños."""
        return BIRTHDAY_DISCOUNT_PERCENT

    @classmethod
    def apply_birthday_discount(cls, user: User, total: float) -> tuple[float, float]:
        """
        Aplicar descuento de cumpleaños si corresponde.

        Args:
            user: Usuario.
            total: Monto total original.

        Returns:
            Tupla (nuevo_total, descuento_aplicado).
            Si no es cumpleaños, retorna (total, 0.0).
        """
        if not cls.is_birthday(user):
            return total, 0.0

        discount = round(total * BIRTHDAY_DISCOUNT_PERCENT / 100, 2)
        new_total = round(total - discount, 2)

        logger.info(
            f"Descuento de cumpleaños aplicado a {user.username}: "
            f"-${discount:.2f} ({BIRTHDAY_DISCOUNT_PERCENT}%)"
        )

        return new_total, discount

    @classmethod
    def get_birthday_message(cls, user: User) -> str | None:
        """
        Generar mensaje de felicitación de cumpleaños.

        Returns:
            Mensaje de felicitación o None si no es su cumpleaños.
        """
        if not cls.is_birthday(user):
            return None

        return (
            f"¡Feliz Cumpleaños, {user.username}!\n"
            f"Hoy tienes un {BIRTHDAY_DISCOUNT_PERCENT:.0f}% de descuento "
            f"en todos tus pedidos. ¡Disfrútalo!"
        )

    @classmethod
    def get_promotion_info(cls, user: User) -> dict:
        """
        Obtener información de promociones activas para un usuario.

        Returns:
            Dict con información de la promoción actual.
        """
        is_bday = cls.is_birthday(user)
        return {
            "is_birthday": is_bday,
            "discount_percent": BIRTHDAY_DISCOUNT_PERCENT if is_bday else 0.0,
            "message": cls.get_birthday_message(user) or "",
        }
