from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

from paper_digest.network import _retry_delay_seconds, fetch_bytes_with_retry


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class RetryDelayAdditionalTests(unittest.TestCase):
    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_bytes_with_retry_retries_retryable_http_error_then_succeeds(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.side_effect = [
            HTTPError(
                url="https://example.com/api",
                code=429,
                msg="Too Many Requests",
                hdrs={"Retry-After": "2"},
                fp=None,
            ),
            DummyHTTPResponse(b"payload"),
        ]

        payload = fetch_bytes_with_retry(
            Request("https://example.com/api"),
            timeout_seconds=30,
            request_delay_seconds=0.0,
            retry_attempts=2,
            retry_backoff_seconds=0.5,
            error_factory=RuntimeError,
            operation_description="fetch failed",
        )

        self.assertEqual(payload, b"payload")
        mock_sleep.assert_called_once_with(2.0)

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_bytes_with_retry_can_return_without_request_delay(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(b"payload")

        payload = fetch_bytes_with_retry(
            Request("https://example.com/api"),
            timeout_seconds=30,
            request_delay_seconds=0.0,
            retry_attempts=1,
            retry_backoff_seconds=2.0,
            error_factory=RuntimeError,
            operation_description="fetch failed",
        )

        self.assertEqual(payload, b"payload")
        mock_sleep.assert_not_called()

    def test_fetch_bytes_with_retry_raises_operation_message_when_no_attempts_run(
        self,
    ) -> None:
        with self.assertRaisesRegex(RuntimeError, "^fetch failed$"):
            fetch_bytes_with_retry(
                Request("https://example.com/api"),
                timeout_seconds=30,
                request_delay_seconds=0.0,
                retry_attempts=0,
                retry_backoff_seconds=2.0,
                error_factory=RuntimeError,
                operation_description="fetch failed",
            )

    def test_retry_delay_uses_maximum_of_retry_after_and_local_delays(self) -> None:
        http_error = HTTPError(
            url="https://example.com/api",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "0.5"},
            fp=None,
        )

        delay = _retry_delay_seconds(
            http_error=http_error,
            request_delay_seconds=2.0,
            retry_backoff_seconds=3.0,
            attempt=1,
        )

        self.assertEqual(delay, 3.0)

    def test_retry_delay_falls_back_when_retry_after_header_is_missing(self) -> None:
        http_error = HTTPError(
            url="https://example.com/api",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=None,
        )

        delay = _retry_delay_seconds(
            http_error=http_error,
            request_delay_seconds=0.0,
            retry_backoff_seconds=2.0,
            attempt=2,
        )

        self.assertEqual(delay, 4.0)

    def test_retry_delay_falls_back_when_retry_after_is_invalid(self) -> None:
        http_error = HTTPError(
            url="https://example.com/api",
            code=503,
            msg="Service Unavailable",
            hdrs={"Retry-After": "not-a-number"},
            fp=None,
        )

        delay = _retry_delay_seconds(
            http_error=http_error,
            request_delay_seconds=0.0,
            retry_backoff_seconds=0.25,
            attempt=1,
        )

        self.assertEqual(delay, 1.0)
