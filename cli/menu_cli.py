"""
CLI de Menú — Ver menú, buscar, y CRUD (admin/staff).
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm

from sqlalchemy.orm import Session

from src.models.user import User, UserRole
from src.models.menu_item import MenuCategory
from src.services.menu_service import MenuService
from src.services.cart_service import CartService
from src.services.analytics_service import AnalyticsService
from src.utils.exceptions import AppError

console = Console()

# Mapeo de categorías a nombres legibles
_CATEGORY_NAMES = {
    MenuCategory.APPETIZER: "Entradas",
    MenuCategory.MAIN_COURSE: "Platos Fuertes",
    MenuCategory.DESSERT: "Postres",
    MenuCategory.BEVERAGE: "Bebidas",
    MenuCategory.SIDE: "Acompañamientos",
    MenuCategory.SPECIAL: "Especiales",
}


def _display_menu_table(items: list, title: str = "Menú") -> None:
    """Mostrar items del menú en una tabla formateada."""
    if not items:
        console.print("[yellow]No hay items para mostrar.[/yellow]")
        return

    table = Table(title=title, show_lines=True)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Nombre", style="bold")
    table.add_column("Descripción", max_width=35)
    table.add_column("Precio", justify="right", style="green")
    table.add_column("Categoría")
    table.add_column("Estado", justify="center")

    for item in items:
        cat_name = _CATEGORY_NAMES.get(item.category, item.category.value)
        flags = []
        if item.is_featured:
            flags.append("[*]")
        if item.is_new:
            flags.append("[NEW]")
        if not item.is_available:
            flags.append("[X]")
        else:
            flags.append("[OK]")

        table.add_row(
            str(item.id),
            item.name,
            (item.description or "")[:35],
            f"${item.price:.2f}",
            cat_name,
            " ".join(flags),
        )

    console.print(table)


def view_menu(session: Session, user: User) -> None:
    """Ver el menú completo (solo disponibles para USER, todos para ADMIN/STAFF)."""
    menu_svc = MenuService(session)

    if user.role in {UserRole.ADMIN, UserRole.STAFF}:
        items = menu_svc.get_all()
        title = "Menú Completo (Admin)"
    else:
        items = menu_svc.get_available()
        title = "Menú de DO Eat"

    _display_menu_table(items, title)


def view_by_category(session: Session) -> None:
    """Ver menú filtrado por categoría."""
    console.print("\n[bold]Categorías disponibles:[/bold]")
    categories = list(MenuCategory)
    for i, cat in enumerate(categories, 1):
        console.print(f"  {i}. {_CATEGORY_NAMES.get(cat, cat.value)}")

    choice = IntPrompt.ask("\nSelecciona categoría", default=1)
    if 1 <= choice <= len(categories):
        menu_svc = MenuService(session)
        selected = categories[choice - 1]
        items = menu_svc.get_by_category(selected)
        _display_menu_table(items, _CATEGORY_NAMES.get(selected, selected.value))
    else:
        console.print("[red]Opción inválida[/red]")


def add_to_cart_flow(session: Session, user: User) -> None:
    """Agregar un item del menú al carrito."""
    view_menu(session, user)
    console.print()

    item_id = IntPrompt.ask("[cyan]ID del item a agregar[/cyan]")
    quantity = IntPrompt.ask("[cyan]Cantidad[/cyan]", default=1)

    cart_svc = CartService(session)
    try:
        cart_svc.add_item(user.id, item_id, quantity)
        console.print(f"\n[green][OK] Item agregado al carrito (x{quantity})[/green]\n")
    except AppError as e:
        console.print(f"\n[red][ERROR] {e.message}[/red]\n")


def view_cart(session: Session, user: User) -> None:
    """Ver contenido del carrito."""
    cart_svc = CartService(session)
    summary = cart_svc.get_cart_summary(user.id)

    if not summary:
        console.print("\n[yellow][!] Tu carrito está vacío[/yellow]\n")
        return

    table = Table(title="Tu Carrito", show_lines=True)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Nombre", style="bold")
    table.add_column("Precio", justify="right", style="green")
    table.add_column("Cantidad", justify="center")
    table.add_column("Subtotal", justify="right", style="bold green")

    for item in summary:
        table.add_row(
            str(item["menu_item_id"]),
            item["name"],
            f"${item['price']:.2f}",
            str(item["quantity"]),
            f"${item['subtotal']:.2f}",
        )

    total = cart_svc.get_total(user.id)
    table.add_section()
    table.add_row("", "", "", "[bold]TOTAL[/bold]", f"[bold]${total:.2f}[/bold]")

    console.print(table)


def remove_from_cart_flow(session: Session, user: User) -> None:
    """Remover item del carrito."""
    view_cart(session, user)
    item_id = IntPrompt.ask("[cyan]ID del item a remover[/cyan]")

    cart_svc = CartService(session)
    if cart_svc.remove_item(user.id, item_id):
        console.print("\n[green][OK] Item removido del carrito[/green]\n")
    else:
        console.print("\n[red][ERROR] Item no encontrado en el carrito[/red]\n")


def clear_cart_flow(session: Session, user: User) -> None:
    """Vaciar carrito."""
    if Confirm.ask("[yellow]¿Vaciar todo el carrito?[/yellow]"):
        cart_svc = CartService(session)
        cart_svc.clear_cart(user.id)
        console.print("\n[green][OK] Carrito vaciado[/green]\n")


# ── CRUD Admin/Staff ────────────────────────────────────────

def create_menu_item_flow(session: Session, user: User) -> None:
    """Crear un nuevo item de menú (ADMIN/STAFF)."""
    console.print(Panel("[bold cyan]Crear Item de Menú[/bold cyan]", expand=False))

    name = Prompt.ask("[cyan]Nombre[/cyan]")
    description = Prompt.ask("[cyan]Descripción[/cyan]", default="")
    price = float(Prompt.ask("[cyan]Precio[/cyan]"))

    console.print("\n[bold]Categorías:[/bold]")
    categories = list(MenuCategory)
    for i, cat in enumerate(categories, 1):
        console.print(f"  {i}. {_CATEGORY_NAMES.get(cat, cat.value)}")
    cat_choice = IntPrompt.ask("Categoría", default=1)
    category = categories[cat_choice - 1] if 1 <= cat_choice <= len(categories) else MenuCategory.MAIN_COURSE

    is_featured = Confirm.ask("¿Destacado?", default=False)
    is_new = Confirm.ask("¿Marcar como nuevo?", default=True)

    menu_svc = MenuService(session)
    try:
        item = menu_svc.create_item(user, {
            "name": name,
            "description": description or None,
            "price": price,
            "category": category,
            "is_featured": is_featured,
            "is_new": is_new,
        })
        console.print(f"\n[green][OK] Item '{item.name}' creado (ID: {item.id})[/green]\n")
    except AppError as e:
        console.print(f"\n[red][ERROR] {e.message}[/red]\n")


def update_menu_item_flow(session: Session, user: User) -> None:
    """Actualizar un item existente (ADMIN/STAFF)."""
    view_menu(session, user)
    item_id = IntPrompt.ask("\n[cyan]ID del item a editar[/cyan]")

    menu_svc = MenuService(session)
    try:
        item = menu_svc.get_by_id(item_id)
    except AppError as e:
        console.print(f"\n[red][ERROR] {e.message}[/red]\n")
        return

    console.print(f"\nEditando: [bold]{item.name}[/bold] (deja vacío para no cambiar)")
    name = Prompt.ask("Nombre", default=item.name)
    description = Prompt.ask("Descripción", default=item.description or "")
    price_str = Prompt.ask("Precio", default=str(item.price))

    data = {}
    if name != item.name:
        data["name"] = name
    if description != (item.description or ""):
        data["description"] = description or None
    try:
        new_price = float(price_str)
        if new_price != item.price:
            data["price"] = new_price
    except ValueError:
        pass

    if data:
        try:
            updated = menu_svc.update_item(user, item_id, data)
            console.print(f"\n[green][OK] Item '{updated.name}' actualizado[/green]\n")
        except AppError as e:
            console.print(f"\n[red][ERROR] {e.message}[/red]\n")
    else:
        console.print("\n[yellow]Sin cambios.[/yellow]\n")


def toggle_availability_flow(session: Session, user: User) -> None:
    """Alternar disponibilidad de un item (ADMIN/STAFF)."""
    view_menu(session, user)
    item_id = IntPrompt.ask("\n[cyan]ID del item[/cyan]")

    menu_svc = MenuService(session)
    try:
        item = menu_svc.toggle_availability(user, item_id)
        status = "disponible [OK]" if item.is_available else "no disponible [X]"
        console.print(f"\n[green][OK] '{item.name}' ahora está {status}[/green]\n")
    except AppError as e:
        console.print(f"\n[red][ERROR] {e.message}[/red]\n")


def delete_menu_item_flow(session: Session, user: User) -> None:
    """Eliminar item del menú (ADMIN/STAFF)."""
    view_menu(session, user)
    item_id = IntPrompt.ask("\n[cyan]ID del item a eliminar[/cyan]")

    if Confirm.ask("[yellow]¿Estás seguro?[/yellow]"):
        menu_svc = MenuService(session)
        try:
            menu_svc.delete_item(user, item_id)
            console.print("\n[green][OK] Item eliminado[/green]\n")
        except AppError as e:
            console.print(f"\n[red][ERROR] {e.message}[/red]\n")




# ── Featured & Rankings ─────────────────────────────────────

def toggle_featured_flow(session: Session, user: User) -> None:
    """Alternar estado destacado de un item (ADMIN/STAFF)."""
    view_menu(session, user)
    item_id = IntPrompt.ask("\n[cyan]ID del item[/cyan]")

    menu_svc = MenuService(session)
    try:
        item = menu_svc.toggle_featured(user, item_id)
        status = "destacado [*]" if item.is_featured else "no destacado"
        console.print(f"\n[green][OK] '{item.name}' ahora está {status}[/green]\n")
    except AppError as e:
        console.print(f"\n[red][ERROR] {e.message}[/red]\n")


def view_featured_items(session: Session) -> None:
    """Ver productos destacados."""
    menu_svc = MenuService(session)
    items = menu_svc.get_featured()

    if not items:
        console.print("\n[yellow]No hay productos destacados actualmente.[/yellow]\n")
        return

    console.print()
    _display_menu_table(items, "Productos Destacados")


def view_rankings(session: Session) -> None:
    """Ver rankings de productos (más vendidos, más ingresos, trending)."""
    analytics = AnalyticsService(session)

    console.print(
        "\n[bold]Rankings[/bold]\n"
        "  1. [HOT] Más vendidos (por cantidad)\n"
        "  2. [REV] Más ingresos\n"
        "  3. [TREND] Trending (últimos 7 días)\n"
        "  0. Volver\n"
    )
    choice = IntPrompt.ask("Opción", default=0)

    if choice == 0:
        return

    if choice == 1:
        items = analytics.get_most_popular_items(limit=10)
        title = "Productos Más Vendidos"
    elif choice == 2:
        items = analytics.get_top_revenue_items(limit=10)
        title = "Productos con Más Ingresos"
    elif choice == 3:
        items = analytics.get_trending_items(limit=10, days=7)
        title = "Trending (Últimos 7 Días)"
    else:
        console.print("[red]Opción inválida[/red]")
        return

    if not items:
        console.print("\n[yellow]No hay datos suficientes para mostrar rankings.[/yellow]\n")
        return

    table = Table(title=title, show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Producto", style="bold")
    table.add_column("Categoría")
    table.add_column("Precio", justify="right", style="green")
    table.add_column("Vendidos", justify="center", style="cyan")

    if choice == 2:
        table.add_column("Ingresos", justify="right", style="bold green")

    for i, item in enumerate(items, 1):
        medal = {1: "1st", 2: "2nd", 3: "3rd"}.get(i, str(i))
        row = [
            medal,
            item["name"],
            item["category"],
            f"${item['price']:.2f}",
            str(item["total_sold"]),
        ]
        if choice == 2:
            row.append(f"${item.get('total_revenue', 0):.2f}")
        table.add_row(*row)

    console.print(table)

    # Mostrar resumen
    total_orders = analytics.get_total_orders_count()
    total_revenue = analytics.get_total_revenue()
    console.print(
        Panel(
            f"Total órdenes completadas: [bold]{total_orders}[/bold]\n"
            f"Ingresos totales: [bold green]${total_revenue:.2f}[/bold green]",
            title="Resumen General",
            expand=False,
        )
    )
