from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from tools.github_api import GitHubRepositoryApiClient

COMMENTS_PER_PAGE = 100
LABELS_PER_PAGE = 100
WORKFLOW_ARTIFACTS_PER_PAGE = 100
PULL_FILES_PER_PAGE = 100


@dataclass(frozen=True)
class IssueComment:
    comment_id: int
    body: str


@dataclass(frozen=True)
class WorkflowArtifact:
    name: str
    expired: bool


class GitHubIssueCommentsClient(GitHubRepositoryApiClient):
    def __init__(self, *, repository: str, token: str) -> None:
        super().__init__(
            repository=repository,
            token=token,
            user_agent="paper-digest-sync-marker-comment",
        )

    def list_issue_comments(self, issue_number: int) -> tuple[IssueComment, ...]:
        payload = self._paginate_list(
            f"/repos/{self.repository}/issues/{issue_number}/comments",
            per_page=COMMENTS_PER_PAGE,
            error_message="GitHub comments API did not return a list payload",
        )
        return tuple(
            IssueComment(
                comment_id=int(item["id"]),
                body=str(item.get("body", "")),
            )
            for item in payload
            if isinstance(item, dict) and "id" in item
        )

    def create_issue_comment(self, issue_number: int, body: str) -> None:
        self._request(
            "POST",
            f"/repos/{self.repository}/issues/{issue_number}/comments",
            payload={"body": body},
        )

    def update_issue_comment(self, comment_id: int, body: str) -> None:
        self._request(
            "PATCH",
            f"/repos/{self.repository}/issues/comments/{comment_id}",
            payload={"body": body},
        )

    def delete_issue_comment(self, comment_id: int) -> None:
        self._request(
            "DELETE",
            f"/repos/{self.repository}/issues/comments/{comment_id}",
        )


class GitHubIssueLabelsClient(GitHubRepositoryApiClient):
    def __init__(self, *, repository: str, token: str) -> None:
        super().__init__(
            repository=repository,
            token=token,
            user_agent="paper-digest-sync-issue-labels",
        )

    def list_issue_labels(self, issue_number: int) -> tuple[str, ...]:
        payload = self._paginate_list(
            f"/repos/{self.repository}/issues/{issue_number}/labels",
            per_page=LABELS_PER_PAGE,
            error_message="GitHub issue labels API did not return a list payload",
        )
        return tuple(
            str(item["name"])
            for item in payload
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        )

    def add_labels(self, issue_number: int, labels: tuple[str, ...]) -> None:
        if not labels:
            return
        self._request(
            "POST",
            f"/repos/{self.repository}/issues/{issue_number}/labels",
            payload={"labels": list(labels)},
        )

    def remove_label(self, issue_number: int, label: str) -> None:
        self._request(
            "DELETE",
            (
                f"/repos/{self.repository}/issues/{issue_number}/labels/"
                f"{quote(label, safe='')}"
            ),
            ignore_statuses=(404,),
        )


class GitHubRepositoryLabelsClient(GitHubRepositoryApiClient):
    def __init__(self, *, repository: str, token: str) -> None:
        super().__init__(
            repository=repository,
            token=token,
            user_agent="paper-digest-sync-repository-labels",
        )

    def label_exists(self, name: str) -> bool:
        payload = self._request(
            "GET",
            f"/repos/{self.repository}/labels/{quote(name, safe='')}",
            ignore_statuses=(404,),
        )
        return payload is not None

    def create_label(self, *, name: str, color: str, description: str) -> None:
        self._request(
            "POST",
            f"/repos/{self.repository}/labels",
            payload={
                "name": name,
                "color": color,
                "description": description,
            },
        )

    def update_label(self, *, name: str, color: str, description: str) -> None:
        self._request(
            "PATCH",
            f"/repos/{self.repository}/labels/{quote(name, safe='')}",
            payload={
                "new_name": name,
                "color": color,
                "description": description,
            },
        )


class GitHubWorkflowArtifactsClient(GitHubRepositoryApiClient):
    def __init__(self, *, repository: str, token: str) -> None:
        super().__init__(
            repository=repository,
            token=token,
            user_agent="paper-digest-docs-check-pr-comment",
        )

    def list_workflow_run_artifacts(
        self,
        workflow_run_id: int,
    ) -> tuple[WorkflowArtifact, ...]:
        payload = self._paginate_list(
            f"/repos/{self.repository}/actions/runs/{workflow_run_id}/artifacts",
            per_page=WORKFLOW_ARTIFACTS_PER_PAGE,
            payload_key="artifacts",
            error_message=(
                "GitHub workflow artifacts API did not return an artifacts list"
            ),
        )
        return tuple(
            WorkflowArtifact(
                name=str(item["name"]),
                expired=bool(item.get("expired", False)),
            )
            for item in payload
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        )


class GitHubPullRequestFilesClient(GitHubRepositoryApiClient):
    def __init__(self, *, repository: str, token: str) -> None:
        super().__init__(
            repository=repository,
            token=token,
            user_agent="paper-digest-pr-hygiene",
        )

    def list_pull_request_files(self, pull_number: int) -> tuple[str, ...]:
        payload = self._paginate_list(
            f"/repos/{self.repository}/pulls/{pull_number}/files",
            per_page=PULL_FILES_PER_PAGE,
            error_message="GitHub pull files API did not return a list payload",
        )
        return tuple(
            str(item["filename"])
            for item in payload
            if isinstance(item, dict) and "filename" in item
        )
