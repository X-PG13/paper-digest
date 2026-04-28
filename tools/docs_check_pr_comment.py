from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
from urllib.error import HTTPError, URLError

from tools.github_api import DEFAULT_GITHUB_TOKEN_ENV
from tools.github_resources import WorkflowArtifact
from tools.github_services import GitHubWorkflowArtifactsService
from tools.render_docs_report import load_docs_check_report
from tools.workflow_outputs import emit_workflow_outputs

DEFAULT_ARTIFACT_NAME = "docs-check-report"
DEFAULT_GITHUB_EVENT_PATH_ENV = "GITHUB_EVENT_PATH"


@dataclass(frozen=True)
class DocsCheckCommentContext:
    pr_number: int
    workflow_run_id: int
    artifact_found: bool


@dataclass(frozen=True)
class DocsCheckCommentDecision:
    mode: str
    marker: str
    comment_body: str | None


def resolve_docs_check_comment_context(
    event_payload: object,
    artifacts: Sequence[WorkflowArtifact],
    *,
    artifact_name: str = DEFAULT_ARTIFACT_NAME,
) -> DocsCheckCommentContext:
    if not isinstance(event_payload, dict):
        raise ValueError("workflow_run event payload must be a JSON object")
    workflow_run = event_payload.get("workflow_run")
    if not isinstance(workflow_run, dict):
        raise ValueError("workflow_run event payload is missing workflow_run")
    workflow_run_id = workflow_run.get("id")
    if not isinstance(workflow_run_id, int):
        raise ValueError("workflow_run event payload is missing workflow_run.id")
    pull_requests = workflow_run.get("pull_requests")
    if not isinstance(pull_requests, list) or not pull_requests:
        raise ValueError(
            f"workflow_run {workflow_run_id} came from pull_request but did not "
            "include an attached PR"
        )
    first_pull_request = pull_requests[0]
    if not isinstance(first_pull_request, dict) or not isinstance(
        first_pull_request.get("number"), int
    ):
        raise ValueError(
            f"workflow_run {workflow_run_id} is missing pull_requests[0].number"
        )

    artifact_found = any(
        artifact.name == artifact_name and not artifact.expired
        for artifact in artifacts
    )
    return DocsCheckCommentContext(
        pr_number=first_pull_request["number"],
        workflow_run_id=workflow_run_id,
        artifact_found=artifact_found,
    )


def decide_docs_check_comment_action(
    report_file: Path,
    comment_file: Path,
) -> DocsCheckCommentDecision:
    report = load_docs_check_report(report_file)
    comment_body = comment_file.read_text(encoding="utf-8").strip()
    marker = comment_body.splitlines()[0].strip() if comment_body else ""

    if not marker.startswith("<!--"):
        raise ValueError(
            f"docs-check PR comment marker is missing from {comment_file}"
        )

    if report.status == "passed":
        return DocsCheckCommentDecision(
            mode="delete",
            marker=marker,
            comment_body=None,
        )

    if marker not in comment_body:
        raise ValueError(
            f"docs-check PR comment body did not preserve marker {marker}"
        )

    return DocsCheckCommentDecision(
        mode="upsert",
        marker=marker,
        comment_body=comment_body,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve and decide trusted docs-check PR comment workflow state."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_parser = subparsers.add_parser(
        "resolve-context",
        help="Resolve the PR number and docs-check artifact state for a workflow_run.",
    )
    resolve_parser.add_argument(
        "--repo",
        required=True,
        help="Repository in owner/name form.",
    )
    resolve_parser.add_argument(
        "--event-path-env",
        default=DEFAULT_GITHUB_EVENT_PATH_ENV,
        help=(
            "Environment variable with the workflow_run event payload path. "
            f"Defaults to {DEFAULT_GITHUB_EVENT_PATH_ENV}."
        ),
    )
    resolve_parser.add_argument(
        "--token-env",
        default=DEFAULT_GITHUB_TOKEN_ENV,
        help=(
            "Environment variable with the GitHub token. Defaults to "
            f"{DEFAULT_GITHUB_TOKEN_ENV}."
        ),
    )
    resolve_parser.add_argument(
        "--artifact-name",
        default=DEFAULT_ARTIFACT_NAME,
        help=f"Artifact name to look for. Defaults to {DEFAULT_ARTIFACT_NAME}.",
    )

    decide_parser = subparsers.add_parser(
        "decide-comment",
        help="Decide whether to upsert or delete the trusted docs-check PR comment.",
    )
    decide_parser.add_argument(
        "--report-file",
        required=True,
        type=Path,
        help="Path to docs-check-report.json.",
    )
    decide_parser.add_argument(
        "--comment-file",
        required=True,
        type=Path,
        help="Path to the rendered docs-check PR comment Markdown file.",
    )
    return parser


def main_resolve_context(
    *,
    repo: str,
    event_path_env: str = DEFAULT_GITHUB_EVENT_PATH_ENV,
    token_env: str = DEFAULT_GITHUB_TOKEN_ENV,
    artifact_name: str = DEFAULT_ARTIFACT_NAME,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    env: dict[str, str] | None = None,
) -> int:
    current_env = os.environ if env is None else env
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr

    token = current_env.get(token_env, "").strip()
    if not token:
        print(
            (
                "docs-check PR comment context failed: missing GitHub token in "
                f"{token_env}"
            ),
            file=error_stream,
        )
        return 1

    event_path_value = current_env.get(event_path_env, "").strip()
    if not event_path_value:
        print(
            "docs-check PR comment context failed: missing workflow_run event "
            f"payload path in {event_path_env}",
            file=error_stream,
        )
        return 1

    try:
        event_payload = json.loads(Path(event_path_value).read_text(encoding="utf-8"))
        workflow_run = event_payload["workflow_run"]
        artifacts = GitHubWorkflowArtifactsService(
            repository=repo,
            token=token,
        ).list_artifacts(int(workflow_run["id"]))
        context = resolve_docs_check_comment_context(
            event_payload,
            artifacts,
            artifact_name=artifact_name,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        HTTPError,
        URLError,
        json.JSONDecodeError,
    ) as exc:
        print(f"docs-check PR comment context failed: {exc}", file=error_stream)
        return 1

    emit_workflow_outputs(
        {
            "pr-number": str(context.pr_number),
            "workflow-run-id": str(context.workflow_run_id),
            "artifact-found": "true" if context.artifact_found else "false",
        },
        env=current_env,
        stdout=output_stream,
    )
    return 0


def main_decide_comment(
    *,
    report_file: Path,
    comment_file: Path,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    env: dict[str, str] | None = None,
) -> int:
    current_env = os.environ if env is None else env
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr

    try:
        decision = decide_docs_check_comment_action(report_file, comment_file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"docs-check PR comment decision failed: {exc}", file=error_stream)
        return 1

    outputs = {
        "mode": decision.mode,
        "marker": decision.marker,
    }
    if decision.comment_body is not None:
        outputs["comment-body"] = decision.comment_body
    emit_workflow_outputs(outputs, env=current_env, stdout=output_stream)
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "resolve-context":
        return main_resolve_context(
            repo=args.repo,
            event_path_env=args.event_path_env,
            token_env=args.token_env,
            artifact_name=args.artifact_name,
        )
    return main_decide_comment(
        report_file=args.report_file,
        comment_file=args.comment_file,
    )


if __name__ == "__main__":
    raise SystemExit(cli())
