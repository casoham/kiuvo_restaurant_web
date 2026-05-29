"""
CLI de Órdenes — Crear, ver, y gestionar órdenes.
"""

from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from sqlalchemy.orm import Session

from src.models.user import User, UserRole
from src.models.order import OrderStatus
from src.services.order_service import OrderService
from src.services.cart_service import CartService
from src.services.promotion_service import PromotionService
from src.utils.exceptions import AppError
from cli.menu_cli import view_cart

console = Console()

# Mapeo de estados a texto limpio
_STATUS_DISPLAY = {
    OrderStatus.PENDING: "Pendiente",
    OrderStatus.CONFIRMED: "Confirmada",
    OrderStatus.PREPARING: "Preparando",
    OrderStatus.READY: "Lista",
    OrderStatus.DELIVERED: "Entregada",
    OrderStatus.CANCELLED: "Cancelada",
}


def _display_orders_table(orders: list, title: str = "Órdenes") -> None:
    """Mostrar órdenes en tabla formateada."""
    if not orders:
        console.print("[yellow]No hay órdenes.[/yellow]")
        return

    table = Table(title=title, show_lines=True)
    table.add_column("ID", style="dim", width=5)
    table.add_column("Usuario", width=12)
    table.add_column("Total", justify="right", style="green")
    table.add_column("Estado")
    table.add_column("Programada", width=18)
    table.add_column("Creada", width=18)

    for order in orders:
        scheduled = (
            order.scheduled_time.strftime("%Y-%m-%d %H:%M")
            if order.scheduled_time
            else "—"
        )
        created = order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "—"
        username = order.user.username if order.user else f"user#{order.user_id}"

        table.add_row(
            str(order.id),
            username,
            f"${order.total_price:.2f}",
            _STATUS_DISPLAY.get(order.status, order.status.value),
            scheduled,
            created,
        )

    console.print(table)


def _display_order_detail(order) -> None:
    """Mostrar detalle completo de una orden."""
    console.print(
        Panel(
            f"[bold]Orden #{order.id}[/bold]\n"
            f"Estado: {_STATUS_DISPLAY.get(order.status, order.status.value)}\n"
            f"Total: [green]${order.total_price:.2f}[/green]\n"
            f"Notas: {order.notes or '—'}",
            title="Detalle de Orden",
            expand=False,
        )
    )

    if order.items:
        table = Table(show_lines=True)
        table.add_column("Item", style="bold")
        table.add_column("Precio", justify="right")
        table.add_column("Cant.", justify="center")
        table.add_column("Subtotal", justify="right", style="green")

        for item in order.items:
            table.add_row(
                item.item_name,
                f"${item.unit_price:.2f}",
                str(item.quantity),
                f"${item.unit_price * item.quantity:.2f}",
            )
        console.print(table)


def create_order_flow(session: Session, user: User) -> None:
    """Crear orden desde el carrito."""
    cart_svc = CartService(session)
    summary = cart_svc.get_cart_summary(user.id)

    if not summary:
        console.print("\n[yellow][!] Tu carrito está vacío. Agrega items primero.[/yellow]\n")
        return

    view_cart(session, user)

    # Mostrar descuento de cumpleaños si aplica
    total = cart_svc.get_total(user.id)
    if PromotionService.is_birthday(user):
        new_total, discount = PromotionService.apply_birthday_discount(user, total)
        console.print(
            Panel(
                f"[bold yellow]¡Feliz Cumpleaños, {user.username}![/bold yellow]\n"
                f"Subtotal: ${total:.2f}\n"
                f"Descuento ({PromotionService.get_birthday_discount():.0f}%): "
                f"[bold green]-${discount:.2f}[/bold green]\n"
                f"[bold]Total con descuento: ${new_total:.2f}[/bold]",
                title="Descuento de Cumpleaños",
                border_style="yellow",
                expand=False,
            )
        )

    if not Confirm.ask("\n[cyan]¿Confirmar pedido?[/cyan]"):
        return

    notes = Prompt.ask("[cyan]Notas adicionales[/cyan] (opcional)", default="")
    schedule = Confirm.ask("[cyan]¿Programar para después?[/cyan]", default=False)

    scheduled_time = None
    if schedule:
        scheduled_time = _pick_schedule_slot(session)

    order_svc = OrderService(session)
    try:
        order = order_svc.create_from_cart(
            user=user,
            notes=notes or None,
            scheduled_time=scheduled_time,
        )
        console.print(
            f"\n[bold green][OK] ¡Orden #{order.id} creada exitosamente![/bold green]\n"
            f"[green]Total: ${order.total_price:.2f}[/green]\n"
        )
    except AppError as e:
        console.print(f"\n[red][ERROR] {e.message}[/red]\n")


def _pick_schedule_slot(session: Session) -> datetime | None:
    """Menú visual de franjas horarias con barra de ocupación."""
    order_svc = OrderService(session)
    base = datetime.now(timezone.utc)
    slots = order_svc.get_schedule_slots(base_date=base, hours_ahead=8, slot_minutes=15)

    if not slots:
        console.print("[yellow]No hay franjas disponibles en este momento.[/yellow]")
        return None

    console.print("\n[bold]Franjas horarias (15 min)[/bold]\n")
    table = Table(show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Hora", width=8)
    table.add_column("Ocupación", min_width=28)
    table.add_column("Cupo", justify="right", width=10)

    for i, slot in enumerate(slots, 1):
        used = slot["count"]
        max_orders = order_svc.MAX_ORDERS_PER_SLOT
        pct = min(100, int(used / max_orders * 100)) if max_orders else 0
        bar_filled = int(pct / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        status = "[red]LLENO[/red]" if slot["full"] else f"[green]{slot['remaining']} libres[/green]"
        table.add_row(
            str(i),
            slot["label"],
            f"{bar} {used}/{max_orders}",
            status,
        )
    console.print(table)

    choice = IntPrompt.ask(
        "\n[cyan]Elige franja[/cyan] (0 = cancelar)",
        default=0,
    )
    if choice < 1 or choice > len(slots):
        return None

    selected = slots[choice - 1]
    if selected["full"]:
        console.print("[red]Esa franja está llena. Elige otra.[/red]")
        return _pick_schedule_slot(session)

    return selected["start"]


def view_my_orders(session: Session, user: User) -> None:
    """Ver órdenes del usuario actual."""
    order_svc = OrderService(session)
    orders = order_svc.get_user_orders(user.id)
    _display_orders_table(orders, "Mis Órdenes")


def view_order_detail_flow(session: Session, user: User) -> None:
    """Ver detalle de una orden específica."""
    order_id = IntPrompt.ask("[cyan]ID de la orden[/cyan]")
    order_svc = OrderService(session)
    try:
        order = order_svc.get_by_id(order_id)
        # Verificar que el usuario tiene acceso
        is_manager = user.role in {UserRole.ADMIN, UserRole.STAFF}
        if order.user_id != user.id and not is_manager:
            console.print("\n[red][ERROR] No tienes acceso a esta orden[/red]\n")
            return
        _display_order_detail(order)
    except AppError as e:
        console.print(f"\n[red][ERROR] {e.message}[/red]\n")


def cancel_order_flow(session: Session, user: User) -> None:
    """Cancelar una orden."""
    view_my_orders(session, user)
    order_id = IntPrompt.ask("\n[cyan]ID de la orden a cancelar[/cyan]")

    if Confirm.ask("[yellow]¿Estás seguro de cancelar esta orden?[/yellow]"):
        order_svc = OrderService(session)
        try:
            order_svc.cancel_order(user, order_id)
            console.print("\n[green][OK] Orden cancelada[/green]\n")
        except AppError as e:
            console.print(f"\n[red][ERROR] {e.message}[/red]\n")


# ── Gestión de órdenes (ADMIN/STAFF) ───────────────────────

def view_all_orders(session: Session) -> None:
    """Ver todas las órdenes (admin/staff)."""
    order_svc = OrderService(session)
    orders = order_svc.get_all_orders()
    _display_orders_table(orders, "Todas las Órdenes")


def view_active_orders(session: Session) -> None:
    """Ver órdenes activas (admin/staff)."""
    order_svc = OrderService(session)
    orders = order_svc.get_active_orders()
    _display_orders_table(orders, "Órdenes Activas")


def change_order_status_flow(session: Session, user: User) -> None:
    """Cambiar estado de una orden (admin/staff)."""
    view_active_orders(session)

    order_id = IntPrompt.ask("\n[cyan]ID de la orden[/cyan]")

    console.print("\n[bold]Estados disponibles:[/bold]")
    statuses = list(OrderStatus)
    for i, status in enumerate(statuses, 1):
        console.print(f"  {i}. {_STATUS_DISPLAY.get(status, status.value)}")

    choice = IntPrompt.ask("Nuevo estado")
    if 1 <= choice <= len(statuses):
        new_status = statuses[choice - 1]
        order_svc = OrderService(session)
        try:
            order = order_svc.update_status(user, order_id, new_status)
            console.print(
                f"\n[green][OK] Orden #{order.id} actualizada a "
                f"{_STATUS_DISPLAY.get(new_status, new_status.value)}[/green]\n"
            )
        except AppError as e:
            console.print(f"\n[red][ERROR] {e.message}[/red]\n")
    else:
        console.print("[red]Opción inválida[/red]")
