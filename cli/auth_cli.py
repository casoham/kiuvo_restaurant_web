"""
CLI de Autenticación — Login, registro bifurcado y recuperación de contraseña.
"""

from datetime import date, datetime, timedelta, timezone

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.user import User, UserRole
from src.models.order import Order, OrderStatus
from src.services.auth_service import AuthService
from src.services.promotion_service import PromotionService
from src.services.password_reset_service import PasswordResetService
from src.utils.exceptions import AppError

console = Console()


def login_flow(session: Session) -> User | None:
    """Flujo interactivo de login."""
    console.print(Panel("[bold cyan]Iniciar Sesión[/bold cyan]", expand=False))

    username = Prompt.ask("[cyan]Usuario[/cyan]")
    password = Prompt.ask("[cyan]Contraseña[/cyan]", password=True)

    auth = AuthService(session)
    try:
        user = auth.login(username, password)
        console.print(
            f"\n[bold green]¡Bienvenido, {user.username}![/bold green] "
            f"[dim](Rol: {user.role.value} | Carnet: {user.student_id})[/dim]\n"
        )

        bday_msg = PromotionService.get_birthday_message(user)
        if bday_msg:
            console.print(
                Panel(
                    f"[bold yellow]{bday_msg}[/bold yellow]",
                    title="¡Feliz Cumpleaños!",
                    border_style="yellow",
                    expand=False,
                )
            )

        return user
    except AppError as e:
        console.print(f"\n[bold red][ERROR] {e.message}[/bold red]\n")
        return None


def _register_client_flow(session: Session) -> User | None:
    """Registro de cliente con email institucional."""
    console.print(Panel("[bold cyan]Registro — Cliente[/bold cyan]", expand=False))

    email = Prompt.ask(
        "[cyan]Email institucional[/cyan]",
        default="nombre.apellido@keyinstitute.edu.sv",
    )
    student_id = Prompt.ask("[cyan]Carnet universitario[/cyan] (Key_xxxxxx)")
    password = Prompt.ask("[cyan]Contraseña[/cyan] (mín. 6, mayúscula y minúscula)", password=True)
    confirm = Prompt.ask("[cyan]Confirmar contraseña[/cyan]", password=True)

    if password != confirm:
        console.print("\n[bold red][ERROR] Las contraseñas no coinciden[/bold red]\n")
        return None

    birth_date = None
    birth_str = Prompt.ask(
        "[cyan]Fecha de nacimiento[/cyan] (YYYY-MM-DD, Enter para omitir)",
        default="",
    )
    if birth_str.strip():
        try:
            birth_date = date.fromisoformat(birth_str.strip())
            if birth_date > date.today():
                console.print("[yellow][!] Fecha en el futuro, se omitirá.[/yellow]")
                birth_date = None
        except ValueError:
            console.print("[yellow][!] Formato inválido, se omitirá.[/yellow]")

    console.print("\n[bold]Selecciona tu carrera:[/bold]")
    console.print("  1. Ingeniería Mecatrónica y Robótica")
    console.print("  2. Ingeniería Industrial y Manufactura Avanzada")
    console.print("  3. Ingeniería Química")
    console.print("  4. Ingeniería en Ciencias de la Computación Integradas")
    major_choice = Prompt.ask("Carrera", choices=["1", "2", "3", "4"])
    major_map = {
        "1": "Ingeniería Mecatrónica y Robótica",
        "2": "Ingeniería Industrial y Manufactura Avanzada",
        "3": "Ingeniería Química",
        "4": "Ingeniería en Ciencias de la Computación Integradas",
    }
    major = major_map[major_choice]

    auth = AuthService(session)
    try:
        user = auth.register_client(
            email=email,
            password=password,
            student_id=student_id,
            birth_date=birth_date,
            major=major,
        )
        console.print(
            f"\n[bold green]Cuenta creada: {user.username}[/bold green]\n"
            f"[dim]Email: {user.email} | Carnet: {user.student_id}[/dim]\n"
        )
        return user
    except AppError as e:
        console.print(f"\n[bold red][ERROR] {e.message}[/bold red]\n")
        return None


def _register_staff_flow(session: Session) -> User | None:
    """Registro de staff con ID presencial."""
    console.print(Panel("[bold cyan]Registro — Staff[/bold cyan]", expand=False))

    full_name = Prompt.ask("[cyan]Nombre completo[/cyan]")
    student_id = Prompt.ask("[cyan]ID presencial[/cyan] (Key_xxxxxx)")
    password = Prompt.ask("[cyan]Contraseña[/cyan]", password=True)
    confirm = Prompt.ask("[cyan]Confirmar contraseña[/cyan]", password=True)

    if password != confirm:
        console.print("\n[bold red][ERROR] Las contraseñas no coinciden[/bold red]\n")
        return None

    auth = AuthService(session)
    try:
        user = auth.register_staff(
            full_name=full_name,
            password=password,
            student_id=student_id,
        )
        console.print(
            f"\n[bold green]Staff registrado: {user.username}[/bold green]\n"
            f"[dim]ID presencial: {user.student_id}[/dim]\n"
        )
        return user
    except AppError as e:
        console.print(f"\n[bold red][ERROR] {e.message}[/bold red]\n")
        return None


def register_flow(session: Session) -> User | None:
    """Registro bifurcado: cliente o staff."""
    console.print(
        "\n[bold]¿Qué tipo de cuenta deseas crear?[/bold]\n"
        "  1. Cliente (estudiante)\n"
        "  2. Staff (personal)\n"
        "  0. Cancelar\n"
    )
    choice = Prompt.ask("Opción", choices=["0", "1", "2"], default="0")
    if choice == "1":
        return _register_client_flow(session)
    if choice == "2":
        return _register_staff_flow(session)
    return None


def forgot_password_flow(session: Session) -> None:
    """Flujo de recuperación de contraseña por email."""
    console.print(Panel("[bold cyan]Recuperar Contraseña[/bold cyan]", expand=False))

    email = Prompt.ask("[cyan]Email de tu cuenta[/cyan]")
    auth = AuthService(session)
    from src.repositories.user_repository import UserRepository

    user = UserRepository(session).get_by_email(email.lower().strip())
    if user is None:
        console.print("\n[yellow]Si el email existe, recibirás un código.[/yellow]\n")
        return

    reset_svc = PasswordResetService()
    code = reset_svc.generate_code(email)
    sent = reset_svc.send_code(email, code)
    if sent:
        console.print("\n[green]Código enviado a tu correo.[/green]\n")
    else:
        console.print(
            Panel(
                f"[bold yellow]Código (modo desarrollo):[/bold yellow] [bold]{code}[/bold]\n"
                f"[dim]Expira en {PasswordResetService.EXPIRATION_MINUTES} minutos[/dim]",
                title="DEV MODE",
                border_style="yellow",
            )
        )

    new_password = Prompt.ask("[cyan]Nueva contraseña[/cyan]", password=True)
    code_input = Prompt.ask("[cyan]Código de verificación[/cyan]")

    if not reset_svc.verify_code(email, code_input):
        console.print("\n[bold red][ERROR] Código inválido o expirado[/bold red]\n")
        return

    try:
        auth.change_password_by_email(email, new_password)
        console.print("\n[bold green]Contraseña actualizada exitosamente[/bold green]\n")
    except AppError as e:
        console.print(f"\n[bold red][ERROR] {e.message}[/bold red]\n")


def profile_flow(session: Session, user: User) -> None:
    """Vista de perfil con Sparks y gasto semanal (clientes)."""
    session.refresh(user)

    table = Table(title="Mi Perfil", show_lines=True)
    table.add_column("Campo", style="cyan")
    table.add_column("Valor", style="bold")
    table.add_row("Usuario", user.username)
    table.add_row("Email", user.email)
    table.add_row("Carnet / ID", user.student_id)
    table.add_row("Rol", user.role.value)
    table.add_row("Sparks", str(user.sparks))
    if user.birth_date:
        table.add_row("Nacimiento", str(user.birth_date))
    if user.major:
        table.add_row("Carrera", user.major)
    console.print(table)

    if user.role == UserRole.USER:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        weekly_spend = (
            session.query(func.coalesce(func.sum(Order.total_price), 0.0))
            .filter(
                Order.user_id == user.id,
                Order.status != OrderStatus.CANCELLED,
                Order.created_at >= week_ago,
            )
            .scalar()
        )
        console.print(
            f"\n[bold]Gasto acumulado (últimos 7 días):[/bold] "
            f"[green]${float(weekly_spend):.2f}[/green]\n"
        )

    promo = PromotionService.get_promotion_info(user)
    if promo.get("is_birthday"):
        console.print(
            Panel(promo["message"], title="Promoción activa", border_style="yellow")
        )
