"""Email delivery helpers."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from .config import EmailConfig
from .digest import DigestRun, render_markdown, summarize_digest


class EmailDeliveryError(RuntimeError):
    """Raised when digest email delivery fails."""


def send_digest_email(config: EmailConfig, digest: DigestRun) -> None:
    """Send the digest via SMTP using standard-library email support."""

    message = EmailMessage()
    message["Subject"] = _build_subject(config, digest)
    message["From"] = config.from_address
    message["To"] = ", ".join(config.to_addresses)
    message.set_content(render_markdown(digest))

    password = _resolve_password(config)

    try:
        if config.use_tls:
            with smtplib.SMTP_SSL(
                config.smtp_host,
                config.smtp_port,
                timeout=30,
            ) as server:
                _authenticate_and_send(server, message, config.username, password)
            return

        with smtplib.SMTP(
            config.smtp_host,
            config.smtp_port,
            timeout=30,
        ) as server:
            if config.use_starttls:
                server.ehlo()
                server.starttls()
                server.ehlo()
            _authenticate_and_send(server, message, config.username, password)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError(
            "failed to send digest email via "
            f"{config.smtp_host}:{config.smtp_port}: {exc}"
        ) from exc


def _authenticate_and_send(
    server: smtplib.SMTP,
    message: EmailMessage,
    username: str | None,
    password: str | None,
) -> None:
    if username is not None and password is not None:
        server.login(username, password)
    server.send_message(message)


def _resolve_password(config: EmailConfig) -> str | None:
    if config.password_env is None:
        return None

    password = os.getenv(config.password_env)
    if not password:
        raise EmailDeliveryError(
            f"email password environment variable {config.password_env!r} is not set"
        )
    return password


def _build_subject(config: EmailConfig, digest: DigestRun) -> str:
    summary = summarize_digest(digest)
    date_label = digest.generated_at.strftime("%Y-%m-%d")
    prefix = config.subject_prefix.strip()
    return f"{prefix} {date_label} | {summary}".strip()
