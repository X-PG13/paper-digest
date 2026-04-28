from __future__ import annotations

import argparse
import hashlib
import platform
import sys
import tarfile
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TextIO
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_ACTIONLINT_VERSION = "1.7.8"
DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH = Path(".tools/actionlint/actionlint")
DEFAULT_ACTIONLINT_VERSION_FILE_RELATIVE_PATH = Path(".tools/actionlint/VERSION")
ACTIONLINT_DOWNLOAD_TIMEOUT_SECONDS = 60
ACTIONLINT_RELEASE_URL_TEMPLATE = (
    "https://github.com/rhysd/actionlint/releases/download/"
    "v{version}/actionlint_{version}_{platform}_{arch}.tar.gz"
)
SUPPORTED_ACTIONLINT_TARGETS = {
    (
        "darwin",
        "amd64",
    ): "16b85caf792b34bcc40f7437736c4347680da0a1b034353a85012debbd71a461",
    (
        "darwin",
        "arm64",
    ): "ffb1f6c429a51dc9f37af9d11f96c16bd52f54b713bf7f8bd92f7fce9fd4284a",
    (
        "linux",
        "amd64",
    ): "be92c2652ab7b6d08425428797ceabeb16e31a781c07bc388456b4e592f3e36a",
    (
        "linux",
        "arm64",
    ): "4c65dbb2d59b409cdd75d47ffa8fa32af8f0eee573ac510468dc2275c48bf07c",
}
SYSTEM_ALIASES = {
    "darwin": "darwin",
    "linux": "linux",
}
MACHINE_ALIASES = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "arm64": "arm64",
    "aarch64": "arm64",
}


@dataclass(frozen=True)
class ActionlintTarget:
    platform: str
    arch: str
    checksum: str


@dataclass(frozen=True)
class ActionlintInstallResult:
    binary_path: Path
    version_path: Path
    version: str
    changed: bool


def normalize_actionlint_target(system: str, machine: str) -> ActionlintTarget:
    normalized_system = SYSTEM_ALIASES.get(system.strip().lower())
    normalized_machine = MACHINE_ALIASES.get(machine.strip().lower())
    if normalized_system is None or normalized_machine is None:
        raise ValueError(
            "actionlint bootstrap supports only macOS/Linux amd64/arm64 hosts; "
            f"got {system}/{machine}"
        )

    checksum = SUPPORTED_ACTIONLINT_TARGETS.get(
        (normalized_system, normalized_machine)
    )
    if checksum is None:
        raise ValueError(
            "actionlint bootstrap supports only macOS/Linux amd64/arm64 hosts; "
            f"got {system}/{machine}"
        )
    return ActionlintTarget(
        platform=normalized_system,
        arch=normalized_machine,
        checksum=checksum,
    )


def build_actionlint_download_url(
    target: ActionlintTarget,
    *,
    version: str = DEFAULT_ACTIONLINT_VERSION,
) -> str:
    return ACTIONLINT_RELEASE_URL_TEMPLATE.format(
        version=version,
        platform=target.platform,
        arch=target.arch,
    )


def read_installed_actionlint_version(root: Path) -> str | None:
    version_path = root / DEFAULT_ACTIONLINT_VERSION_FILE_RELATIVE_PATH
    binary_path = root / DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH
    if not version_path.is_file() or not binary_path.is_file():
        return None
    return version_path.read_text(encoding="utf-8").strip() or None


def download_actionlint_archive(url: str) -> bytes:
    with urlopen(url, timeout=ACTIONLINT_DOWNLOAD_TIMEOUT_SECONDS) as response:
        payload = response.read()
    if isinstance(payload, bytes):
        return payload
    return bytes(payload)


def verify_actionlint_archive_checksum(
    archive_bytes: bytes,
    *,
    target: ActionlintTarget,
) -> None:
    digest = hashlib.sha256(archive_bytes).hexdigest()
    if digest != target.checksum:
        raise ValueError(
            "actionlint archive checksum mismatch: "
            f"expected {target.checksum}, got {digest}"
        )


def extract_actionlint_binary(archive_bytes: bytes) -> bytes:
    with tarfile.open(fileobj=BytesIO(archive_bytes), mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile() and Path(member.name).name == "actionlint":
                extracted = archive.extractfile(member)
                if extracted is None:
                    break
                return extracted.read()
    raise ValueError("actionlint archive did not contain an actionlint binary")


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_bytes(data)
    tmp_path.replace(path)


def install_actionlint(
    root: Path,
    *,
    force: bool = False,
    system: str | None = None,
    machine: str | None = None,
) -> ActionlintInstallResult:
    repo_root = root.resolve()
    binary_path = repo_root / DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH
    version_path = repo_root / DEFAULT_ACTIONLINT_VERSION_FILE_RELATIVE_PATH
    installed_version = read_installed_actionlint_version(repo_root)

    if (
        not force
        and installed_version == DEFAULT_ACTIONLINT_VERSION
        and binary_path.is_file()
    ):
        return ActionlintInstallResult(
            binary_path=binary_path,
            version_path=version_path,
            version=DEFAULT_ACTIONLINT_VERSION,
            changed=False,
        )

    target = normalize_actionlint_target(
        platform.system() if system is None else system,
        platform.machine() if machine is None else machine,
    )
    url = build_actionlint_download_url(target)
    archive_bytes = download_actionlint_archive(url)
    verify_actionlint_archive_checksum(archive_bytes, target=target)
    binary_bytes = extract_actionlint_binary(archive_bytes)

    _write_atomic(binary_path, binary_bytes)
    binary_path.chmod(0o755)
    _write_atomic(
        version_path,
        f"{DEFAULT_ACTIONLINT_VERSION}\n".encode(),
    )

    return ActionlintInstallResult(
        binary_path=binary_path,
        version_path=version_path,
        version=DEFAULT_ACTIONLINT_VERSION,
        changed=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install the pinned actionlint binary into .tools/actionlint for "
            "local workflow linting."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reinstall the pinned actionlint version even if it is already present.",
    )
    return parser


def main(
    *,
    root: Path | None = None,
    force: bool = False,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr
    repo_root = Path(__file__).resolve().parents[1] if root is None else root.resolve()

    try:
        result = install_actionlint(repo_root, force=force)
    except (OSError, URLError, ValueError, tarfile.TarError) as exc:
        print(f"actionlint install failed: {exc}", file=error_stream)
        return 1

    binary_display = result.binary_path.relative_to(repo_root)
    if result.changed:
        print(
            f"Installed actionlint {result.version} at {binary_display}.",
            file=output_stream,
        )
    else:
        print(
            f"actionlint {result.version} is already installed at {binary_display}.",
            file=output_stream,
        )
    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return main(force=args.force)


if __name__ == "__main__":
    raise SystemExit(cli())
