from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from tools.github_resources import (
    GitHubIssueCommentsClient,
    GitHubIssueLabelsClient,
    GitHubPullRequestFilesClient,
    GitHubRepositoryLabelsClient,
    GitHubWorkflowArtifactsClient,
    IssueComment,
    WorkflowArtifact,
)


class IssueCommentsClientProtocol(Protocol):
    def list_issue_comments(self, issue_number: int) -> tuple[IssueComment, ...]: ...

    def create_issue_comment(self, issue_number: int, body: str) -> None: ...

    def update_issue_comment(self, comment_id: int, body: str) -> None: ...

    def delete_issue_comment(self, comment_id: int) -> None: ...


class IssueLabelsClientProtocol(Protocol):
    def list_issue_labels(self, issue_number: int) -> tuple[str, ...]: ...

    def add_labels(self, issue_number: int, labels: tuple[str, ...]) -> None: ...

    def remove_label(self, issue_number: int, label: str) -> None: ...


class RepositoryLabelsClientProtocol(Protocol):
    def label_exists(self, name: str) -> bool: ...

    def create_label(self, *, name: str, color: str, description: str) -> None: ...

    def update_label(self, *, name: str, color: str, description: str) -> None: ...


class WorkflowArtifactsClientProtocol(Protocol):
    def list_workflow_run_artifacts(
        self,
        workflow_run_id: int,
    ) -> tuple[WorkflowArtifact, ...]: ...


class PullRequestFilesClientProtocol(Protocol):
    def list_pull_request_files(self, pull_number: int) -> tuple[str, ...]: ...


def find_marker_comment(
    comments: Sequence[IssueComment],
    *,
    marker: str,
) -> IssueComment | None:
    for comment in comments:
        if marker in comment.body:
            return comment
    return None


class GitHubManagedCommentsService:
    def __init__(
        self,
        *,
        repository: str | None = None,
        token: str | None = None,
        client: IssueCommentsClientProtocol | None = None,
    ) -> None:
        if client is None:
            if repository is None or token is None:
                raise ValueError(
                    "repository and token are required when no comment "
                    "client is provided"
                )
            client = GitHubIssueCommentsClient(repository=repository, token=token)
        self._client = client

    def sync_marker_comment(
        self,
        *,
        issue_number: int,
        marker: str,
        desired_body: str | None,
    ) -> str:
        existing_comment = find_marker_comment(
            self._client.list_issue_comments(issue_number),
            marker=marker,
        )

        if desired_body is None:
            if existing_comment is None:
                return "unchanged"
            self._client.delete_issue_comment(existing_comment.comment_id)
            return "deleted"

        if marker not in desired_body:
            raise ValueError("comment body must include the configured marker")

        if existing_comment is None:
            self._client.create_issue_comment(issue_number, desired_body)
            return "created"

        if existing_comment.body == desired_body:
            return "unchanged"

        self._client.update_issue_comment(existing_comment.comment_id, desired_body)
        return "updated"


@dataclass(frozen=True)
class IssueLabelSyncResult:
    added: tuple[str, ...]
    removed: tuple[str, ...]


@dataclass(frozen=True)
class RepositoryLabelSpec:
    name: str
    color: str
    description: str


@dataclass(frozen=True)
class RepositoryLabelSyncResult:
    created: tuple[str, ...]
    updated: tuple[str, ...]


def normalize_labels(labels: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for label in labels:
        cleaned = label.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return tuple(normalized)


class GitHubIssueLabelsService:
    def __init__(
        self,
        *,
        repository: str | None = None,
        token: str | None = None,
        client: IssueLabelsClientProtocol | None = None,
    ) -> None:
        if client is None:
            if repository is None or token is None:
                raise ValueError(
                    "repository and token are required when no labels "
                    "client is provided"
                )
            client = GitHubIssueLabelsClient(repository=repository, token=token)
        self._client = client

    def sync_labels(
        self,
        issue_number: int,
        *,
        ensure_labels: Sequence[str],
        remove_labels: Sequence[str],
    ) -> IssueLabelSyncResult:
        ensure = normalize_labels(ensure_labels)
        remove = normalize_labels(remove_labels)
        overlap = sorted(set(ensure) & set(remove))
        if overlap:
            raise ValueError("ensure and remove labels overlap: " + ", ".join(overlap))

        if not ensure and not remove:
            return IssueLabelSyncResult(added=(), removed=())

        current = set(self._client.list_issue_labels(issue_number))
        labels_to_add = tuple(label for label in ensure if label not in current)
        labels_to_remove = tuple(label for label in remove if label in current)

        if labels_to_add:
            self._client.add_labels(issue_number, labels_to_add)
        for label in labels_to_remove:
            self._client.remove_label(issue_number, label)

        return IssueLabelSyncResult(
            added=labels_to_add,
            removed=labels_to_remove,
        )


class GitHubRepositoryLabelsService:
    def __init__(
        self,
        *,
        repository: str | None = None,
        token: str | None = None,
        client: RepositoryLabelsClientProtocol | None = None,
    ) -> None:
        if client is None:
            if repository is None or token is None:
                raise ValueError(
                    "repository and token are required when no repository labels "
                    "client is provided"
                )
            client = GitHubRepositoryLabelsClient(repository=repository, token=token)
        self._client = client

    def sync_labels(
        self,
        labels: Sequence[RepositoryLabelSpec],
    ) -> RepositoryLabelSyncResult:
        created: list[str] = []
        updated: list[str] = []
        for label in labels:
            if self._client.label_exists(label.name):
                self._client.update_label(
                    name=label.name,
                    color=label.color,
                    description=label.description,
                )
                updated.append(label.name)
                continue

            self._client.create_label(
                name=label.name,
                color=label.color,
                description=label.description,
            )
            created.append(label.name)

        return RepositoryLabelSyncResult(
            created=tuple(created),
            updated=tuple(updated),
        )


class GitHubWorkflowArtifactsService:
    def __init__(
        self,
        *,
        repository: str | None = None,
        token: str | None = None,
        client: WorkflowArtifactsClientProtocol | None = None,
    ) -> None:
        if client is None:
            if repository is None or token is None:
                raise ValueError(
                    "repository and token are required when no artifacts "
                    "client is provided"
                )
            client = GitHubWorkflowArtifactsClient(repository=repository, token=token)
        self._client = client

    def list_artifacts(self, workflow_run_id: int) -> tuple[WorkflowArtifact, ...]:
        return self._client.list_workflow_run_artifacts(workflow_run_id)

    def has_unexpired_artifact(
        self,
        workflow_run_id: int,
        *,
        artifact_name: str,
    ) -> bool:
        return any(
            artifact.name == artifact_name and not artifact.expired
            for artifact in self.list_artifacts(workflow_run_id)
        )


class GitHubPullRequestFilesService:
    def __init__(
        self,
        *,
        repository: str | None = None,
        token: str | None = None,
        client: PullRequestFilesClientProtocol | None = None,
    ) -> None:
        if client is None:
            if repository is None or token is None:
                raise ValueError(
                    "repository and token are required when no pull-request "
                    "files client is provided"
                )
            client = GitHubPullRequestFilesClient(repository=repository, token=token)
        self._client = client

    def list_paths(self, pull_number: int) -> tuple[str, ...]:
        return self._client.list_pull_request_files(pull_number)
