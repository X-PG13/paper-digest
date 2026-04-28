from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from tools.docs_contracts import (
    DOCS_CHECKER_CONFIG,
    build_repository_reference_pattern,
)

FENCE_RE = re.compile(r"^(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?\s*$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
LINK_TARGET_RE = re.compile(r'\s*(<[^>]+>|[^ )]+)(?:\s+"[^"]*")?\s*$')
TEXT_REFERENCE_RE = re.compile(
    build_repository_reference_pattern(DOCS_CHECKER_CONFIG)
)
FIELD_BULLET_RE = re.compile(r"^- (?P<label>[^:]+):(?:\s*(?P<value>.*))?$")
CHECKLIST_ITEM_RE = re.compile(r"^- \[ \]\s+(?P<text>.+)$")
PLAIN_BULLET_RE = re.compile(r"^- (?!\[ \])(?P<text>.+)$")
ISSUE_FORM_ITEM_RE = re.compile(r"^(?P<indent>\s*)-\s+type:\s*(?P<type>.+?)\s*$")
ISSUE_FORM_SCALAR_RE = re.compile(r"^\s*(?P<key>id|label):\s*(?P<value>.+?)\s*$")
ISSUE_FORM_BLOCK_RE = re.compile(
    r"^(?P<indent>\s*)(?P<key>value|placeholder):\s*\|\s*$"
)
WORKFLOW_BODY_START_RE = re.compile(r"\bconst\s+body\s*=\s*\[")
WORKFLOW_BODY_END_RE = re.compile(r"^\s*\](?:\.join\([^)]*\))?;?\s*$")
WORKFLOW_BODY_ITEM_RE = re.compile(
    r"""^\s*(?P<quote>["'`])(?P<content>.*)(?P=quote),?\s*$"""
)


@dataclass(frozen=True)
class MarkdownLink:
    source: Path
    line_number: int
    target: str


@dataclass(frozen=True)
class RepositoryReference:
    source: Path
    line_number: int
    target: str


@dataclass(frozen=True)
class IssueFormField:
    field_type: str
    field_id: str | None
    label: str | None
    line_number: int
    end_line: int
    value_lines: tuple[str, ...]
    placeholder_lines: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowBodyEntry:
    line_number: int
    content: str


def to_repository_relative_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.md"):
        relative_parts = path.relative_to(root).parts
        if any(part in DOCS_CHECKER_CONFIG.skip_dirs for part in relative_parts):
            continue
        files.append(path)
    return sorted(files)


def iter_github_metadata_files(root: Path) -> list[Path]:
    github_dir = root / DOCS_CHECKER_CONFIG.github_metadata_root
    if not github_dir.exists():
        return []

    files: list[Path] = []
    for suffix in DOCS_CHECKER_CONFIG.github_metadata_globs:
        files.extend(github_dir.rglob(suffix))
    return sorted(set(path.resolve() for path in files))


def iter_visible_lines(path: Path) -> list[tuple[int, str]]:
    visible_lines: list[tuple[int, str]] = []
    in_fence = False
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        visible_lines.append((line_number, line))
    return visible_lines


def iter_markdown_lines(
    path: Path,
    *,
    visible_only: bool = True,
) -> list[tuple[int, str]]:
    if visible_only:
        return iter_visible_lines(path)

    lines = path.read_text(encoding="utf-8").splitlines()
    return list(enumerate(lines, 1))


def parse_link_target(raw_target: str) -> str | None:
    match = LINK_TARGET_RE.fullmatch(raw_target)
    if match is None:
        return None
    target = match.group(1)
    if target.startswith("<") and target.endswith(">"):
        return target[1:-1]
    return target


def extract_markdown_links(path: Path) -> list[MarkdownLink]:
    links: list[MarkdownLink] = []
    for line_number, line in iter_visible_lines(path):
        for match in LINK_RE.finditer(line):
            target = parse_link_target(match.group(1))
            if target is None:
                continue
            links.append(MarkdownLink(path, line_number, target))
    return links


def extract_repository_references(path: Path) -> list[RepositoryReference]:
    references: list[RepositoryReference] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, 1):
        seen_targets: set[str] = set()
        for match in TEXT_REFERENCE_RE.finditer(line):
            target = match.group("target")
            if target in seen_targets:
                continue
            seen_targets.add(target)
            references.append(RepositoryReference(path, line_number, target))
    return references


def strip_yaml_scalar_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def count_leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def extract_issue_form_fields(path: Path) -> list[IssueFormField]:
    fields: list[IssueFormField] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0

    while index < len(lines):
        item_match = ISSUE_FORM_ITEM_RE.match(lines[index])
        if item_match is None:
            index += 1
            continue

        item_line_number = index + 1
        item_indent = len(item_match.group("indent"))
        field_type = strip_yaml_scalar_quotes(item_match.group("type").strip())
        field_id: str | None = None
        label: str | None = None
        value_lines: tuple[str, ...] = ()
        placeholder_lines: tuple[str, ...] = ()
        index += 1

        while index < len(lines):
            next_item_match = ISSUE_FORM_ITEM_RE.match(lines[index])
            if (
                next_item_match is not None
                and len(next_item_match.group("indent")) == item_indent
            ):
                break

            scalar_match = ISSUE_FORM_SCALAR_RE.match(lines[index])
            if scalar_match is not None:
                key = scalar_match.group("key")
                value = strip_yaml_scalar_quotes(scalar_match.group("value").strip())
                if key == "id":
                    field_id = value
                else:
                    label = value
                index += 1
                continue

            block_match = ISSUE_FORM_BLOCK_RE.match(lines[index])
            if block_match is not None:
                block_key = block_match.group("key")
                block_indent = len(block_match.group("indent"))
                block_lines: list[str] = []
                index += 1
                while index < len(lines):
                    next_line = lines[index]
                    next_indent = count_leading_spaces(next_line)
                    if next_line.strip() and next_indent <= block_indent:
                        break
                    if next_line.strip():
                        trim_width = min(len(next_line), block_indent + 2)
                        block_lines.append(next_line[trim_width:])
                    else:
                        block_lines.append("")
                    index += 1
                if block_key == "value":
                    value_lines = tuple(block_lines)
                else:
                    placeholder_lines = tuple(block_lines)
                continue

            index += 1

        end_line = len(lines) if index >= len(lines) else index

        fields.append(
            IssueFormField(
                field_type=field_type,
                field_id=field_id,
                label=label,
                line_number=item_line_number,
                end_line=end_line,
                value_lines=value_lines,
                placeholder_lines=placeholder_lines,
            )
        )

    return fields


def find_issue_form_field_by_id(
    fields: list[IssueFormField],
    field_id: str,
) -> IssueFormField | None:
    for field in fields:
        if field.field_id == field_id:
            return field
    return None


def extract_workflow_body_lines(path: Path) -> list[str]:
    return [entry.content for entry in extract_workflow_body_entries(path)]


def extract_workflow_body_entries(path: Path) -> list[WorkflowBodyEntry]:
    body_lines: list[WorkflowBodyEntry] = []
    in_body = False

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        if not in_body:
            if WORKFLOW_BODY_START_RE.search(line):
                in_body = True
            continue

        if WORKFLOW_BODY_END_RE.match(line):
            break

        item_match = WORKFLOW_BODY_ITEM_RE.match(line)
        if item_match is None:
            continue
        body_lines.append(
            WorkflowBodyEntry(
                line_number=line_number,
                content=item_match.group("content"),
            )
        )

    return body_lines


def split_template_sections(
    lines: list[str],
) -> tuple[list[str], dict[str, list[str]]]:
    intro_entries, section_entries = split_template_section_entries(
        [WorkflowBodyEntry(line_number=0, content=line) for line in lines]
    )
    return (
        [entry.content for entry in intro_entries],
        {
            section: [entry.content for entry in entries]
            for section, entries in section_entries.items()
        },
    )


def split_template_section_entries(
    entries: list[WorkflowBodyEntry],
) -> tuple[list[WorkflowBodyEntry], dict[str, list[WorkflowBodyEntry]]]:
    intro_lines: list[WorkflowBodyEntry] = []
    sections: dict[str, list[WorkflowBodyEntry]] = {}
    current_section: str | None = None

    for entry in entries:
        if entry.content.startswith("## "):
            current_section = entry.content[3:].strip()
            sections[current_section] = []
            continue
        if current_section is None:
            intro_lines.append(entry)
        else:
            sections[current_section].append(entry)

    return intro_lines, sections


def extract_first_fenced_block_lines(lines: list[str]) -> list[str] | None:
    block_lines: list[str] = []
    in_fence = False

    for line in lines:
        if FENCE_RE.match(line.strip()):
            if in_fence:
                return block_lines
            in_fence = True
            continue
        if in_fence:
            block_lines.append(line)

    return None


def parse_markdown_items(
    lines: list[str],
    item_re: re.Pattern[str],
) -> list[str]:
    items: list[str] = []
    current_parts: list[str] = []

    def flush_current() -> None:
        if current_parts:
            items.append(" ".join(part for part in current_parts if part).strip())
            current_parts.clear()

    for line in lines:
        stripped = line.strip()
        match = item_re.match(stripped)
        if match is not None:
            flush_current()
            current_parts.append(match.group("text").strip())
            continue
        if current_parts and stripped and not stripped.startswith("## "):
            current_parts.append(stripped)

    flush_current()
    return items


def parse_checklist_items(lines: list[str]) -> list[str]:
    return parse_markdown_items(lines, CHECKLIST_ITEM_RE)


def parse_plain_bullet_items(lines: list[str]) -> list[str]:
    return parse_markdown_items(lines, PLAIN_BULLET_RE)


def parse_bullet_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_label: str | None = None
    current_parts: list[str] = []

    def flush_current() -> None:
        nonlocal current_label
        if current_label is not None:
            fields[current_label] = " ".join(
                part for part in current_parts if part
            ).strip()
        current_label = None
        current_parts.clear()

    for line in lines:
        stripped = line.strip()
        match = FIELD_BULLET_RE.match(stripped)
        if match is not None:
            flush_current()
            current_label = match.group("label").strip()
            current_parts.append((match.group("value") or "").strip())
            continue
        if current_label is not None and stripped and not stripped.startswith("## "):
            current_parts.append(stripped)

    flush_current()
    return fields


def get_markdown_section_lines(path: Path, heading: str) -> list[str] | None:
    return get_markdown_section_lines_with_options(path, heading)


def get_markdown_section_lines_with_options(
    path: Path,
    heading: str,
    *,
    visible_only: bool = True,
) -> list[str] | None:
    section_lines: list[str] = []
    active_level: int | None = None
    in_fence = False

    for _, line in iter_markdown_lines(path, visible_only=visible_only):
        if not visible_only and FENCE_RE.match(line.strip()):
            if active_level is not None:
                section_lines.append(line)
            in_fence = not in_fence
            continue

        match = None if in_fence else HEADING_RE.match(line)
        if match is not None:
            level = len(match.group(1))
            title = match.group(2).strip()
            if active_level is not None and level <= active_level:
                break
            if active_level is None and title == heading:
                active_level = level
                continue
        if active_level is not None:
            section_lines.append(line)

    if active_level is None:
        return None
    return section_lines


def find_markdown_heading_line(
    path: Path,
    heading: str,
    *,
    visible_only: bool = True,
) -> int | None:
    line, _ = find_markdown_heading_range(
        path,
        heading,
        visible_only=visible_only,
    )
    return line


def find_markdown_heading_range(
    path: Path,
    heading: str,
    *,
    visible_only: bool = True,
) -> tuple[int | None, int | None]:
    in_fence = False
    heading_line: int | None = None
    end_line: int | None = None
    active_level: int | None = None
    for line_number, line in iter_markdown_lines(path, visible_only=visible_only):
        if not visible_only and FENCE_RE.match(line.strip()):
            if heading_line is not None:
                end_line = line_number
            in_fence = not in_fence
            continue
        if in_fence:
            if heading_line is not None:
                end_line = line_number
            continue
        match = HEADING_RE.match(line)
        if match is None:
            if heading_line is not None:
                end_line = line_number
            continue

        level = len(match.group(1))
        title = match.group(2).strip()
        if (
            heading_line is not None
            and active_level is not None
            and level <= active_level
        ):
            return heading_line, end_line or heading_line
        if heading_line is None and title == heading:
            heading_line = line_number
            end_line = line_number
            active_level = level

    if heading_line is None:
        return None, None
    return heading_line, end_line or heading_line


def find_workflow_section_line(path: Path, section: str | None) -> int | None:
    line, _ = find_workflow_section_range(path, section)
    return line


def find_workflow_section_range(
    path: Path,
    section: str | None,
) -> tuple[int | None, int | None]:
    entries = extract_workflow_body_entries(path)
    if not entries:
        return None, None
    intro_entries, section_entries = split_template_section_entries(entries)
    if section is None:
        target_entries = intro_entries or [entries[0]]
        return target_entries[0].line_number, target_entries[-1].line_number
    heading = f"## {section}"
    for entry in entries:
        if entry.content == heading:
            section_entries_for_heading = section_entries.get(section, [])
            end_line = (
                section_entries_for_heading[-1].line_number
                if section_entries_for_heading
                else entry.line_number
            )
            return entry.line_number, end_line
    return None, None


def normalize_anchor(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.strip().lower()
    ascii_text = re.sub(r"[`*_~]", "", ascii_text)
    ascii_text = re.sub(r"[^\w\s-]", "", ascii_text)
    ascii_text = re.sub(r"\s+", "-", ascii_text)
    ascii_text = re.sub(r"-+", "-", ascii_text)
    return ascii_text.strip("-")


def collect_markdown_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    seen: dict[str, int] = defaultdict(int)
    for _, line in iter_visible_lines(path):
        match = HEADING_RE.match(line)
        if match is None:
            continue
        base_anchor = normalize_anchor(match.group(2))
        if not base_anchor:
            continue
        suffix = seen[base_anchor]
        seen[base_anchor] += 1
        anchor = base_anchor if suffix == 0 else f"{base_anchor}-{suffix}"
        anchors.add(anchor)
    return anchors
