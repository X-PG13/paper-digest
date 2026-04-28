from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from tools.docs_pipeline import (
    DOCS_CHECK_COMMAND,
    DocsCheckCommand,
    format_docs_check_json_report,
    format_docs_check_markdown_report,
    run_docs_check_command,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run repository-local documentation consistency checks."
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        dest="output_format",
        help="Choose text, machine-readable JSON, or Markdown summary output.",
    )
    parser.add_argument(
        "--json-report-file",
        type=Path,
        help="Write the machine-readable JSON report to a file.",
    )
    parser.add_argument(
        "--markdown-report-file",
        type=Path,
        help="Write the Markdown summary report to a file.",
    )
    return parser


def main(
    command: DocsCheckCommand = DOCS_CHECK_COMMAND,
    *,
    output_format: str = "text",
    json_report_file: Path | None = None,
    markdown_report_file: Path | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr
    result = run_docs_check_command(command)
    if json_report_file is not None:
        json_report_file.parent.mkdir(parents=True, exist_ok=True)
        json_report_file.write_text(
            f"{format_docs_check_json_report(result)}\n",
            encoding="utf-8",
        )
    if markdown_report_file is not None:
        markdown_report_file.parent.mkdir(parents=True, exist_ok=True)
        markdown_report_file.write_text(
            f"{format_docs_check_markdown_report(result)}\n",
            encoding="utf-8",
        )
    if output_format == "json":
        print(format_docs_check_json_report(result), file=output_stream)
        return result.exit_code
    if output_format == "markdown":
        print(format_docs_check_markdown_report(result), file=output_stream)
        return result.exit_code
    for line in result.stdout_lines:
        print(line, file=output_stream)
    for line in result.stderr_lines:
        print(line, file=error_stream)
    return result.exit_code


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return main(
        output_format=args.output_format,
        json_report_file=args.json_report_file,
        markdown_report_file=args.markdown_report_file,
    )


if __name__ == "__main__":
    raise SystemExit(cli())
