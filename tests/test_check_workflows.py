from __future__ import annotations

import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from tools.check_workflows import (
    ACTIONLINT_MISSING_EXIT_CODE,
    find_actionlint_binary,
    main,
)
from tools.install_actionlint import DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH


class CheckWorkflowsTests(unittest.TestCase):
    def test_find_actionlint_binary_prefers_configured_path(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.dict(
                os.environ,
                {},
                clear=True,
            ),
        ):
            root = Path(tmpdir)
            binary = root / "vendor" / "actionlint"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o755)

            with patch("tools.check_workflows.shutil.which", return_value=None):
                self.assertEqual(
                    find_actionlint_binary(root, configured_path="vendor/actionlint"),
                    binary,
                )

    def test_find_actionlint_binary_uses_repo_local_binary(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.dict(
                os.environ,
                {},
                clear=True,
            ),
        ):
            root = Path(tmpdir)
            binary = root / DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o755)

            with patch("tools.check_workflows.shutil.which", return_value=None):
                self.assertEqual(find_actionlint_binary(root), binary)

    def test_find_actionlint_binary_falls_back_to_path_lookup(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.dict(
                os.environ,
                {},
                clear=True,
            ),
        ):
            root = Path(tmpdir)

            with patch(
                "tools.check_workflows.shutil.which",
                return_value="/usr/local/bin/actionlint",
            ):
                self.assertEqual(
                    find_actionlint_binary(root),
                    Path("/usr/local/bin/actionlint"),
                )

    def test_main_reports_missing_actionlint_with_install_hint(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.dict(
                os.environ,
                {},
                clear=True,
            ),
        ):
            stderr = StringIO()

            with patch("tools.check_workflows.shutil.which", return_value=None):
                exit_code = main(root=Path(tmpdir), stderr=stderr)

            self.assertEqual(exit_code, ACTIONLINT_MISSING_EXIT_CODE)
            self.assertIn("actionlint not found", stderr.getvalue())
            self.assertIn(
                str(DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH), stderr.getvalue()
            )
            self.assertIn("make workflow-tools", stderr.getvalue())

    def test_main_runs_actionlint_from_repo_root(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.dict(
                os.environ,
                {},
                clear=True,
            ),
        ):
            root = Path(tmpdir)
            binary = root / DEFAULT_ACTIONLINT_BINARY_RELATIVE_PATH
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o755)

            with patch(
                "tools.check_workflows.subprocess.run",
                return_value=Mock(returncode=5),
            ) as mock_run:
                exit_code = main(root=root)

            self.assertEqual(exit_code, 5)
            mock_run.assert_called_once_with(
                [str(binary.resolve())],
                cwd=root.resolve(),
                check=False,
            )


if __name__ == "__main__":
    unittest.main()
