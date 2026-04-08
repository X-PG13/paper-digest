"""Shared network retry helpers."""

from __future__ import annotations

from collections.abc import Callable
from time import sleep
from urllib.error import HTTPError
from urllib.request import Request, urlopen

RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


def fetch_bytes_with_retry(
    request: Request,
    *,
    timeout_seconds: int,
    request_delay_seconds: float,
    retry_attempts: int,
    retry_backoff_seconds: float,
    error_factory: Callable[[str], Exception],
    operation_description: str,
) -> bytes:
    """Fetch raw bytes with bounded retry and backoff."""

    last_error: BaseException | None = None
    for attempt in range(1, retry_attempts + 1):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload = bytes(response.read())
        except HTTPError as exc:
            last_error = exc
            if exc.code in RETRYABLE_STATUS_CODES and attempt < retry_attempts:
                sleep(
                    _retry_delay_seconds(
                        http_error=exc,
                        request_delay_seconds=request_delay_seconds,
                        retry_backoff_seconds=retry_backoff_seconds,
                        attempt=attempt,
                    )
                )
                continue
            raise error_factory(f"{operation_description}: {exc}") from exc
        except OSError as exc:
            last_error = exc
            if attempt < retry_attempts:
                sleep(
                    _retry_delay_seconds(
                        http_error=None,
                        request_delay_seconds=request_delay_seconds,
                        retry_backoff_seconds=retry_backoff_seconds,
                        attempt=attempt,
                    )
                )
                continue
            raise error_factory(f"{operation_description}: {exc}") from exc

        if request_delay_seconds > 0:
            sleep(request_delay_seconds)
        return payload

    message = operation_description
    if last_error is not None:
        message = f"{operation_description}: {last_error}"
    raise error_factory(message)


def _retry_delay_seconds(
    *,
    http_error: HTTPError | None,
    request_delay_seconds: float,
    retry_backoff_seconds: float,
    attempt: int,
) -> float:
    if http_error is not None:
        retry_after = http_error.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(
                    float(retry_after),
                    request_delay_seconds,
                    retry_backoff_seconds,
                    1.0,
                )
            except ValueError:
                pass

    return max(
        request_delay_seconds,
        retry_backoff_seconds * float(2 ** (attempt - 1)),
        1.0,
    )
