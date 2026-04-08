from __future__ import annotations

import os
import smtplib
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from paper_digest.config import EmailConfig
from paper_digest.digest import DigestRun, FeedDigest
from paper_digest.email_delivery import EmailDeliveryError, send_digest_email


class FakeSMTP:
    instances: list[FakeSMTP] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.ehlo_calls = 0
        self.starttls_called = False
        self.login_args: tuple[str, str] | None = None
        self.message = None
        FakeSMTP.instances.append(self)

    def __enter__(self) -> FakeSMTP:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def ehlo(self) -> None:
        self.ehlo_calls += 1

    def starttls(self) -> None:
        self.starttls_called = True

    def login(self, username: str, password: str) -> None:
        self.login_args = (username, password)

    def send_message(self, message: object) -> None:
        self.message = message


class EmailDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeSMTP.instances.clear()

    def test_send_digest_email_uses_starttls_and_login(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[])],
        )
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="bot@example.com",
            password_env="SMTP_PASSWORD",
            from_address="bot@example.com",
            to_addresses=["reader@example.com"],
            use_tls=False,
            use_starttls=True,
            subject_prefix="[Digest]",
        )

        with patch("paper_digest.email_delivery.smtplib.SMTP", FakeSMTP):
            with patch.dict(os.environ, {"SMTP_PASSWORD": "secret"}, clear=False):
                send_digest_email(config, digest)

        server = FakeSMTP.instances[0]
        assert server.message is not None
        self.assertTrue(server.starttls_called)
        self.assertEqual(server.login_args, ("bot@example.com", "secret"))
        self.assertIn("[Digest] 2026-04-08 | LLM=0", server.message["Subject"])

    def test_send_digest_email_requires_password_env(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[],
        )
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=465,
            username="bot@example.com",
            password_env="SMTP_PASSWORD",
            from_address="bot@example.com",
            to_addresses=["reader@example.com"],
            use_tls=True,
            use_starttls=False,
            subject_prefix="[Digest]",
        )

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(EmailDeliveryError):
                send_digest_email(config, digest)

    @patch(
        "paper_digest.email_delivery.smtplib.SMTP_SSL",
        side_effect=smtplib.SMTPException("boom"),
    )
    def test_send_digest_email_wraps_smtp_errors(self, _mock_smtp_ssl) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[],
        )
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=465,
            username=None,
            password_env=None,
            from_address="bot@example.com",
            to_addresses=["reader@example.com"],
            use_tls=True,
            use_starttls=False,
            subject_prefix="[Digest]",
        )

        with self.assertRaises(EmailDeliveryError):
            send_digest_email(config, digest)
