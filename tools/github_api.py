from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_GITHUB_TOKEN_ENV = "GITHUB_TOKEN"


class GitHubRepositoryApiClient:
    def __init__(self, *, repository: str, token: str, user_agent: str) -> None:
        self.repository = repository
        self.token = token
        self.user_agent = user_agent

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str | int] | None = None,
        payload: dict[str, object] | None = None,
        ignore_statuses: Sequence[int] = (),
    ) -> Any:
        url = f"https://api.github.com{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": self.user_agent,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"

        request = Request(url, method=method, headers=headers, data=body)
        try:
            with urlopen(request) as response:
                response_body = response.read()
        except HTTPError as exc:
            if exc.code in ignore_statuses:
                return None
            raise

        if not response_body:
            return None
        return json.loads(response_body)

    def _paginate_list(
        self,
        path: str,
        *,
        per_page: int,
        payload_key: str | None = None,
        error_message: str,
    ) -> tuple[Any, ...]:
        items: list[Any] = []
        page = 1
        while True:
            payload = self._request(
                "GET",
                path,
                query={"per_page": per_page, "page": page},
            )
            if payload_key is None:
                if not isinstance(payload, list):
                    raise ValueError(error_message)
                page_items = payload
            else:
                if not isinstance(payload, dict) or not isinstance(
                    payload.get(payload_key), list
                ):
                    raise ValueError(error_message)
                page_items = payload[payload_key]
            items.extend(page_items)
            if len(page_items) < per_page:
                break
            page += 1
        return tuple(items)
