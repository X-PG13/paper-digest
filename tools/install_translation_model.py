"""Install the pinned offline English-to-Chinese translation model."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path
from urllib.request import Request, urlopen

from paper_digest.config import ConfigError, load_config

MODEL_URL = "https://argos-net.com/v1/translate-en_zh-1_9.argosmodel"
MODEL_SHA256 = "433e7c4f034d87fbe2353161e05f18646d7999452f801a4e1f0378522b9850ab"
ARCHIVE_PREFIX = "translate-en_zh-1_9/"
MARKER_NAME = ".model-sha256"
MODEL_FILES = (
    "README.md",
    "metadata.json",
    "sentencepiece.model",
    "model/config.json",
    "model/model.bin",
    "model/shared_vocabulary.json",
)


class ModelInstallError(RuntimeError):
    """Raised when the pinned translation model cannot be installed safely."""


def ensure_translation_model(output_dir: Path) -> bool:
    """Install the model when absent and return whether files were downloaded."""

    output_dir = output_dir.expanduser()
    marker = output_dir / MARKER_NAME
    if _is_complete_install(output_dir, marker):
        return False

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        marker.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="paper-digest-translation-",
            dir=output_dir.parent,
        ) as temporary_dir:
            archive_path = Path(temporary_dir) / "model.argosmodel"
            _download_model(archive_path)
            _verify_archive(archive_path)
            _extract_model(archive_path, output_dir)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ModelInstallError(f"failed to install translation model: {exc}") from exc

    marker.write_text(MODEL_SHA256 + "\n", encoding="ascii")
    return True


def _is_complete_install(output_dir: Path, marker: Path) -> bool:
    try:
        marker_value = marker.read_text(encoding="ascii").strip()
    except OSError:
        return False
    return marker_value == MODEL_SHA256 and all(
        (output_dir / relative_path).is_file() for relative_path in MODEL_FILES
    )


def _download_model(destination: Path) -> None:
    request = Request(
        MODEL_URL,
        headers={"User-Agent": "paper-digest-translation-model-installer"},
    )
    try:
        with urlopen(request, timeout=180) as response:
            with destination.open("wb") as output:
                shutil.copyfileobj(response, output)
    except OSError as exc:
        raise ModelInstallError(f"failed to download translation model: {exc}") from exc


def _verify_archive(archive_path: Path) -> None:
    digest = hashlib.sha256()
    with archive_path.open("rb") as archive:
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != MODEL_SHA256:
        raise ModelInstallError(
            "translation model checksum mismatch: "
            f"expected {MODEL_SHA256}, received {actual}"
        )


def _extract_model(archive_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for relative_path in MODEL_FILES:
            archive_name = ARCHIVE_PREFIX + relative_path
            try:
                source = archive.open(archive_name)
            except KeyError as exc:
                raise ModelInstallError(
                    f"translation model archive is missing {archive_name}"
                ) from exc
            destination = output_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group()
    target.add_argument(
        "--config",
        type=Path,
        help="load the model path and failure policy from a project config",
    )
    target.add_argument(
        "--output-dir",
        type=Path,
        help="directory that will contain the verified extracted model",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir or Path(
        ".paper-digest-models/argos-en-zh-1.9"
    )
    fail_on_error = True
    if args.config is not None:
        try:
            config = load_config(args.config)
        except ConfigError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        if config.translation is None:
            print("Translation is disabled; model installation skipped.")
            return 0
        output_dir = config.translation.model_path
        fail_on_error = config.translation.fail_on_error

    try:
        installed = ensure_translation_model(output_dir)
    except ModelInstallError as exc:
        label = "Error" if fail_on_error else "Warning"
        print(f"{label}: {exc}", file=sys.stderr)
        return 1 if fail_on_error else 0
    state = "installed" if installed else "already installed"
    print(f"Translation model {state}: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
