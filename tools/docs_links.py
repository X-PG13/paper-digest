from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

from tools.docs_findings import DocsCheckFinding
from tools.docs_parser import (
    LINK_RE,
    TEXT_REFERENCE_RE,
    collect_markdown_anchors,
    extract_markdown_links,
    extract_repository_references,
    iter_github_metadata_files,
    iter_markdown_files,
    parse_link_target,
    to_repository_relative_path,
)


def check_anchor_reference(
    root: Path,
    source_display: Path,
    line_number: int,
    target_path: Path,
    anchor: str,
    anchor_cache: dict[Path, set[str]],
    errors: list[DocsCheckFinding],
) -> None:
    if not anchor or target_path.suffix.lower() != ".md":
        return

    anchors = anchor_cache.setdefault(
        target_path,
        collect_markdown_anchors(target_path),
    )
    if anchor not in anchors:
        errors.append(
            DocsCheckFinding(
                message=(
                    f"missing anchor '{anchor}' in {target_path.relative_to(root)}"
                ),
                path=source_display.as_posix(),
                line=line_number,
            )
        )


def is_external_target(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme in {"http", "https", "mailto", "tel"}


def resolve_target(root: Path, source: Path, target: str) -> tuple[Path, str]:
    path_part, anchor = urldefrag(target)
    if not path_part:
        resolved_path = source
    elif path_part.startswith("/"):
        resolved_path = (root / unquote(path_part.lstrip("/"))).resolve()
    else:
        resolved_path = (source.parent / unquote(path_part)).resolve()
    return resolved_path, anchor


def resolve_repository_reference(root: Path, target: str) -> tuple[Path, str]:
    normalized_target = target[2:] if target.startswith("./") else target
    path_part, anchor = urldefrag(normalized_target)
    return (root / unquote(path_part)).resolve(), anchor


def extract_markdown_link_targets_from_lines(
    root: Path,
    source: Path,
    lines: list[str],
) -> set[str]:
    root = root.resolve()
    source = source.resolve()
    targets: set[str] = set()
    for line in lines:
        for match in LINK_RE.finditer(line):
            target = parse_link_target(match.group(1))
            if target is None or is_external_target(target):
                continue
            target_path, _ = resolve_target(root, source, target)
            targets.add(to_repository_relative_path(root, target_path))
    return targets


def extract_repository_reference_targets_from_lines(lines: list[str]) -> set[str]:
    targets: set[str] = set()
    for line in lines:
        seen_targets: set[str] = set()
        for match in TEXT_REFERENCE_RE.finditer(line):
            target = match.group("target")
            if target in seen_targets:
                continue
            seen_targets.add(target)
            normalized_target = target[2:] if target.startswith("./") else target
            targets.add(urldefrag(normalized_target)[0])
    return targets


def check_markdown_links(
    root: Path,
    files: list[Path] | None = None,
) -> list[DocsCheckFinding]:
    root = root.resolve()
    files = (
        iter_markdown_files(root)
        if files is None
        else sorted(path.resolve() for path in files)
    )
    anchor_cache: dict[Path, set[str]] = {}
    errors: list[DocsCheckFinding] = []

    for source in files:
        source_display = source.relative_to(root)
        for link in extract_markdown_links(source):
            if is_external_target(link.target):
                continue

            target_path, anchor = resolve_target(root, link.source, link.target)
            try:
                target_path.relative_to(root)
            except ValueError:
                errors.append(
                    DocsCheckFinding(
                        message=f"link escapes repository root: {link.target}",
                        path=source_display.as_posix(),
                        line=link.line_number,
                    )
                )
                continue

            if not target_path.exists():
                errors.append(
                    DocsCheckFinding(
                        message=f"missing target: {link.target}",
                        path=source_display.as_posix(),
                        line=link.line_number,
                    )
                )
                continue

            if target_path.is_dir():
                errors.append(
                    DocsCheckFinding(
                        message=f"link points to a directory: {link.target}",
                        path=source_display.as_posix(),
                        line=link.line_number,
                    )
                )
                continue

            check_anchor_reference(
                root,
                source_display,
                link.line_number,
                target_path,
                anchor,
                anchor_cache,
                errors,
            )

    return errors


def check_repository_references(
    root: Path,
    files: list[Path] | None = None,
) -> list[DocsCheckFinding]:
    root = root.resolve()
    files = (
        iter_github_metadata_files(root)
        if files is None
        else sorted(path.resolve() for path in files)
    )
    anchor_cache: dict[Path, set[str]] = {}
    errors: list[DocsCheckFinding] = []

    for source in files:
        source_display = source.relative_to(root)
        for reference in extract_repository_references(source):
            target_path, anchor = resolve_repository_reference(root, reference.target)
            try:
                target_path.relative_to(root)
            except ValueError:
                errors.append(
                    DocsCheckFinding(
                        message=(
                            "reference escapes repository root: "
                            f"{reference.target}"
                        ),
                        path=source_display.as_posix(),
                        line=reference.line_number,
                    )
                )
                continue

            if not target_path.exists():
                errors.append(
                    DocsCheckFinding(
                        message=f"missing repository file: {reference.target}",
                        path=source_display.as_posix(),
                        line=reference.line_number,
                    )
                )
                continue

            if target_path.is_dir():
                continue

            check_anchor_reference(
                root,
                source_display,
                reference.line_number,
                target_path,
                anchor,
                anchor_cache,
                errors,
            )

    return errors
