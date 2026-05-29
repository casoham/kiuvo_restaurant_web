"""
Tests de la API REST — FastAPI TestClient.

Cubre: auth, users, menu, cart, orders, analytics.
Usa BD SQLite en memoria con StaticPool (misma conexión para todos).
"""

import pytest
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from config.database import Base
from api.dependencies import get_db

# ── Setup de BD en memoria (StaticPool = misma conexión) ────

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


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Fixtures ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """TestClient con BD de test aislada."""
    import src.models  # noqa: F401 — registrar modelos con Base
    Base.metadata.create_all(bind=TEST_ENGINE)

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from src.utils.exceptions import AppError
    from api.exception_handlers import app_error_handler
    from api.routers import auth, users, menu, cart, orders, analytics

    app = FastAPI(title="Test API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, app_error_handler)

    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(menu.router, prefix=api_prefix)
    app.include_router(cart.router, prefix=api_prefix)
    app.include_router(orders.router, prefix=api_prefix)
    app.include_router(analytics.router, prefix=api_prefix)

    @app.get("/health", tags=["Sistema"])
    def health_check():
        return {"status": "ok"}

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture(scope="module")
def admin_token(client):
    """Registrar admin y obtener token."""
    resp = client.post("/api/v1/auth/register", json={
        "email": "admin@test.com",
        "username": "admin_test",
        "password": "Admin123",
        "student_id": "Key_ADM001",
        "role": "admin",
    })
    assert resp.status_code == 201, f"Admin register failed: {resp.text}"

    resp = client.post("/api/v1/auth/login", data={
        "username": "admin_test",
        "password": "Admin123",
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def staff_token(client):
    """Registrar staff y obtener token."""
    client.post("/api/v1/auth/register", json={
        "email": "staff@test.com",
        "username": "staff_test",
        "password": "Staff123",
        "student_id": "Key_STF001",
        "role": "staff",
    })
    resp = client.post("/api/v1/auth/login", data={
        "username": "staff_test",
        "password": "Staff123",
    })
    assert resp.status_code == 200, f"Staff login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def user_token(client):
    """Registrar usuario normal y obtener token."""
    client.post("/api/v1/auth/register", json={
        "email": "usuario.test@keyinstitute.edu.sv",
        "username": "user_test",
        "password": "User1234",
        "student_id": "Key_USR001",
        "birth_date": "2000-06-15",
        "major": "Ingeniería Química",
    })
    resp = client.post("/api/v1/auth/login", data={
        "username": "user_test",
        "password": "User1234",
    })
    assert resp.status_code == 200, f"User login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def birthday_user_token(client):
    """Registrar usuario con cumpleaños hoy y obtener token."""
    today = date.today().isoformat()
    client.post("/api/v1/auth/register", json={
        "email": "cumple.test@keyinstitute.edu.sv",
        "username": "birthday_user",
        "password": "Bday1234",
        "student_id": "Key_BDAY01",
        "birth_date": today,
        "major": "Ingeniería Química",
    })
    resp = client.post("/api/v1/auth/login", data={
        "username": "birthday_user",
        "password": "Bday1234",
    })
    assert resp.status_code == 200, f"Birthday user login failed: {resp.text}"
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ════════════════════════════════════════════════════════════
#  TESTS — HEALTH
# ════════════════════════════════════════════════════════════

class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ════════════════════════════════════════════════════════════
#  TESTS — AUTH
# ════════════════════════════════════════════════════════════

class TestAuth:
    def test_register(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "nuevo.usuario@keyinstitute.edu.sv",
            "username": "newuser",
            "password": "Pass1234",
            "student_id": "Key_NEW001",
            "major": "Ingeniería Química",
        })
        assert resp.status_code == 201, f"Register failed: {resp.text}"
        data = resp.json()
        assert data["email"] == "nuevo.usuario@keyinstitute.edu.sv"
        assert data["username"] == "newuser"
        assert data["major"] == "Ingeniería Química"
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_duplicate_email(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "nuevo.usuario@keyinstitute.edu.sv",
            "username": "another",
            "password": "Pass1234",
            "student_id": "Key_DUP001",
            "major": "Ingeniería Química",
        })
        assert resp.status_code == 409

    def test_login_success(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "newuser",
            "password": "Pass1234",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "newuser",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_refresh_token(self, client):
        login_resp = client.post("/api/v1/auth/login", data={
            "username": "newuser",
            "password": "Pass1234",
        })
        refresh = login_resp.json()["refresh_token"]
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_get_me(self, client, user_token):
        resp = client.get("/api/v1/auth/me", headers=_auth(user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "user_test"
        assert "password" not in data

    def test_change_password(self, client, user_token):
        resp = client.post("/api/v1/auth/change-password", json={
            "current_password": "User1234",
            "new_password": "NewPass123",
        }, headers=_auth(user_token))
        assert resp.status_code == 200

    def test_unauthorized_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ════════════════════════════════════════════════════════════
#  TESTS — USERS
# ════════════════════════════════════════════════════════════

class TestUsers:
    def test_list_users_admin(self, client, admin_token):
        resp = client.get("/api/v1/users/", headers=_auth(admin_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    def test_list_users_forbidden_for_user(self, client, user_token):
        resp = client.get("/api/v1/users/", headers=_auth(user_token))
        assert resp.status_code == 403

    def test_get_user_by_id(self, client, admin_token):
        users_resp = client.get("/api/v1/users/", headers=_auth(admin_token))
        uid = users_resp.json()[0]["id"]
        resp = client.get(f"/api/v1/users/{uid}", headers=_auth(admin_token))
        assert resp.status_code == 200
        assert resp.json()["id"] == uid

    def test_update_profile(self, client, user_token):
        resp = client.put("/api/v1/users/profile", json={
            "email": "updated@test.com",
        }, headers=_auth(user_token))
        assert resp.status_code == 200
        assert resp.json()["email"] == "updated@test.com"


# ════════════════════════════════════════════════════════════
#  TESTS — MENÚ
# ════════════════════════════════════════════════════════════

class TestMenu:
    def test_create_item(self, client, staff_token):
        resp = client.post("/api/v1/menu/", json={
            "name": "Hamburguesa Clásica",
            "description": "Carne, lechuga, tomate",
            "price": 5.99,
            "category": "main_course",
        }, headers=_auth(staff_token))
        assert resp.status_code == 201, f"Create item failed: {resp.text}"
        data = resp.json()
        assert data["name"] == "Hamburguesa Clásica"
        assert data["price"] == 5.99

    def test_create_second_item(self, client, staff_token):
        resp = client.post("/api/v1/menu/", json={
            "name": "Refresco Cola",
            "description": "Bebida gaseosa",
            "price": 1.50,
            "category": "beverage",
        }, headers=_auth(staff_token))
        assert resp.status_code == 201

    def test_list_available(self, client, user_token):
        resp = client.get("/api/v1/menu/", headers=_auth(user_token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_get_item_by_id(self, client, user_token):
        items = client.get("/api/v1/menu/", headers=_auth(user_token)).json()
        item_id = items[0]["id"]
        resp = client.get(f"/api/v1/menu/{item_id}", headers=_auth(user_token))
        assert resp.status_code == 200

    def test_update_item(self, client, staff_token):
        items = client.get("/api/v1/menu/", headers=_auth(staff_token)).json()
        item_id = items[0]["id"]
        resp = client.put(f"/api/v1/menu/{item_id}", json={
            "price": 6.99,
        }, headers=_auth(staff_token))
        assert resp.status_code == 200
        assert resp.json()["price"] == 6.99

    def test_toggle_availability(self, client, staff_token):
        items = client.get("/api/v1/menu/", headers=_auth(staff_token)).json()
        item_id = items[0]["id"]
        resp = client.patch(
            f"/api/v1/menu/{item_id}/toggle-availability",
            headers=_auth(staff_token),
        )
        assert resp.status_code == 200
        assert resp.json()["is_available"] is False
        # Toggle back
        client.patch(f"/api/v1/menu/{item_id}/toggle-availability", headers=_auth(staff_token))

    def test_search_items(self, client, user_token):
        resp = client.get("/api/v1/menu/search?q=hamburguesa", headers=_auth(user_token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_user_cannot_create(self, client, user_token):
        resp = client.post("/api/v1/menu/", json={
            "name": "Intento",
            "price": 1.0,
            "category": "beverage",
        }, headers=_auth(user_token))
        assert resp.status_code == 403

    def test_category_filter(self, client, user_token):
        resp = client.get("/api/v1/menu/category/beverage", headers=_auth(user_token))
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════
#  TESTS — CARRITO
# ════════════════════════════════════════════════════════════

class TestCart:
    def test_add_item_to_cart(self, client, user_token):
        items = client.get("/api/v1/menu/", headers=_auth(user_token)).json()
        item_id = items[0]["id"]
        resp = client.post("/api/v1/cart/items", json={
            "menu_item_id": item_id,
            "quantity": 2,
        }, headers=_auth(user_token))
        assert resp.status_code == 201

    def test_get_cart(self, client, user_token):
        resp = client.get("/api/v1/cart/", headers=_auth(user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["item_count"] >= 1
        assert data["total"] > 0
        assert len(data["items"]) >= 1

    def test_update_quantity(self, client, user_token):
        items = client.get("/api/v1/menu/", headers=_auth(user_token)).json()
        item_id = items[0]["id"]
        resp = client.put("/api/v1/cart/items", json={
            "menu_item_id": item_id,
            "quantity": 3,
        }, headers=_auth(user_token))
        assert resp.status_code == 200

    def test_remove_item(self, client, user_token):
        items = client.get("/api/v1/menu/", headers=_auth(user_token)).json()
        item_id = items[0]["id"]
        resp = client.delete(f"/api/v1/cart/items/{item_id}", headers=_auth(user_token))
        assert resp.status_code == 200

    def test_clear_cart(self, client, user_token):
        resp = client.delete("/api/v1/cart/", headers=_auth(user_token))
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════
#  TESTS — ÓRDENES
# ════════════════════════════════════════════════════════════

class TestOrders:
    def test_create_order_empty_cart(self, client, user_token):
        resp = client.post("/api/v1/orders/", json={}, headers=_auth(user_token))
        assert resp.status_code == 400

    def test_create_order(self, client, user_token):
        items = client.get("/api/v1/menu/", headers=_auth(user_token)).json()
        client.post("/api/v1/cart/items", json={
            "menu_item_id": items[0]["id"],
            "quantity": 1,
        }, headers=_auth(user_token))

        resp = client.post("/api/v1/orders/", json={
            "notes": "Sin cebolla",
        }, headers=_auth(user_token))
        assert resp.status_code == 201, f"Create order failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "pending"
        assert data["total_price"] > 0

    def test_get_my_orders(self, client, user_token):
        resp = client.get("/api/v1/orders/mine", headers=_auth(user_token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_order_detail(self, client, user_token):
        orders = client.get("/api/v1/orders/mine", headers=_auth(user_token)).json()
        order_id = orders[0]["id"]
        resp = client.get(f"/api/v1/orders/{order_id}", headers=_auth(user_token))
        assert resp.status_code == 200

    def test_cancel_order(self, client, user_token):
        orders = client.get("/api/v1/orders/mine", headers=_auth(user_token)).json()
        pending = [o for o in orders if o["status"] == "pending"]
        if pending:
            order_id = pending[0]["id"]
            resp = client.post(f"/api/v1/orders/{order_id}/cancel", headers=_auth(user_token))
            assert resp.status_code == 200
            assert resp.json()["status"] == "cancelled"

    def test_staff_list_orders(self, client, staff_token):
        resp = client.get("/api/v1/orders/", headers=_auth(staff_token))
        assert resp.status_code == 200

    def test_staff_update_status(self, client, staff_token, user_token):
        items = client.get("/api/v1/menu/", headers=_auth(user_token)).json()
        client.post("/api/v1/cart/items", json={
            "menu_item_id": items[0]["id"],
            "quantity": 1,
        }, headers=_auth(user_token))
        order_resp = client.post("/api/v1/orders/", json={}, headers=_auth(user_token))
        assert order_resp.status_code == 201
        order_id = order_resp.json()["id"]

        resp = client.put(f"/api/v1/orders/{order_id}/status", json={
            "status": "confirmed",
        }, headers=_auth(staff_token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    def test_promotion_endpoint(self, client, user_token):
        resp = client.get("/api/v1/orders/my-promotion", headers=_auth(user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "is_birthday" in data

    def test_birthday_discount_on_order(self, client, birthday_user_token):
        """El descuento de cumpleaños se aplica automáticamente."""
        items = client.get("/api/v1/menu/", headers=_auth(birthday_user_token)).json()
        client.post("/api/v1/cart/items", json={
            "menu_item_id": items[0]["id"],
            "quantity": 1,
        }, headers=_auth(birthday_user_token))

        resp = client.post("/api/v1/orders/", json={}, headers=_auth(birthday_user_token))
        assert resp.status_code == 201, f"Birthday order failed: {resp.text}"
        data = resp.json()
        # El item cuesta 6.99, con 20% descuento ≈ 5.592
        assert data["total_price"] < 6.99
        assert "cumpleanos" in (data.get("notes") or "").lower()


# ════════════════════════════════════════════════════════════
#  TESTS — ANALYTICS
# ════════════════════════════════════════════════════════════

class TestAnalytics:
    def test_summary(self, client, staff_token):
        resp = client.get("/api/v1/analytics/summary", headers=_auth(staff_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_orders" in data
        assert "total_revenue" in data

    def test_popular(self, client, staff_token):
        resp = client.get("/api/v1/analytics/popular", headers=_auth(staff_token))
        assert resp.status_code == 200

    def test_trending(self, client, staff_token):
        resp = client.get("/api/v1/analytics/trending", headers=_auth(staff_token))
        assert resp.status_code == 200

    def test_revenue(self, client, staff_token):
        resp = client.get("/api/v1/analytics/revenue", headers=_auth(staff_token))
        assert resp.status_code == 200

    def test_user_cannot_access_analytics(self, client, user_token):
        resp = client.get("/api/v1/analytics/summary", headers=_auth(user_token))
        assert resp.status_code == 403


# ════════════════════════════════════════════════════════════
#  TESTS — NUEVOS ENDPOINTS (plan de implementación)
# ════════════════════════════════════════════════════════════

class TestAuthExtended:
    def test_register_client(self, client):
        resp = client.post("/api/v1/auth/register/client", json={
            "email": "pedro.sanchez@keyinstitute.edu.sv",
            "password": "Client123",
            "student_id": "Key_PED001",
            "birth_date": "2000-01-15",
            "major": "Ingeniería en Ciencias de la Computación Integradas",
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["username"] == "pedro_sanchez"
        assert data["sparks"] == 0
        assert data["major"] == "Ingeniería en Ciencias de la Computación Integradas"

    def test_register_staff_unauthenticated(self, client):
        resp = client.post("/api/v1/auth/register/staff", json={
            "full_name": "Ana Staff 1",
            "password": "Staff123",
            "student_id": "Key_ANA001",
        })
        assert resp.status_code == 401

    def test_register_staff_forbidden_for_user(self, client, user_token):
        resp = client.post("/api/v1/auth/register/staff", json={
            "full_name": "Ana Staff 2",
            "password": "Staff123",
            "student_id": "Key_ANA002",
        }, headers=_auth(user_token))
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Vos no pertenecesis aqui"

    def test_register_staff_success_as_admin(self, client, admin_token):
        resp = client.post("/api/v1/auth/register/staff", json={
            "full_name": "Ana Staff 3",
            "password": "Staff123",
            "student_id": "Key_ANA003",
        }, headers=_auth(admin_token))
        assert resp.status_code == 201, resp.text
        assert resp.json()["role"] == "staff"

    def test_forgot_and_reset_password(self, client):
        client.post("/api/v1/auth/register/client", json={
            "email": "reset.api@keyinstitute.edu.sv",
            "password": "OldPass1",
            "student_id": "Key_RES001",
            "major": "Ingeniería Química",
        })
        forgot = client.post("/api/v1/auth/forgot-password", json={
            "email": "reset.api@keyinstitute.edu.sv",
        })
        assert forgot.status_code == 200

        from src.services.password_reset_service import PasswordResetService
        svc = PasswordResetService()
        code = svc.generate_code("reset.api@keyinstitute.edu.sv")

        reset = client.post("/api/v1/auth/reset-password", json={
            "email": "reset.api@keyinstitute.edu.sv",
            "code": code,
            "new_password": "NewPass2",
        })
        assert reset.status_code == 200, reset.text

        login = client.post("/api/v1/auth/login", data={
            "username": "reset_api",
            "password": "NewPass2",
        })
        assert login.status_code == 200


class TestOrderSlots:
    def test_get_slots(self, client, user_token):
        resp = client.get("/api/v1/orders/slots", headers=_auth(user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "label" in data[0]
            assert "remaining" in data[0]
            assert "full" in data[0]
