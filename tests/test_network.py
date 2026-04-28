from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

from paper_digest.network import fetch_bytes_with_retry


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class FetchBytesWithRetryTests(unittest.TestCase):
    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_bytes_with_retry_returns_payload_and_applies_request_delay(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(b"payload")

        payload = fetch_bytes_with_retry(
            Request("https://example.com/api"),
            timeout_seconds=30,
            request_delay_seconds=1.5,
            retry_attempts=3,
            retry_backoff_seconds=2.0,
            error_factory=RuntimeError,
            operation_description="fetch failed",
        )

        self.assertEqual(payload, b"payload")
        mock_sleep.assert_called_once_with(1.5)

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_bytes_with_retry_raises_immediately_on_non_retryable_http_error(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com/api",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=None,
        )

        with self.assertRaisesRegex(RuntimeError, "HTTP Error 400"):
            fetch_bytes_with_retry(
                Request("https://example.com/api"),
                timeout_seconds=30,
                request_delay_seconds=1.0,
                retry_attempts=3,
                retry_backoff_seconds=2.0,
                error_factory=RuntimeError,
                operation_description="fetch failed",
            )

        mock_sleep.assert_not_called()

    @patch("paper_digest.network.sleep")
    @patch("paper_digest.network.urlopen")
    def test_fetch_bytes_with_retry_retries_oserror_and_wraps_last_failure(
        self,
        mock_urlopen,
        mock_sleep,
    ) -> None:
        mock_urlopen.side_effect = [
            OSError("first failure"),
            OSError("second failure"),
            OSError("final failure"),
        ]

        with self.assertRaisesRegex(RuntimeError, "final failure"):
            fetch_bytes_with_retry(
                Request("https://example.com/api"),
                timeout_seconds=30,
                request_delay_seconds=0.0,
                retry_attempts=3,
                retry_backoff_seconds=2.0,
                error_factory=RuntimeError,
                operation_description="fetch failed",
            )

        self.assertEqual(mock_sleep.call_args_list[0].args, (2.0,))
        self.assertEqual(mock_sleep.call_args_list[1].args, (4.0,))
