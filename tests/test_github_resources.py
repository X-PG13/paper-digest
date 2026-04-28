from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.github_resources import (
    GitHubIssueCommentsClient,
    GitHubIssueLabelsClient,
    GitHubPullRequestFilesClient,
    GitHubRepositoryLabelsClient,
    GitHubWorkflowArtifactsClient,
    IssueComment,
    WorkflowArtifact,
)


class GitHubResourcesTests(unittest.TestCase):
    def test_issue_comments_client_maps_list_and_write_paths(self) -> None:
        client = GitHubIssueCommentsClient(repository="owner/repo", token="token")
        with patch.object(
            client,
            "_request",
            side_effect=[
                [{"id": 1, "body": "first"}] * 100,
                [{"id": 2, "body": "second"}],
            ],
        ) as mock_request:
            comments = client.list_issue_comments(9)

        self.assertEqual(comments[0], IssueComment(comment_id=1, body="first"))
        self.assertEqual(comments[-1], IssueComment(comment_id=2, body="second"))
        self.assertEqual(mock_request.call_count, 2)

        with patch.object(client, "_request") as mock_request:
            client.create_issue_comment(7, "body")
            client.update_issue_comment(8, "updated")
            client.delete_issue_comment(8)

        self.assertEqual(mock_request.call_count, 3)

    def test_issue_labels_client_maps_list_and_delete_path(self) -> None:
        client = GitHubIssueLabelsClient(repository="owner/repo", token="token")
        with patch.object(
            client,
            "_request",
            side_effect=[
                [{"name": "bug"}] * 100,
                [{"name": "needs-info"}],
            ],
        ) as mock_request:
            labels = client.list_issue_labels(7)

        self.assertEqual(labels[0], "bug")
        self.assertEqual(labels[-1], "needs-info")
        self.assertEqual(mock_request.call_count, 2)

        with patch.object(client, "_request") as mock_request:
            client.remove_label(7, "needs info")

        mock_request.assert_called_once()
        self.assertIn("needs%20info", mock_request.call_args.args[1])

    def test_repository_labels_client_maps_get_create_and_update_paths(self) -> None:
        client = GitHubRepositoryLabelsClient(repository="owner/repo", token="token")
        with patch.object(client, "_request", side_effect=[None, {"name": "bug"}]):
            self.assertFalse(client.label_exists("missing label"))
            self.assertTrue(client.label_exists("bug"))

        with patch.object(client, "_request") as mock_request:
            client.create_label(
                name="new label",
                color="ededed",
                description="New label",
            )
            client.update_label(
                name="needs info",
                color="fbca04",
                description="Needs information",
            )

        self.assertEqual(mock_request.call_count, 2)
        self.assertIn("needs%20info", mock_request.call_args_list[1].args[1])

    def test_workflow_artifacts_client_maps_payload_key(self) -> None:
        client = GitHubWorkflowArtifactsClient(
            repository="owner/repo",
            token="token",
        )
        with patch.object(
            client,
            "_request",
            side_effect=[
                {"artifacts": [{"name": "a", "expired": False}] * 100},
                {"artifacts": [{"name": "b", "expired": True}]},
            ],
        ) as mock_request:
            artifacts = client.list_workflow_run_artifacts(4)

        self.assertEqual(
            artifacts[0],
            WorkflowArtifact(name="a", expired=False),
        )
        self.assertEqual(
            artifacts[-1],
            WorkflowArtifact(name="b", expired=True),
        )
        self.assertEqual(mock_request.call_count, 2)

    def test_pull_request_files_client_maps_filenames(self) -> None:
        client = GitHubPullRequestFilesClient(
            repository="owner/repo",
            token="token",
        )
        with patch.object(
            client,
            "_request",
            side_effect=[
                [{"filename": "a.py"}] * 100,
                [{"filename": "b.py"}],
            ],
        ) as mock_request:
            paths = client.list_pull_request_files(5)

        self.assertEqual(paths[0], "a.py")
        self.assertEqual(paths[-1], "b.py")
        self.assertEqual(mock_request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
