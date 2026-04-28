from __future__ import annotations

import runpy
import unittest
from unittest.mock import patch


class MainModuleTests(unittest.TestCase):
    @patch("paper_digest.cli.main", return_value=7)
    def test_package_main_exits_with_cli_status(self, mock_main) -> None:
        with self.assertRaises(SystemExit) as exit_info:
            runpy.run_module("paper_digest", run_name="__main__")

        self.assertEqual(exit_info.exception.code, 7)
        mock_main.assert_called_once_with()
