from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.docs_contracts import (
    FileTextSource,
    MarkdownSectionSource,
    TextSource,
    WorkflowSectionSource,
)
from tools.docs_findings import DocsCheckFinding, finding_for_subject
from tools.docs_parser import (
    extract_workflow_body_lines,
    find_markdown_heading_range,
    find_workflow_section_range,
    get_markdown_section_lines_with_options,
    split_template_sections,
)

WorkflowBodyParts = tuple[list[str], dict[str, list[str]]]
WorkflowBodyCache = dict[str, WorkflowBodyParts]


@dataclass(frozen=True)
class TextSourceOrigin:
    path: str
    line: int | None = None
    end_line: int | None = None


def resolve_repository_path(root: Path, relative_path: str) -> Path:
    return root / relative_path


def read_markdown_section_text(
    path: Path,
    heading: str,
    errors: list[DocsCheckFinding],
    *,
    label: str | None = None,
    visible_only: bool = True,
) -> str | None:
    lines = read_markdown_section_lines(
        path,
        heading,
        errors,
        label=label,
        visible_only=visible_only,
    )
    if lines is None:
        return None
    return "\n".join(lines)


def read_markdown_section_lines(
    path: Path,
    heading: str,
    errors: list[DocsCheckFinding],
    *,
    label: str | None = None,
    visible_only: bool = True,
) -> list[str] | None:
    lines = get_markdown_section_lines_with_options(
        path,
        heading,
        visible_only=visible_only,
    )
    if lines is None:
        errors.append(
            finding_for_subject(
                f"missing section '{heading}'",
                label or path.as_posix(),
            )
        )
        return None
    return lines


def get_workflow_body_parts(
    root: Path,
    source: WorkflowSectionSource,
    cache: WorkflowBodyCache,
) -> WorkflowBodyParts:
    return cache.setdefault(
        source.path,
        split_template_sections(
            extract_workflow_body_lines(
                resolve_repository_path(root, source.path)
            )
        ),
    )


def read_text_from_source(
    root: Path,
    source: TextSource,
    errors: list[DocsCheckFinding],
    workflow_cache: WorkflowBodyCache,
) -> str:
    if isinstance(source, FileTextSource):
        return resolve_repository_path(root, source.path).read_text(
            encoding="utf-8"
        )
    if isinstance(source, MarkdownSectionSource):
        return (
            read_markdown_section_text(
                resolve_repository_path(root, source.path),
                source.heading,
                errors,
                label=source.path,
                visible_only=source.visible_only,
            )
            or ""
        )
    intro_lines, sections = get_workflow_body_parts(root, source, workflow_cache)
    lines = intro_lines if source.section is None else sections.get(source.section, [])
    return "\n".join(lines)


def find_text_source_origin(root: Path, source: TextSource) -> TextSourceOrigin:
    if isinstance(source, FileTextSource):
        file_lines = resolve_repository_path(root, source.path).read_text(
            encoding="utf-8"
        ).splitlines()
        end_line = len(file_lines) or 1
        return TextSourceOrigin(path=source.path, line=1, end_line=end_line)
    if isinstance(source, MarkdownSectionSource):
        heading_line, heading_end_line = find_markdown_heading_range(
            resolve_repository_path(root, source.path),
            source.heading,
            visible_only=source.visible_only,
        )
        return TextSourceOrigin(
            path=source.path,
            line=heading_line,
            end_line=heading_end_line,
        )
    section_line, section_end_line = find_workflow_section_range(
        resolve_repository_path(root, source.path),
        source.section,
    )
    return TextSourceOrigin(
        path=source.path,
        line=section_line,
        end_line=section_end_line,
    )


def collect_text_by_label(
    root: Path,
    sources: Sequence[TextSource],
    errors: list[DocsCheckFinding],
) -> dict[str, str]:
    workflow_cache: WorkflowBodyCache = {}
    return {
        source.label: read_text_from_source(root, source, errors, workflow_cache)
        for source in sources
    }


def collect_text_source_origins(
    root: Path,
    sources: Sequence[TextSource],
) -> dict[str, TextSourceOrigin]:
    return {
        source.label: find_text_source_origin(root, source)
        for source in sources
    }


def get_workflow_section_lines(
    root: Path,
    source: WorkflowSectionSource,
) -> list[str]:
    intro_lines, sections = get_workflow_body_parts(root, source, {})
    if source.section is None:
        return intro_lines
    return sections.get(source.section, [])
