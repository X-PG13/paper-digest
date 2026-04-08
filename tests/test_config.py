from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_digest.config import ConfigError, load_config


class LoadConfigTests(unittest.TestCase):
    def test_load_config_resolves_output_relative_to_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "configs" / "digest.toml"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "Asia/Shanghai"
                    lookback_hours = 48
                    output_dir = "../artifacts"
                    request_delay_seconds = 1.5

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]
                    keywords = ["agent"]
                    exclude_keywords = ["survey"]
                    max_results = 50
                    max_items = 5
                    """
                ).strip(),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.timezone, "Asia/Shanghai")
        self.assertEqual(config.lookback_hours, 48)
        self.assertEqual(
            config.output_dir,
            (config_path.parent / "../artifacts").resolve(),
        )
        self.assertEqual(config.request_delay_seconds, 1.5)
        self.assertEqual(config.feeds[0].name, "LLM")

    def test_invalid_timezone_raises_config_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [app]
                    timezone = "Mars/Olympus_Mons"

                    [[feeds]]
                    name = "LLM"
                    categories = ["cs.AI"]
                    """
                ).strip(),
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError):
                load_config(config_path)
