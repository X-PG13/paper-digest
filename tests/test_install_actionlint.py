from __future__ import annotations

import hashlib
import tarfile
import tempfile
import unittest
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from tools.install_actionlint import (
    DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH,
    DEFAULT_ACTIONLINT_VERSION,
    DEFAULT_ACTIONLINT_VERSION_FILE_RELATIVE_PATH,
    build_actionlint_download_url,
    extract_actionlint_binary,
    install_actionlint,
    main,
    normalize_actionlint_target,
)


def _build_actionlint_archive(binary_name: str = "actionlint") -> bytes:
    archive_bytes = BytesIO()
    payload = b"#!/bin/sh\necho actionlint\n"
    with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
        info = tarfile.TarInfo(name=f"actionlint-build/{binary_name}")
        info.size = len(payload)
        info.mode = 0o755
        archive.addfile(info, BytesIO(payload))
    return archive_bytes.getvalue()


class _FakeResponse(BytesIO):
    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class InstallActionlintTests(unittest.TestCase):
    def test_normalize_actionlint_target_accepts_supported_hosts(self) -> None:
        target = normalize_actionlint_target("Darwin", "arm64")
        self.assertEqual(target.platform, "darwin")
        self.assertEqual(target.arch, "arm64")

        target = normalize_actionlint_target("Linux", "x86_64")
        self.assertEqual(target.platform, "linux")
        self.assertEqual(target.arch, "amd64")

    def test_normalize_actionlint_target_rejects_unsupported_hosts(self) -> None:
        with self.assertRaisesRegex(ValueError, "supports only macOS/Linux"):
            normalize_actionlint_target("Windows", "AMD64")

    def test_build_actionlint_download_url_uses_release_convention(self) -> None:
        target = normalize_actionlint_target("Linux", "x86_64")
        self.assertEqual(
            build_actionlint_download_url(target),
            "https://github.com/rhysd/actionlint/releases/download/"
            f"v{DEFAULT_ACTIONLINT_VERSION}/"
            f"actionlint_{DEFAULT_ACTIONLINT_VERSION}_linux_amd64.tar.gz",
        )

    def test_extract_actionlint_binary_reads_archive_member(self) -> None:
        archive = _build_actionlint_archive()
        self.assertIn(b"echo actionlint", extract_actionlint_binary(archive))

    def test_install_actionlint_downloads_and_installs_binary(self) -> None:
        archive = _build_actionlint_archive()
        checksum = hashlib.sha256(archive).hexdigest()

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch(
                "tools.install_actionlint.SUPPORTED_ACTIONLINT_TARGETS",
                {("darwin", "arm64"): checksum},
            ),
            patch(
                "tools.install_actionlint.urlopen",
                return_value=_FakeResponse(archive),
            ),
        ):
            root = Path(tmpdir)
            result = install_actionlint(root, system="Darwin", machine="arm64")

            self.assertTrue(result.changed)
            self.assertEqual(
                result.binary_path,
                root.resolve() / DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH,
            )
            self.assertEqual(
                result.version_path,
                root.resolve() / DEFAULT_ACTIONLINT_VERSION_FILE_RELATIVE_PATH,
            )
            self.assertTrue(result.binary_path.is_file())
            self.assertTrue(result.version_path.is_file())
            self.assertEqual(
                result.version_path.read_text(encoding="utf-8").strip(),
                DEFAULT_ACTIONLINT_VERSION,
            )

    def test_install_actionlint_skips_download_when_pinned_version_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            binary = root / DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH
            version = root / DEFAULT_ACTIONLINT_VERSION_FILE_RELATIVE_PATH
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o755)
            version.write_text(f"{DEFAULT_ACTIONLINT_VERSION}\n", encoding="utf-8")

            with patch("tools.install_actionlint.urlopen") as mock_urlopen:
                result = install_actionlint(root)

            self.assertFalse(result.changed)
            mock_urlopen.assert_not_called()

    def test_install_actionlint_rejects_checksum_mismatch(self) -> None:
        archive = _build_actionlint_archive()
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch(
                "tools.install_actionlint.SUPPORTED_ACTIONLINT_TARGETS",
                {("darwin", "arm64"): "0" * 64},
            ),
            patch(
                "tools.install_actionlint.urlopen",
                return_value=_FakeResponse(archive),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                install_actionlint(Path(tmpdir), system="Darwin", machine="arm64")

    def test_main_reports_already_installed_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            binary = root / DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH
            version = root / DEFAULT_ACTIONLINT_VERSION_FILE_RELATIVE_PATH
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o755)
            version.write_text(f"{DEFAULT_ACTIONLINT_VERSION}\n", encoding="utf-8")
            stdout = StringIO()

            exit_code = main(root=root, stdout=stdout)

            self.assertEqual(exit_code, 0)
            self.assertIn("already installed", stdout.getvalue())

    def test_main_reports_install_failures(self) -> None:
        stderr = StringIO()
        with patch(
            "tools.install_actionlint.install_actionlint",
            side_effect=ValueError("boom"),
        ):
            exit_code = main(root=Path.cwd(), stderr=stderr)

        self.assertEqual(exit_code, 1)
        self.assertIn("actionlint install failed: boom", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
