from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DocsCheckFinding:
    message: str
    severity: str = "error"
    path: str | None = None
    line: int | None = None
    end_line: int | None = None


REPOSITORY_PATH_RE = re.compile(
    r"(?P<path>(?:[A-Za-z0-9_.-]+/)*(?:[A-Za-z0-9_.-]+\.(?:md|ya?ml|json|toml|py)|CODEOWNERS))"
)


def infer_repository_path(subject: str) -> str | None:
    direct_target = subject.strip().split("#", 1)[0]
    direct_match = REPOSITORY_PATH_RE.fullmatch(direct_target)
    if direct_match is not None:
        return direct_match.group("path")

    match = REPOSITORY_PATH_RE.search(subject)
    if match is not None:
        return match.group("path")
    return None


def finding_for_subject(
    message: str,
    subject: str,
    *,
    severity: str = "error",
    line: int | None = None,
    end_line: int | None = None,
) -> DocsCheckFinding:
    return DocsCheckFinding(
        message=message,
        severity=severity,
        path=infer_repository_path(subject),
        line=line,
        end_line=end_line,
    )
