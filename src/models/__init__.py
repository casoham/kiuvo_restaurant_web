"""
Modelos de dominio — SQLAlchemy ORM.

Importar todos los modelos aquí para que Base.metadata los registre
al llamar init_db().
"""

from src.models.user import User, UserRole  # noqa: F401
from src.models.menu_item import MenuItem, MenuCategory  # noqa: F401
from src.models.order import Order, OrderItem, OrderStatus  # noqa: F401
from src.models.cart import Cart, CartItem  # noqa: F401
from src.models.reservation import Reservation, ReservationStatus  # noqa: F401
