"""
CLI Principal — Punto de entrada de la aplicación.

Uso:
    python -m cli.main          # Iniciar la app
    python -m cli.main --seed   # Inicializar BD con datos de prueba
"""

import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en el path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt
from rich.text import Text

from config.database import init_db, get_session
from config.settings import settings
from src.models.user import User, UserRole
from src.utils.logger import logger

# Importar sub-CLIs
from cli.auth_cli import login_flow, register_flow, forgot_password_flow, profile_flow
from cli.menu_cli import (
    view_menu,
    view_by_category,
    add_to_cart_flow,
    view_cart,
    remove_from_cart_flow,
    clear_cart_flow,
    create_menu_item_flow,
    update_menu_item_flow,
    toggle_availability_flow,
    toggle_featured_flow,
    delete_menu_item_flow,
    view_featured_items,
    view_rankings,
)
from cli.order_cli import (
    create_order_flow,
    view_my_orders,
    view_order_detail_flow,
    cancel_order_flow,
    view_all_orders,
    view_active_orders,
    change_order_status_flow,
)

console = Console()


# ════════════════════════════════════════════════════════════
#  SEED DATA
# ════════════════════════════════════════════════════════════

def seed_database() -> None:
    """Inicializar BD con datos de prueba."""
    from datetime import date, datetime, timezone
    from src.services.auth_service import AuthService
    from src.services.menu_service import MenuService
    from src.services.cart_service import CartService
    from src.services.order_service import OrderService
    from src.models.menu_item import MenuCategory
    from src.models.order import OrderStatus

    session = get_session()
    auth = AuthService(session)
    menu_svc = MenuService(session)

    try:
        # ── Usuarios ────────────────────────────────────────
        console.print("[cyan]Creando usuarios de prueba...[/cyan]")
        today = date.today()
        admin = auth.register(
            "admin@restaurant.com", "admin", "Admin123",
            student_id="Key_ADM001", birth_date=date(1990, 3, 15),
            role=UserRole.ADMIN,
        )
        staff = auth.register_staff(
            "María López", "Staff123", student_id="Key_STF001",
        )
        user = auth.register_client(
            "juan.perez@keyinstitute.edu.sv", "User1234",
            student_id="Key_USR001", birth_date=date(2002, 11, 10),
            major="Ingeniería en Ciencias de la Computación Integradas",
        )
        birthday_user = auth.register_client(
            "ana.garcia@keyinstitute.edu.sv", "Bday1234",
            student_id="Key_BDAY01",
            birth_date=date(2001, today.month, today.day),
            major="Ingeniería Química",
        )

        # ── Items del menú ──────────────────────────────────
        console.print("[cyan]Creando menú de prueba...[/cyan]")
        menu_items = [
            # Entradas
            {"name": "Nachos con Guacamole", "description": "Nachos crujientes con guacamole fresco, pico de gallo y crema", "price": 8.99, "category": MenuCategory.APPETIZER, "is_featured": True},
            {"name": "Sopa de Tortilla", "description": "Sopa tradicional con tortilla, aguacate y queso", "price": 6.50, "category": MenuCategory.APPETIZER},
            {"name": "Empanadas de Queso", "description": "3 empanadas rellenas de queso y jalapeño", "price": 7.25, "category": MenuCategory.APPETIZER, "is_new": True},
            # Platos fuertes
            {"name": "Tacos al Pastor", "description": "3 tacos con carne al pastor, piña, cilantro y cebolla", "price": 12.99, "category": MenuCategory.MAIN_COURSE, "is_featured": True},
            {"name": "Enchiladas Verdes", "description": "Enchiladas bañadas en salsa verde con pollo y crema", "price": 11.50, "category": MenuCategory.MAIN_COURSE},
            {"name": "Burrito Supremo", "description": "Burrito grande con carne, frijoles, arroz, queso y guacamole", "price": 13.99, "category": MenuCategory.MAIN_COURSE, "is_new": True},
            {"name": "Chiles Rellenos", "description": "Chiles poblanos rellenos de queso con salsa de tomate", "price": 10.99, "category": MenuCategory.MAIN_COURSE},
            # Postres
            {"name": "Churros con Chocolate", "description": "6 churros calientes con salsa de chocolate", "price": 5.99, "category": MenuCategory.DESSERT, "is_featured": True},
            {"name": "Flan Napolitano", "description": "Flan casero con caramelo", "price": 4.99, "category": MenuCategory.DESSERT},
            {"name": "Tres Leches", "description": "Pastel de tres leches con crema batida", "price": 6.50, "category": MenuCategory.DESSERT, "is_new": True},
            # Bebidas
            {"name": "Agua de Horchata", "description": "Bebida tradicional de arroz y canela", "price": 3.50, "category": MenuCategory.BEVERAGE},
            {"name": "Margarita Clásica", "description": "Margarita con tequila, limón y sal", "price": 8.99, "category": MenuCategory.BEVERAGE, "is_featured": True},
            {"name": "Jamaica Fresca", "description": "Agua fresca de flor de jamaica", "price": 3.00, "category": MenuCategory.BEVERAGE},
            # Acompañamientos
            {"name": "Arroz Mexicano", "description": "Arroz rojo con verduras", "price": 2.99, "category": MenuCategory.SIDE},
            {"name": "Frijoles Refritos", "description": "Frijoles con queso y totopos", "price": 2.50, "category": MenuCategory.SIDE},
            # Especiales
            {"name": "Parrillada para 2", "description": "Selección de carnes a la parrilla con guarniciones", "price": 29.99, "category": MenuCategory.SPECIAL, "is_featured": True},
        ]

        created_items = []
        for item_data in menu_items:
            created_items.append(menu_svc.create_item(admin, item_data))

        # ── Órdenes de ejemplo (para rankings) ──────────────
        console.print("[cyan]Creando órdenes de ejemplo para rankings...[/cyan]")
        cart_svc = CartService(session)
        order_svc = OrderService(session)

        # Orden 1: user compra tacos y nachos
        cart_svc.add_item(user.id, created_items[3].id, 3)  # 3 Tacos al Pastor
        cart_svc.add_item(user.id, created_items[0].id, 2)  # 2 Nachos
        order1 = order_svc.create_from_cart(user, notes="Primera orden de prueba")
        order_svc.update_status(admin, order1.id, OrderStatus.CONFIRMED)
        order_svc.update_status(admin, order1.id, OrderStatus.PREPARING)
        order_svc.update_status(admin, order1.id, OrderStatus.READY)
        order_svc.update_status(admin, order1.id, OrderStatus.DELIVERED)

        # Orden 2: user compra burritos y churros
        cart_svc.add_item(user.id, created_items[5].id, 2)  # 2 Burrito Supremo
        cart_svc.add_item(user.id, created_items[7].id, 1)  # 1 Churros
        order2 = order_svc.create_from_cart(user, notes="Segunda orden")
        order_svc.update_status(admin, order2.id, OrderStatus.CONFIRMED)
        order_svc.update_status(admin, order2.id, OrderStatus.PREPARING)
        order_svc.update_status(admin, order2.id, OrderStatus.READY)
        order_svc.update_status(admin, order2.id, OrderStatus.DELIVERED)

        # Orden 3: birthday_user compra tacos y margarita
        cart_svc.add_item(birthday_user.id, created_items[3].id, 2)  # 2 Tacos
        cart_svc.add_item(birthday_user.id, created_items[11].id, 2)  # 2 Margaritas
        order3 = order_svc.create_from_cart(birthday_user, notes="Pedido de cumpleañero")
        order_svc.update_status(admin, order3.id, OrderStatus.CONFIRMED)

        # Orden 4: staff compra parrillada
        cart_svc.add_item(staff.id, created_items[15].id, 1)  # 1 Parrillada
        cart_svc.add_item(staff.id, created_items[11].id, 3)  # 3 Margaritas
        order4 = order_svc.create_from_cart(staff, notes="Cena especial")
        order_svc.update_status(admin, order4.id, OrderStatus.CONFIRMED)
        order_svc.update_status(admin, order4.id, OrderStatus.PREPARING)
        order_svc.update_status(admin, order4.id, OrderStatus.READY)
        order_svc.update_status(admin, order4.id, OrderStatus.DELIVERED)

        console.print(
            Panel(
                "[bold green]Base de datos inicializada exitosamente[/bold green]\n\n"
                "[bold]Usuarios creados:[/bold]\n"
                "  • admin / admin123 (ADMIN) — Carnet: ADM-2024-001\n"
                "  • staff1 / staff123 (STAFF) — Carnet: STF-2024-001\n"
                "  • user1 / user123 (USER) — Carnet: UNI-2024-001\n"
                "  • cumple / cumple123 (USER) — Carnet: UNI-2024-002 [Cumpleaños HOY!]\n\n"
                f"[bold]Items de menú creados:[/bold] {len(menu_items)}\n"
                "[bold]Órdenes de ejemplo:[/bold] 4 (para rankings)",
                title="Seed Data",
                expand=False,
            )
        )

    except Exception as e:
        console.print(f"[yellow][!] Seed ya existente o error: {e}[/yellow]")
    finally:
        session.close()


# ════════════════════════════════════════════════════════════
#  MENÚS DE NAVEGACIÓN
# ════════════════════════════════════════════════════════════

def _show_header() -> None:
    """Mostrar banner de la app."""
    banner = Text()
    banner.append(settings.APP_NAME, style="bold magenta")
    banner.append(f"  v{settings.APP_VERSION}", style="dim")
    console.print(Panel(banner, expand=False))


def _auth_menu(session) -> User | None:
    """Menú de autenticación (antes de loguearse)."""
    while True:
        console.print(
            "\n[bold]¿Qué deseas hacer?[/bold]\n"
            "  1. Iniciar sesión\n"
            "  2. Crear cuenta\n"
            "  3. ¿Olvidaste tu contraseña?\n"
            "  0. Salir\n"
        )
        choice = IntPrompt.ask("Opción", default=0)

        if choice == 1:
            user = login_flow(session)
            if user:
                return user
        elif choice == 2:
            user = register_flow(session)
            if user:
                return user
        elif choice == 3:
            forgot_password_flow(session)
        elif choice == 0:
            return None
        else:
            console.print("[red]Opción inválida[/red]")


def _user_menu(session, user: User) -> None:
    """Menú para usuarios regulares."""
    while True:
        console.print(
            f"\n[bold cyan]{user.username}[/bold cyan] [dim]({user.role.value} | Carnet: {user.student_id})[/dim]\n"
            "[bold]── Menú ──[/bold]\n"
            "  1. Ver menú\n"
            "  2. Ver por categoría\n"
            "  3. Productos destacados\n"
            "  4. Ver rankings\n"
            "[bold]── Carrito ──[/bold]\n"
            "  5. Agregar al carrito\n"
            "  6. Ver carrito\n"
            "  7. Remover del carrito\n"
            "  8. Vaciar carrito\n"
            "[bold]── Pedidos ──[/bold]\n"
            "  9. Crear pedido\n"
            " 10. Mis pedidos\n"
            " 11. Ver detalle de pedido\n"
            " 12. Cancelar pedido\n"
            " 13. Mi perfil (Sparks y gastos)\n"
            "  0. Cerrar sesión\n"
        )
        choice = IntPrompt.ask("Opción", default=0)

        actions = {
            1: lambda: view_menu(session, user),
            2: lambda: view_by_category(session),
            3: lambda: view_featured_items(session),
            4: lambda: view_rankings(session),
            5: lambda: add_to_cart_flow(session, user),
            6: lambda: view_cart(session, user),
            7: lambda: remove_from_cart_flow(session, user),
            8: lambda: clear_cart_flow(session, user),
            9: lambda: create_order_flow(session, user),
            10: lambda: view_my_orders(session, user),
            11: lambda: view_order_detail_flow(session, user),
            12: lambda: cancel_order_flow(session, user),
            13: lambda: profile_flow(session, user),
        }

        if choice == 0:
            console.print("[yellow]Sesión cerrada.[/yellow]")
            break
        elif choice in actions:
            actions[choice]()
        else:
            console.print("[red]Opción inválida[/red]")


def _staff_menu(session, user: User) -> None:
    """Menú para staff (incluye gestión de menú y órdenes)."""
    while True:
        console.print(
            f"\n[bold cyan]{user.username}[/bold cyan] [dim]({user.role.value})[/dim]\n"
            "[bold]── Menú ──[/bold]\n"
            "  1. Ver menú completo\n"
            "  2. Crear item\n"
            "  3. Editar item\n"
            "  4. Toggle disponibilidad\n"
            "  5. Toggle destacado\n"
            "  6. Eliminar item\n"
            "[bold]── Órdenes ──[/bold]\n"
            "  7. Órdenes activas\n"
            "  8. Todas las órdenes\n"
            "  9. Cambiar estado de orden\n"
            " 10. Ver detalle de orden\n"
            "[bold]── Analytics ──[/bold]\n"
            " 11. Ver rankings\n"
            " 12. Productos destacados\n"
            "  0. Cerrar sesión\n"
        )
        choice = IntPrompt.ask("Opción", default=0)

        actions = {
            1: lambda: view_menu(session, user),
            2: lambda: create_menu_item_flow(session, user),
            3: lambda: update_menu_item_flow(session, user),
            4: lambda: toggle_availability_flow(session, user),
            5: lambda: toggle_featured_flow(session, user),
            6: lambda: delete_menu_item_flow(session, user),
            7: lambda: view_active_orders(session),
            8: lambda: view_all_orders(session),
            9: lambda: change_order_status_flow(session, user),
            10: lambda: view_order_detail_flow(session, user),
            11: lambda: view_rankings(session),
            12: lambda: view_featured_items(session),
        }

        if choice == 0:
            console.print("[yellow]Sesión cerrada.[/yellow]")
            break
        elif choice in actions:
            actions[choice]()
        else:
            console.print("[red]Opción inválida[/red]")


def _admin_menu(session, user: User) -> None:
    """Menú para admin (todo incluido)."""
    from src.services.user_service import UserService

    while True:
        console.print(
            f"\n[bold cyan]{user.username}[/bold cyan] [dim]({user.role.value})[/dim]\n"
            "[bold]── Menú ──[/bold]\n"
            "  1. Ver menú completo\n"
            "  2. Crear item\n"
            "  3. Editar item\n"
            "  4. Toggle disponibilidad\n"
            "  5. Toggle destacado\n"
            "  6. Eliminar item\n"
            "[bold]── Órdenes ──[/bold]\n"
            "  7. Órdenes activas\n"
            "  8. Todas las órdenes\n"
            "  9. Cambiar estado de orden\n"
            " 10. Ver detalle de orden\n"
            "[bold]── Usuarios ──[/bold]\n"
            " 11. Listar usuarios\n"
            " 12. Cambiar rol de usuario\n"
            " 13. Desactivar usuario\n"
            " 14. Activar usuario\n"
            "[bold]── Analytics ──[/bold]\n"
            " 15. Ver rankings\n"
            " 16. Productos destacados\n"
            "  0. Cerrar sesión\n"
        )
        choice = IntPrompt.ask("Opción", default=0)

        def _list_users():
            from rich.table import Table
            user_svc = UserService(session)
            users = user_svc.get_all()
            table = Table(title="Usuarios", show_lines=True)
            table.add_column("ID", style="dim", width=4)
            table.add_column("Usuario", style="bold")
            table.add_column("Email")
            table.add_column("Rol")
            table.add_column("Activo", justify="center")
            for u in users:
                table.add_row(
                    str(u.id), u.username, u.email,
                    u.role.value, "Si" if u.is_active else "No",
                )
            console.print(table)

        def _change_role():
            _list_users()
            uid = IntPrompt.ask("\n[cyan]ID del usuario[/cyan]")
            console.print("Roles: 1=USER, 2=STAFF, 3=ADMIN")
            role_choice = IntPrompt.ask("Nuevo rol")
            role_map = {1: UserRole.USER, 2: UserRole.STAFF, 3: UserRole.ADMIN}
            if role_choice in role_map:
                user_svc = UserService(session)
                try:
                    updated = user_svc.change_role(user, uid, role_map[role_choice])
                    console.print(f"\n[green]Rol cambiado: {updated.username} → {updated.role.value}[/green]\n")
                except Exception as e:
                    console.print(f"\n[red][ERROR] {e}[/red]\n")

        def _deactivate():
            _list_users()
            uid = IntPrompt.ask("\n[cyan]ID del usuario a desactivar[/cyan]")
            user_svc = UserService(session)
            try:
                user_svc.deactivate_user(user, uid)
                console.print("\n[green]Usuario desactivado[/green]\n")
            except Exception as e:
                console.print(f"\n[red][ERROR] {e}[/red]\n")

        def _activate():
            _list_users()
            uid = IntPrompt.ask("\n[cyan]ID del usuario a activar[/cyan]")
            user_svc = UserService(session)
            try:
                user_svc.activate_user(user, uid)
                console.print("\n[green]Usuario activado[/green]\n")
            except Exception as e:
                console.print(f"\n[red][ERROR] {e}[/red]\n")

        actions = {
            1: lambda: view_menu(session, user),
            2: lambda: create_menu_item_flow(session, user),
            3: lambda: update_menu_item_flow(session, user),
            4: lambda: toggle_availability_flow(session, user),
            5: lambda: toggle_featured_flow(session, user),
            6: lambda: delete_menu_item_flow(session, user),
            7: lambda: view_active_orders(session),
            8: lambda: view_all_orders(session),
            9: lambda: change_order_status_flow(session, user),
            10: lambda: view_order_detail_flow(session, user),
            11: _list_users,
            12: _change_role,
            13: _deactivate,
            14: _activate,
            15: lambda: view_rankings(session),
            16: lambda: view_featured_items(session),
        }

        if choice == 0:
            console.print("[yellow]Sesión cerrada.[/yellow]")
            break
        elif choice in actions:
            actions[choice]()
        else:
            console.print("[red]Opción inválida[/red]")


# ════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════

def main() -> None:
    """Punto de entrada principal."""
    # Inicializar BD
    init_db()
    logger.info(f"{settings.APP_NAME} iniciado (env: {settings.APP_ENV})")

    # Check for --seed flag
    if "--seed" in sys.argv:
        seed_database()
        if len(sys.argv) == 2:  # Solo --seed, sin interactivo
            return

    _show_header()

    session = get_session()
    try:
        while True:
            user = _auth_menu(session)
            if user is None:
                console.print("\n[bold]Hasta luego[/bold]\n")
                break

            # Dirigir al menú según rol
            if user.role == UserRole.ADMIN:
                _admin_menu(session, user)
            elif user.role == UserRole.STAFF:
                _staff_menu(session, user)
            else:
                _user_menu(session, user)
    except KeyboardInterrupt:
        console.print("\n\n[bold]Hasta luego[/bold]\n")
    finally:
        session.close()
        logger.info("Aplicación cerrada")


if __name__ == "__main__":
    main()
