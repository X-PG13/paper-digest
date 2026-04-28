from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from tools.github_api import GitHubRepositoryApiClient


class GitHubApiTests(unittest.TestCase):
    def test_paginate_list_supports_list_and_dict_payloads(self) -> None:
        client = GitHubRepositoryApiClient(
            repository="owner/repo",
            token="token",
            user_agent="paper-digest-test",
        )

        with patch.object(
            client,
            "_request",
            side_effect=[
                [{"id": 1}] * 2,
                [{"id": 3}],
            ],
        ):
            items = client._paginate_list(
                "/repos/owner/repo/issues/1/comments",
                per_page=2,
                error_message="bad comments payload",
            )
        self.assertEqual(len(items), 3)

        with patch.object(
            client,
            "_request",
            side_effect=[
                {"artifacts": [{"id": 1}] * 2},
                {"artifacts": [{"id": 3}]},
            ],
        ):
            items = client._paginate_list(
                "/repos/owner/repo/actions/runs/1/artifacts",
                per_page=2,
                payload_key="artifacts",
                error_message="bad artifacts payload",
            )
        self.assertEqual(len(items), 3)

    def test_paginate_list_validates_payload_shape(self) -> None:
        client = GitHubRepositoryApiClient(
            repository="owner/repo",
            token="token",
            user_agent="paper-digest-test",
        )
        with patch.object(client, "_request", return_value={"bad": []}):
            with self.assertRaisesRegex(ValueError, "bad comments payload"):
                client._paginate_list(
                    "/repos/owner/repo/issues/1/comments",
                    per_page=2,
                    error_message="bad comments payload",
                )

    def test_request_can_ignore_http_statuses(self) -> None:
        client = GitHubRepositoryApiClient(
            repository="owner/repo",
            token="token",
            user_agent="paper-digest-test",
        )
        error = HTTPError(
            url="https://api.github.com/test",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )
        with patch("tools.github_api.urlopen", side_effect=error):
            self.assertIsNone(
                client._request(
                    "DELETE",
                    "/repos/owner/repo/issues/1/labels/needs-info",
                    ignore_statuses=(404,),
                )
            )


if __name__ == "__main__":
    unittest.main()
