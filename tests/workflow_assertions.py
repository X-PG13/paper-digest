from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_workflow_lines(relative_path: str) -> list[str]:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8").splitlines()


def indentation_width(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def extract_indented_block(lines: list[str], header: str) -> str:
    try:
        start = lines.index(header)
    except ValueError as error:
        raise AssertionError(f"Missing workflow block header: {header}") from error

    header_indent = indentation_width(header)
    block = [header]
    for line in lines[start + 1 :]:
        if line.strip() and indentation_width(line) <= header_indent:
            break
        block.append(line)

    return "\n".join(block)


def extract_step_block(lines: list[str], step_name: str) -> str:
    header = f"      - name: {step_name}"
    try:
        start = lines.index(header)
    except ValueError as error:
        raise AssertionError(f"Missing workflow step: {step_name}") from error

    block = [header]
    for line in lines[start + 1 :]:
        if line.startswith("      - name: "):
            break
        block.append(line)

    return "\n".join(block)
