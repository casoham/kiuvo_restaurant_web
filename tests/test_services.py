"""
Tests para validar los servicios principales.

Ejecutar: cd restaurant_app && python -m pytest tests/ -v
"""

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

# Asegurar que el root del proyecto está en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.database import Base
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(TEST_ENGINE, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestSessionLocal = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)

from src.models import *  # noqa: F401, F403
from src.services.auth_service import AuthService
from src.services.menu_service import MenuService
from src.services.cart_service import CartService
from src.services.order_service import OrderService
from src.services.promotion_service import PromotionService
from src.services.analytics_service import AnalyticsService
from src.services.password_reset_service import PasswordResetService
from src.models.user import User, UserRole
from src.models.menu_item import MenuCategory
from src.models.order import OrderStatus
from src.utils.exceptions import (
    AuthenticationError,
    DuplicateError,
    NotFoundError,
    BusinessLogicError,
    ValidationError,
)


@pytest.fixture(autouse=True)
def setup_db():
    """Crear tablas limpias antes de cada test."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def session():
    s = TestSessionLocal()
    yield s
    s.close()


# ── Auth ────────────────────────────────────────────────────

class TestAuthService:
    def test_register_and_login(self, session):
        auth = AuthService(session)
        user = auth.register(
            "test@test.com", "testuser", "Pass1234",
            student_id="Key_UNI001",
            major="Ingeniería Química",
        )
        assert user.username == "testuser"
        assert user.student_id == "Key_UNI001"

        logged = auth.login("testuser", "Pass1234")
        assert logged.id == user.id

    def test_register_with_birth_date(self, session):
        auth = AuthService(session)
        user = auth.register(
            "test@test.com", "testuser", "Pass1234",
            student_id="Key_UNI001",
            birth_date=date(2000, 5, 14),
            major="Ingeniería Química",
        )
        assert user.birth_date == date(2000, 5, 14)

    def test_register_duplicate_email(self, session):
        auth = AuthService(session)
        auth.register("dup@test.com", "user1", "Pass123", student_id="Key_UNI001", major="Ingeniería Química")
        with pytest.raises(DuplicateError):
            auth.register("dup@test.com", "user2", "Pass123", student_id="Key_UNI002", major="Ingeniería Química")

    def test_register_duplicate_student_id(self, session):
        """Verificar que no se permiten carnets duplicados."""
        auth = AuthService(session)
        auth.register("a@test.com", "user1", "Pass123", student_id="Key_SAME01", major="Ingeniería Química")
        with pytest.raises(DuplicateError):
            auth.register("b@test.com", "user2", "Pass123", student_id="Key_SAME01", major="Ingeniería Química")

    def test_register_empty_student_id(self, session):
        """Verificar que se requiere carnet no vacío."""
        auth = AuthService(session)
        with pytest.raises(ValidationError):
            auth.register("a@test.com", "user1", "Pass123", student_id="", major="Ingeniería Química")

    def test_register_whitespace_student_id(self, session):
        """Verificar que espacios en blanco no cuentan como carnet."""
        auth = AuthService(session)
        with pytest.raises(ValidationError):
            auth.register("a@test.com", "user1", "Pass123", student_id="   ", major="Ingeniería Química")

    def test_login_wrong_password(self, session):
        auth = AuthService(session)
        auth.register("t@t.com", "user1", "Pass123", student_id="Key_UNI001", major="Ingeniería Química")
        with pytest.raises(AuthenticationError):
            auth.login("user1", "wrongpass")


# ── Menu ────────────────────────────────────────────────────

class TestMenuService:
    def _create_admin(self, session):
        auth = AuthService(session)
        return auth.register(
            "a@a.com", "admin", "Pass123",
            student_id="Key_ADM001", role=UserRole.ADMIN,
        )

    def test_create_and_get(self, session):
        admin = self._create_admin(session)
        menu = MenuService(session)
        item = menu.create_item(admin, {
            "name": "Taco",
            "price": 5.0,
            "category": MenuCategory.MAIN_COURSE,
        })
        assert item.id is not None
        fetched = menu.get_by_id(item.id)
        assert fetched.name == "Taco"

    def test_toggle_availability(self, session):
        admin = self._create_admin(session)
        menu = MenuService(session)
        item = menu.create_item(admin, {
            "name": "Soda",
            "price": 2.0,
            "category": MenuCategory.BEVERAGE,
        })
        assert item.is_available is True
        toggled = menu.toggle_availability(admin, item.id)
        assert toggled.is_available is False

    def test_toggle_featured(self, session):
        """Verificar toggle de estado destacado."""
        admin = self._create_admin(session)
        menu = MenuService(session)
        item = menu.create_item(admin, {
            "name": "Nachos",
            "price": 8.0,
            "category": MenuCategory.APPETIZER,
            "is_featured": False,
        })
        assert item.is_featured is False
        toggled = menu.toggle_featured(admin, item.id)
        assert toggled.is_featured is True
        toggled2 = menu.toggle_featured(admin, item.id)
        assert toggled2.is_featured is False

    def test_get_featured(self, session):
        """Verificar que get_featured retorna solo items destacados."""
        admin = self._create_admin(session)
        menu = MenuService(session)
        menu.create_item(admin, {"name": "Regular", "price": 5.0, "category": MenuCategory.MAIN_COURSE, "is_featured": False})
        menu.create_item(admin, {"name": "Featured", "price": 10.0, "category": MenuCategory.MAIN_COURSE, "is_featured": True})
        featured = menu.get_featured()
        assert len(featured) == 1
        assert featured[0].name == "Featured"


# ── Promotions / Birthday ──────────────────────────────────

class TestPromotionService:
    def _create_user_with_birthday(self, session, birth_date):
        auth = AuthService(session)
        return auth.register(
            f"user_{birth_date}@test.com",
            f"user_{birth_date.isoformat()}",
            "Pass123",
            student_id="Key_BD0001",
            birth_date=birth_date,
            major="Ingeniería Química",
        )

    def test_is_birthday_today(self, session):
        """Verificar detección de cumpleaños hoy."""
        today = date.today()
        user = self._create_user_with_birthday(
            session, date(2000, today.month, today.day)
        )
        assert PromotionService.is_birthday(user) is True

    def test_is_not_birthday(self, session):
        """Verificar que no-cumpleaños retorna False."""
        tomorrow = date.today() + timedelta(days=1)
        user = self._create_user_with_birthday(
            session, date(2000, tomorrow.month, tomorrow.day)
        )
        assert PromotionService.is_birthday(user) is False

    def test_is_birthday_no_date(self, session):
        """Verificar que sin fecha de nacimiento retorna False."""
        auth = AuthService(session)
        user = auth.register(
            "no_bday@test.com", "nobday", "Pass123",
            student_id="Key_NOBD01", birth_date=None,
            major="Ingeniería Química",
        )
        assert PromotionService.is_birthday(user) is False

    def test_apply_birthday_discount(self, session):
        """Verificar aplicación de descuento por cumpleaños."""
        today = date.today()
        user = self._create_user_with_birthday(
            session, date(2000, today.month, today.day)
        )
        new_total, discount = PromotionService.apply_birthday_discount(user, 100.0)
        assert discount == 20.0  # 20% de 100
        assert new_total == 80.0

    def test_no_discount_when_not_birthday(self, session):
        """Verificar que no hay descuento cuando no es cumpleaños."""
        tomorrow = date.today() + timedelta(days=1)
        user = self._create_user_with_birthday(
            session, date(2000, tomorrow.month, tomorrow.day)
        )
        new_total, discount = PromotionService.apply_birthday_discount(user, 100.0)
        assert discount == 0.0
        assert new_total == 100.0

    def test_birthday_message(self, session):
        """Verificar generación de mensaje de cumpleaños."""
        today = date.today()
        user = self._create_user_with_birthday(
            session, date(2000, today.month, today.day)
        )
        msg = PromotionService.get_birthday_message(user)
        assert msg is not None
        assert "Feliz Cumpleaños" in msg
        assert user.username in msg

    def test_no_birthday_message_when_not_birthday(self, session):
        """Verificar que no hay mensaje cuando no es cumpleaños."""
        tomorrow = date.today() + timedelta(days=1)
        user = self._create_user_with_birthday(
            session, date(2000, tomorrow.month, tomorrow.day)
        )
        assert PromotionService.get_birthday_message(user) is None


# ── Cart & Order ────────────────────────────────────────────

class TestCartAndOrder:
    def _setup_user_and_menu(self, session):
        auth = AuthService(session)
        admin = auth.register(
            "a@a.com", "admin", "Pass123",
            student_id="Key_ADM001", role=UserRole.ADMIN,
        )
        user = auth.register(
            "u@u.com", "user1", "Pass123",
            student_id="Key_UNI001",
            major="Ingeniería Química",
        )
        menu = MenuService(session)
        item = menu.create_item(admin, {
            "name": "Burrito",
            "price": 10.0,
            "category": MenuCategory.MAIN_COURSE,
        })
        return user, admin, item

    def test_cart_add_and_total(self, session):
        user, _, item = self._setup_user_and_menu(session)
        cart = CartService(session)
        cart.add_item(user.id, item.id, 3)
        assert cart.get_total(user.id) == 30.0

    def test_create_order_from_cart(self, session):
        user, admin, item = self._setup_user_and_menu(session)
        cart = CartService(session)
        cart.add_item(user.id, item.id, 2)

        order_svc = OrderService(session)
        order = order_svc.create_from_cart(user)
        assert order.total_price == 20.0
        assert order.status == OrderStatus.PENDING
        assert cart.get_item_count(user.id) == 0

    def test_birthday_discount_on_order(self, session):
        """Verificar que el descuento de cumpleaños se aplica en la orden."""
        today = date.today()
        auth = AuthService(session)
        admin = auth.register(
            "a@a.com", "admin", "Pass123",
            student_id="Key_ADM001", role=UserRole.ADMIN,
        )
        birthday_user = auth.register(
            "bday@test.com", "bdayuser", "Pass123",
            student_id="Key_BDAY01",
            birth_date=date(2000, today.month, today.day),
            major="Ingeniería Química",
        )
        menu = MenuService(session)
        item = menu.create_item(admin, {
            "name": "Taco", "price": 10.0,
            "category": MenuCategory.MAIN_COURSE,
        })
        cart = CartService(session)
        cart.add_item(birthday_user.id, item.id, 5)  # 5 * 10 = 50

        order_svc = OrderService(session)
        order = order_svc.create_from_cart(birthday_user)
        # 50 - 20% = 40
        assert order.total_price == 40.0
        assert "cumpleanos" in (order.notes or "").lower()

    def test_empty_cart_raises(self, session):
        user, _, _ = self._setup_user_and_menu(session)
        order_svc = OrderService(session)
        with pytest.raises(BusinessLogicError):
            order_svc.create_from_cart(user)

    def test_order_status_transitions(self, session):
        user, admin, item = self._setup_user_and_menu(session)
        cart = CartService(session)
        cart.add_item(user.id, item.id, 1)
        order_svc = OrderService(session)
        order = order_svc.create_from_cart(user)

        order = order_svc.update_status(admin, order.id, OrderStatus.CONFIRMED)
        assert order.status == OrderStatus.CONFIRMED

        with pytest.raises(BusinessLogicError):
            order_svc.update_status(admin, order.id, OrderStatus.DELIVERED)


# ── Analytics / Rankings ────────────────────────────────────

class TestAnalyticsService:
    def _setup_with_orders(self, session):
        """Crear datos de prueba con órdenes completadas."""
        auth = AuthService(session)
        admin = auth.register(
            "a@a.com", "admin", "Pass123",
            student_id="Key_ADM001", role=UserRole.ADMIN,
        )
        user = auth.register(
            "u@u.com", "user1", "Pass123",
            student_id="Key_UNI001",
            major="Ingeniería Química",
        )
        menu = MenuService(session)
        taco = menu.create_item(admin, {"name": "Taco", "price": 10.0, "category": MenuCategory.MAIN_COURSE})
        burrito = menu.create_item(admin, {"name": "Burrito", "price": 15.0, "category": MenuCategory.MAIN_COURSE})
        soda = menu.create_item(admin, {"name": "Soda", "price": 3.0, "category": MenuCategory.BEVERAGE})

        cart_svc = CartService(session)
        order_svc = OrderService(session)

        # Orden 1: 5 tacos + 2 sodas
        cart_svc.add_item(user.id, taco.id, 5)
        cart_svc.add_item(user.id, soda.id, 2)
        o1 = order_svc.create_from_cart(user)
        order_svc.update_status(admin, o1.id, OrderStatus.CONFIRMED)
        order_svc.update_status(admin, o1.id, OrderStatus.PREPARING)
        order_svc.update_status(admin, o1.id, OrderStatus.READY)
        order_svc.update_status(admin, o1.id, OrderStatus.DELIVERED)

        # Orden 2: 3 burritos
        cart_svc.add_item(user.id, burrito.id, 3)
        o2 = order_svc.create_from_cart(user)
        order_svc.update_status(admin, o2.id, OrderStatus.CONFIRMED)
        order_svc.update_status(admin, o2.id, OrderStatus.PREPARING)
        order_svc.update_status(admin, o2.id, OrderStatus.READY)
        order_svc.update_status(admin, o2.id, OrderStatus.DELIVERED)

        return admin, user, taco, burrito, soda

    def test_most_popular_items(self, session):
        """Verificar ranking por cantidad vendida."""
        self._setup_with_orders(session)
        analytics = AnalyticsService(session)
        popular = analytics.get_most_popular_items(limit=5)

        assert len(popular) >= 2
        # Tacos (5 vendidos) deben ser el más popular
        assert popular[0]["name"] == "Taco"
        assert popular[0]["total_sold"] == 5

    def test_top_revenue_items(self, session):
        """Verificar ranking por ingresos."""
        self._setup_with_orders(session)
        analytics = AnalyticsService(session)
        revenue = analytics.get_top_revenue_items(limit=5)

        assert len(revenue) >= 2
        # Taco: 5*10=50, Burrito: 3*15=45 → Taco primero
        assert revenue[0]["name"] == "Taco"
        assert revenue[0]["total_revenue"] == 50.0

    def test_trending_items(self, session):
        """Verificar items trending (recientes)."""
        self._setup_with_orders(session)
        analytics = AnalyticsService(session)
        trending = analytics.get_trending_items(limit=5, days=7)

        # Todas las órdenes son recientes
        assert len(trending) >= 2

    def test_total_orders_count(self, session):
        """Verificar conteo total de órdenes."""
        self._setup_with_orders(session)
        analytics = AnalyticsService(session)
        count = analytics.get_total_orders_count()
        assert count == 2  # 2 órdenes no canceladas

    def test_total_revenue(self, session):
        """Verificar ingresos totales."""
        self._setup_with_orders(session)
        analytics = AnalyticsService(session)
        revenue = analytics.get_total_revenue()
        # Orden 1: 5*10 + 2*3 = 56, Orden 2: 3*15 = 45 → Total: 101
        assert revenue == 101.0

    def test_empty_rankings(self, session):
        """Verificar rankings vacíos cuando no hay órdenes."""
        analytics = AnalyticsService(session)
        assert analytics.get_most_popular_items() == []
        assert analytics.get_top_revenue_items() == []
        assert analytics.get_trending_items() == []
        assert analytics.get_total_orders_count() == 0
        assert analytics.get_total_revenue() == 0.0


# ── Registro bifurcado y Sparks ─────────────────────────────

class TestRegisterClientStaff:
    def test_register_client_institutional_email(self, session):
        auth = AuthService(session)
        user = auth.register_client(
            "maria.lopez@keyinstitute.edu.sv",
            "Client123",
            student_id="Key_CLI001",
            birth_date=date(2001, 3, 10),
            major="Ingeniería Mecatrónica y Robótica",
        )
        assert user.role == UserRole.USER
        assert user.username == "maria_lopez"
        assert user.email == "maria.lopez@keyinstitute.edu.sv"

    def test_register_client_invalid_email(self, session):
        auth = AuthService(session)
        with pytest.raises(ValidationError):
            auth.register_client(
                "invalid@gmail.com", "Client123", student_id="Key_CLI002",
                major="Ingeniería Mecatrónica y Robótica",
            )

    def test_register_staff(self, session):
        auth = AuthService(session)
        user = auth.register_staff("Carlos Ruiz", "Staff123", student_id="Key_STF002")
        assert user.role == UserRole.STAFF
        assert user.student_id == "Key_STF002"


class TestPasswordReset:
    def test_generate_and_verify_code(self):
        svc = PasswordResetService()
        email = "user@test.com"
        code = svc.generate_code(email)
        assert len(code) == 6
        assert code.isdigit()
        assert svc.verify_code(email, code) is True
        # Código de un solo uso
        assert svc.verify_code(email, code) is False

    def test_change_password_by_email(self, session):
        auth = AuthService(session)
        auth.register(
            "reset@test.com", "resetuser", "OldPass1",
            student_id="Key_RST001",
            major="Ingeniería Química",
        )
        auth.change_password_by_email("reset@test.com", "NewPass2")
        user = auth.login("resetuser", "NewPass2")
        assert user.email == "reset@test.com"


class TestSparksAndSlots:
    def test_sparks_on_delivered(self, session):
        auth = AuthService(session)
        admin = auth.register(
            "a@a.com", "admin", "Pass123",
            student_id="Key_ADM002", role=UserRole.ADMIN,
        )
        user = auth.register(
            "u@u.com", "user1", "Pass123", student_id="Key_USR002",
            major="Ingeniería Química",
        )
        menu = MenuService(session)
        item = menu.create_item(admin, {
            "name": "Pizza", "price": 12.50,
            "category": MenuCategory.MAIN_COURSE,
        })
        cart = CartService(session)
        cart.add_item(user.id, item.id, 2)
        order_svc = OrderService(session)
        order = order_svc.create_from_cart(user)
        assert user.sparks == 0

        for status in (
            OrderStatus.CONFIRMED,
            OrderStatus.PREPARING,
            OrderStatus.READY,
            OrderStatus.DELIVERED,
        ):
            order_svc.update_status(admin, order.id, status)

        session.refresh(user)
        expected_sparks = int(order.total_price) * 2
        assert user.sparks == expected_sparks

    def test_schedule_slots_capacity(self, session):
        from datetime import datetime, timezone, timedelta

        auth = AuthService(session)
        admin = auth.register(
            "a@a.com", "admin2", "Pass123",
            student_id="Key_ADM003", role=UserRole.ADMIN,
        )
        user = auth.register(
            "u@u.com", "user2", "Pass123", student_id="Key_USR003",
            major="Ingeniería Química",
        )
        menu = MenuService(session)
        item = menu.create_item(admin, {
            "name": "Snack", "price": 5.0,
            "category": MenuCategory.SIDE,
        })
        order_svc = OrderService(session)
        cart = CartService(session)

        slot = datetime.now(timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        for _ in range(order_svc.MAX_ORDERS_PER_SLOT):
            cart.add_item(user.id, item.id, 1)
            order_svc.create_from_cart(user, scheduled_time=slot)
            cart.clear_cart(user.id)

        cart.add_item(user.id, item.id, 1)
        with pytest.raises(BusinessLogicError):
            order_svc.create_from_cart(user, scheduled_time=slot)
