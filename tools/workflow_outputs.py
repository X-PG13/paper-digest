from __future__ import annotations

import json
import os
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import TextIO


def write_github_outputs(output_path: Path, outputs: Mapping[str, str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            if "\n" not in value:
                handle.write(f"{key}={value}\n")
                continue

            delimiter = f"EOF_{uuid.uuid4().hex}"
            while delimiter in value:
                delimiter = f"EOF_{uuid.uuid4().hex}"
            handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def emit_workflow_outputs(
    outputs: Mapping[str, str],
    *,
    env: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
) -> None:
    current_env = os.environ if env is None else env
    output_path = current_env.get("GITHUB_OUTPUT")
    if output_path:
        write_github_outputs(Path(output_path), outputs)
        return

    output_stream = sys.stdout if stdout is None else stdout
    print(json.dumps(dict(outputs), sort_keys=True), file=output_stream)
