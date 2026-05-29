"""
Servicio de Recuperación de Contraseña.

Genera códigos de verificación de 6 dígitos, los almacena en memoria
con expiración de 15 minutos, y los envía por correo electrónico.
Si el envío SMTP falla, muestra el código en consola (modo desarrollo).
"""

import os
import random
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.utils.logger import logger


class PasswordResetService:
    """Servicio de restablecimiento de contraseña — almacén en memoria."""

    # Almacén en memoria: {email: {"code": str, "expires_at": datetime}}
    _store: dict[str, dict] = {}

    # Tiempo de expiración en minutos
    EXPIRATION_MINUTES = 15

    def generate_code(self, email: str) -> str:
        """
        Generar un código numérico de 6 dígitos y almacenarlo.

        Args:
            email: Email del usuario.

        Returns:
            El código generado.
        """
        code = f"{random.randint(100000, 999999)}"
        expires_at = datetime.now() + timedelta(minutes=self.EXPIRATION_MINUTES)

        PasswordResetService._store[email.lower().strip()] = {
            "code": code,
            "expires_at": expires_at,
        }

        logger.info(f"Codigo de recuperacion generado para: {email}")
        return code

    def verify_code(self, email: str, code: str) -> bool:
        """
        Verificar un código de recuperación.

        Args:
            email: Email del usuario.
            code: Código ingresado por el usuario.

        Returns:
            True si el código es válido y no ha expirado.
        """
        email_key = email.lower().strip()
        entry = PasswordResetService._store.get(email_key)

        if entry is None:
            return False

        if datetime.now() > entry["expires_at"]:
            # Limpiar código expirado
            del PasswordResetService._store[email_key]
            return False

        if entry["code"] != code.strip():
            return False

        # Código válido — eliminarlo para que no se reutilice
        del PasswordResetService._store[email_key]
        logger.info(f"Codigo de recuperacion verificado para: {email}")
        return True

    def send_code(self, email: str, code: str) -> bool:
        """
        Enviar código de verificación por correo electrónico.

        Usa las credenciales SMTP configuradas en .env.
        Si falla el envío, retorna False (el código se muestra en consola).

        Args:
            email: Dirección destino.
            code: Código de 6 dígitos.

        Returns:
            True si el correo se envió exitosamente, False si no.
        """
        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", smtp_user)

        if not smtp_host or not smtp_user or not smtp_password:
            logger.warning(
                "Credenciales SMTP no configuradas. "
                "El codigo se mostrara en consola (DEV MODE)."
            )
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Do Eat - Codigo de recuperacion de contrasena"
            msg["From"] = smtp_from
            msg["To"] = email

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Do Eat - Recuperacion de contrasena</h2>
                <p>Tu codigo de verificacion es:</p>
                <h1 style="color: #2196F3; letter-spacing: 8px;">{code}</h1>
                <p>Este codigo expira en {self.EXPIRATION_MINUTES} minutos.</p>
                <p style="color: #999;">Si no solicitaste este cambio, ignora este correo.</p>
            </body>
            </html>
            """
            msg.attach(MIMEText(html_body, "html"))

            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, email, msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, email, msg.as_string())

            logger.info(f"Correo de recuperacion enviado a: {email}")
            return True

        except Exception as exc:
            logger.error(f"Error al enviar correo a {email}: {exc}")
            return False
