from __future__ import annotations

import hashlib
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tools.install_translation_model import (
    ARCHIVE_PREFIX,
    MODEL_FILES,
    ModelInstallError,
    ensure_translation_model,
    main,
)


class FakeResponse(BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def build_archive(*, omit: str | None = None) -> bytes:
    payload = BytesIO()
    with zipfile.ZipFile(payload, mode="w") as archive:
        for relative_path in MODEL_FILES:
            if relative_path != omit:
                archive.writestr(ARCHIVE_PREFIX + relative_path, relative_path)
    return payload.getvalue()


class InstallTranslationModelTests(unittest.TestCase):
    def test_installs_verified_model_and_reuses_complete_install(self) -> None:
        archive = build_archive()
        checksum = hashlib.sha256(archive).hexdigest()
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "model"
            with (
                patch("tools.install_translation_model.MODEL_SHA256", checksum),
                patch(
                    "tools.install_translation_model.urlopen",
                    return_value=FakeResponse(archive),
                ) as urlopen,
            ):
                self.assertTrue(ensure_translation_model(output_dir))
                self.assertFalse(ensure_translation_model(output_dir))

            self.assertEqual(urlopen.call_count, 1)
            self.assertTrue((output_dir / "model" / "model.bin").is_file())

    def test_rejects_checksum_mismatch_and_incomplete_archive(self) -> None:
        archive = build_archive()
        with TemporaryDirectory() as temp_dir:
            with patch(
                "tools.install_translation_model.urlopen",
                return_value=FakeResponse(archive),
            ):
                with self.assertRaisesRegex(ModelInstallError, "checksum mismatch"):
                    ensure_translation_model(Path(temp_dir) / "bad-checksum")

        incomplete = build_archive(omit="model/model.bin")
        checksum = hashlib.sha256(incomplete).hexdigest()
        with TemporaryDirectory() as temp_dir:
            with (
                patch("tools.install_translation_model.MODEL_SHA256", checksum),
                patch(
                    "tools.install_translation_model.urlopen",
                    return_value=FakeResponse(incomplete),
                ),
            ):
                with self.assertRaisesRegex(ModelInstallError, "is missing"):
                    ensure_translation_model(Path(temp_dir) / "incomplete")

    def test_main_skips_disabled_translation_and_honors_failure_policy(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                "[app]\ntimezone='UTC'\n"
                "[[feeds]]\nname='LLM'\ncategories=['cs.AI']\n"
                "[translation]\nenabled=false\n",
                encoding="utf-8",
            )
            self.assertEqual(main(["--config", str(config_path)]), 0)

            config_path.write_text(
                "[app]\ntimezone='UTC'\n"
                "[[feeds]]\nname='LLM'\ncategories=['cs.AI']\n"
                "[translation]\nenabled=true\nfail_on_error=false\n",
                encoding="utf-8",
            )
            with patch(
                "tools.install_translation_model.ensure_translation_model",
                side_effect=ModelInstallError("offline"),
            ):
                self.assertEqual(main(["--config", str(config_path)]), 0)

            config_path.write_text(
                "[app]\ntimezone='UTC'\n"
                "[[feeds]]\nname='LLM'\ncategories=['cs.AI']\n"
                "[translation]\nenabled=true\nfail_on_error=true\n",
                encoding="utf-8",
            )
            with patch(
                "tools.install_translation_model.ensure_translation_model",
                side_effect=ModelInstallError("offline"),
            ):
                self.assertEqual(main(["--config", str(config_path)]), 1)

    def test_main_rejects_invalid_config_and_reports_install_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "bad.toml"
            config_path.write_text("not valid = [", encoding="utf-8")
            self.assertEqual(main(["--config", str(config_path)]), 2)

            output_dir = Path(temp_dir) / "model"
            with patch(
                "tools.install_translation_model.ensure_translation_model",
                return_value=True,
            ) as ensure:
                self.assertEqual(main(["--output-dir", str(output_dir)]), 0)
            ensure.assert_called_once_with(output_dir)


if __name__ == "__main__":
    unittest.main()
