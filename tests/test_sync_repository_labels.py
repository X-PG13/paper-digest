from __future__ import annotations

import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tools.github_services import (
    GitHubRepositoryLabelsService,
    RepositoryLabelSpec,
    RepositoryLabelSyncResult,
)
from tools.sync_repository_labels import (
    load_label_specs,
    main,
    sync_repository_labels,
)


class FakeRepositoryLabelsClient:
    def __init__(self, existing: list[str]) -> None:
        self.existing = set(existing)
        self.created: list[RepositoryLabelSpec] = []
        self.updated: list[RepositoryLabelSpec] = []

    def label_exists(self, name: str) -> bool:
        return name in self.existing

    def create_label(self, *, name: str, color: str, description: str) -> None:
        spec = RepositoryLabelSpec(
            name=name,
            color=color,
            description=description,
        )
        self.created.append(spec)
        self.existing.add(name)

    def update_label(self, *, name: str, color: str, description: str) -> None:
        self.updated.append(
            RepositoryLabelSpec(
                name=name,
                color=color,
                description=description,
            )
        )


class SyncRepositoryLabelsTests(unittest.TestCase):
    def test_load_label_specs_reads_and_validates_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            labels_file = Path(tmpdir) / "labels.json"
            labels_file.write_text(
                json.dumps(
                    [
                        {
                            "name": "bug",
                            "color": "d73a4a",
                            "description": "Bug reports",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                load_label_specs(labels_file),
                (
                    RepositoryLabelSpec(
                        name="bug",
                        color="d73a4a",
                        description="Bug reports",
                    ),
                ),
            )

            labels_file.write_text(
                json.dumps(
                    [
                        {"name": "bug", "color": "d73a4a", "description": ""},
                        {"name": "bug", "color": "d73a4a", "description": ""},
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate label name"):
                load_label_specs(labels_file)

    def test_sync_repository_labels_creates_missing_and_updates_existing(self) -> None:
        client = FakeRepositoryLabelsClient(["bug"])
        labels = (
            RepositoryLabelSpec(
                name="bug",
                color="d73a4a",
                description="Bug reports",
            ),
            RepositoryLabelSpec(
                name="maintenance",
                color="7057ff",
                description="Maintenance work",
            ),
        )

        result = sync_repository_labels(
            GitHubRepositoryLabelsService(client=client),
            labels,
        )

        self.assertEqual(
            result,
            RepositoryLabelSyncResult(
                created=("maintenance",),
                updated=("bug",),
            ),
        )
        self.assertEqual(client.updated, [labels[0]])
        self.assertEqual(client.created, [labels[1]])

    def test_main_syncs_registry_and_reports_missing_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            labels_file = Path(tmpdir) / "labels.json"
            labels_file.write_text(
                json.dumps(
                    [
                        {
                            "name": "bug",
                            "color": "d73a4a",
                            "description": "Bug reports",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            stdout = StringIO()
            with patch(
                "tools.sync_repository_labels.GitHubRepositoryLabelsService"
            ) as mock_service_class:
                mock_service_class.return_value.sync_labels.return_value = (
                    RepositoryLabelSyncResult(created=(), updated=("bug",))
                )
                exit_code = main(
                    repo="owner/repo",
                    labels_file=labels_file,
                    env={"GITHUB_TOKEN": "token"},
                    stdout=stdout,
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("updated bug", stdout.getvalue())
            mock_service_class.assert_called_once_with(
                repository="owner/repo",
                token="token",
            )
            mock_service_class.return_value.sync_labels.assert_called_once_with(
                (
                    RepositoryLabelSpec(
                        name="bug",
                        color="d73a4a",
                        description="Bug reports",
                    ),
                )
            )

        stderr = StringIO()
        exit_code = main(
            repo="owner/repo",
            env={},
            stderr=stderr,
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("missing GitHub token", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
