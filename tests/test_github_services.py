from __future__ import annotations

import unittest

from tools.github_resources import IssueComment, WorkflowArtifact
from tools.github_services import (
    GitHubIssueLabelsService,
    GitHubManagedCommentsService,
    GitHubPullRequestFilesService,
    GitHubRepositoryLabelsService,
    GitHubWorkflowArtifactsService,
    IssueLabelSyncResult,
    RepositoryLabelSpec,
    RepositoryLabelSyncResult,
    find_marker_comment,
    normalize_labels,
)


class FakeCommentsClient:
    def __init__(self, comments: list[IssueComment]) -> None:
        self.comments = list(comments)
        self.created: list[tuple[int, str]] = []
        self.updated: list[tuple[int, str]] = []
        self.deleted: list[int] = []

    def list_issue_comments(self, issue_number: int) -> tuple[IssueComment, ...]:
        return tuple(self.comments)

    def create_issue_comment(self, issue_number: int, body: str) -> None:
        self.created.append((issue_number, body))

    def update_issue_comment(self, comment_id: int, body: str) -> None:
        self.updated.append((comment_id, body))

    def delete_issue_comment(self, comment_id: int) -> None:
        self.deleted.append(comment_id)


class FakeLabelsClient:
    def __init__(self, labels: list[str]) -> None:
        self.labels = list(labels)
        self.added: list[tuple[int, tuple[str, ...]]] = []
        self.removed: list[tuple[int, str]] = []

    def list_issue_labels(self, issue_number: int) -> tuple[str, ...]:
        return tuple(self.labels)

    def add_labels(self, issue_number: int, labels: tuple[str, ...]) -> None:
        self.added.append((issue_number, labels))
        for label in labels:
            if label not in self.labels:
                self.labels.append(label)

    def remove_label(self, issue_number: int, label: str) -> None:
        self.removed.append((issue_number, label))
        if label in self.labels:
            self.labels.remove(label)


class FakeRepositoryLabelsClient:
    def __init__(self, existing: list[str]) -> None:
        self.existing = set(existing)
        self.created: list[RepositoryLabelSpec] = []
        self.updated: list[RepositoryLabelSpec] = []

    def label_exists(self, name: str) -> bool:
        return name in self.existing

    def create_label(self, *, name: str, color: str, description: str) -> None:
        self.created.append(
            RepositoryLabelSpec(
                name=name,
                color=color,
                description=description,
            )
        )
        self.existing.add(name)

    def update_label(self, *, name: str, color: str, description: str) -> None:
        self.updated.append(
            RepositoryLabelSpec(
                name=name,
                color=color,
                description=description,
            )
        )


class FakeArtifactsClient:
    def __init__(self, artifacts: tuple[WorkflowArtifact, ...]) -> None:
        self.artifacts = artifacts

    def list_workflow_run_artifacts(
        self,
        workflow_run_id: int,
    ) -> tuple[WorkflowArtifact, ...]:
        return self.artifacts


class FakePullFilesClient:
    def __init__(self, paths: tuple[str, ...]) -> None:
        self.paths = paths

    def list_pull_request_files(self, pull_number: int) -> tuple[str, ...]:
        return self.paths


class GitHubServicesTests(unittest.TestCase):
    def test_find_marker_comment_returns_first_match(self) -> None:
        comment = find_marker_comment(
            (
                IssueComment(comment_id=1, body="no marker"),
                IssueComment(comment_id=2, body="<!-- marker -->\nhello"),
                IssueComment(comment_id=3, body="<!-- marker -->\nworld"),
            ),
            marker="<!-- marker -->",
        )

        self.assertIsNotNone(comment)
        assert comment is not None
        self.assertEqual(comment.comment_id, 2)

    def test_managed_comments_service_syncs_create_update_delete_and_noop(self) -> None:
        created_client = FakeCommentsClient([])
        created = GitHubManagedCommentsService(
            client=created_client
        ).sync_marker_comment(
            issue_number=12,
            marker="<!-- marker -->",
            desired_body="<!-- marker -->\ncreated",
        )
        self.assertEqual(created, "created")
        self.assertEqual(created_client.created, [(12, "<!-- marker -->\ncreated")])

        updated_client = FakeCommentsClient(
            [IssueComment(comment_id=5, body="<!-- marker -->\nold")]
        )
        updated = GitHubManagedCommentsService(
            client=updated_client
        ).sync_marker_comment(
            issue_number=12,
            marker="<!-- marker -->",
            desired_body="<!-- marker -->\nnew",
        )
        self.assertEqual(updated, "updated")
        self.assertEqual(updated_client.updated, [(5, "<!-- marker -->\nnew")])

        unchanged_client = FakeCommentsClient(
            [IssueComment(comment_id=6, body="<!-- marker -->\nkeep")]
        )
        unchanged = GitHubManagedCommentsService(
            client=unchanged_client
        ).sync_marker_comment(
            issue_number=12,
            marker="<!-- marker -->",
            desired_body="<!-- marker -->\nkeep",
        )
        self.assertEqual(unchanged, "unchanged")

        deleted_client = FakeCommentsClient(
            [IssueComment(comment_id=7, body="<!-- marker -->\nbye")]
        )
        deleted = GitHubManagedCommentsService(
            client=deleted_client
        ).sync_marker_comment(
            issue_number=12,
            marker="<!-- marker -->",
            desired_body=None,
        )
        self.assertEqual(deleted, "deleted")
        self.assertEqual(deleted_client.deleted, [7])

    def test_managed_comments_service_rejects_body_without_marker(self) -> None:
        with self.assertRaisesRegex(ValueError, "must include the configured marker"):
            GitHubManagedCommentsService(
                client=FakeCommentsClient([])
            ).sync_marker_comment(
                issue_number=12,
                marker="<!-- marker -->",
                desired_body="missing marker",
            )

    def test_labels_service_normalizes_and_syncs(self) -> None:
        self.assertEqual(
            normalize_labels([" needs-info ", "", "bug", "bug"]),
            ("needs-info", "bug"),
        )

        client = FakeLabelsClient(["bug", "stale"])
        result = GitHubIssueLabelsService(client=client).sync_labels(
            12,
            ensure_labels=("needs-info", "bug"),
            remove_labels=("stale",),
        )
        self.assertEqual(
            result,
            IssueLabelSyncResult(added=("needs-info",), removed=("stale",)),
        )
        self.assertEqual(client.added, [(12, ("needs-info",))])
        self.assertEqual(client.removed, [(12, "stale")])

        with self.assertRaisesRegex(ValueError, "overlap"):
            GitHubIssueLabelsService(client=FakeLabelsClient(["bug"])).sync_labels(
                5,
                ensure_labels=("needs-info",),
                remove_labels=("needs-info",),
            )

    def test_repository_labels_service_creates_and_updates_labels(self) -> None:
        client = FakeRepositoryLabelsClient(["bug"])
        labels = (
            RepositoryLabelSpec(
                name="bug",
                color="d73a4a",
                description="Bug reports",
            ),
            RepositoryLabelSpec(
                name="maintenance",
                color="7057ff",
                description="Maintenance work",
            ),
        )

        result = GitHubRepositoryLabelsService(client=client).sync_labels(labels)

        self.assertEqual(
            result,
            RepositoryLabelSyncResult(
                created=("maintenance",),
                updated=("bug",),
            ),
        )
        self.assertEqual(client.updated, [labels[0]])
        self.assertEqual(client.created, [labels[1]])

    def test_workflow_artifacts_service_lists_and_matches_unexpired_artifacts(
        self,
    ) -> None:
        service = GitHubWorkflowArtifactsService(
            client=FakeArtifactsClient(
                (
                    WorkflowArtifact(name="other", expired=False),
                    WorkflowArtifact(name="docs-check-report", expired=True),
                    WorkflowArtifact(name="docs-check-report", expired=False),
                )
            )
        )

        self.assertEqual(len(service.list_artifacts(42)), 3)
        self.assertTrue(
            service.has_unexpired_artifact(
                42,
                artifact_name="docs-check-report",
            )
        )
        self.assertFalse(
            service.has_unexpired_artifact(
                42,
                artifact_name="missing",
            )
        )

    def test_pull_request_files_service_lists_paths(self) -> None:
        service = GitHubPullRequestFilesService(
            client=FakePullFilesClient(("a.py", "b.py"))
        )
        self.assertEqual(service.list_paths(5), ("a.py", "b.py"))


if __name__ == "__main__":
    unittest.main()
