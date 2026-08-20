from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from paper_digest.arxiv_client import Paper
from paper_digest.config import TranslationConfig
from paper_digest.digest import DigestRun, FeedDigest
from paper_digest.translation import (
    TranslationError,
    _ArgosRuntime,
    _normalize_translation,
    _select_papers,
    _split_text,
    _truncate_source,
    enrich_digest_with_translation,
    translated_summary,
    translated_title,
)


def build_paper(title: str, summary: str | None = None) -> Paper:
    published_at = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)
    return Paper(
        title=title,
        summary=summary or f"{title} summary",
        authors=["Alice"],
        categories=["cs.AI"],
        paper_id=f"https://arxiv.org/abs/{title}",
        abstract_url=f"https://arxiv.org/abs/{title}",
        pdf_url=None,
        published_at=published_at,
        updated_at=published_at,
    )


def build_config(model_path: Path, *, fail_on_error: bool = False) -> TranslationConfig:
    return TranslationConfig(
        provider="argos",
        model_path=model_path,
        max_papers=2,
        max_summary_chars=12,
        fail_on_error=fail_on_error,
    )


class DummyRuntime:
    def __init__(self, _model_path: Path) -> None:
        self.inputs: list[str] = []

    def translate(self, text: str) -> str:
        self.inputs.append(text)
        return f"中文：{text}"


class FailingRuntime:
    def __init__(self, _model_path: Path) -> None:
        raise TranslationError("model unavailable")


class TranslationTests(unittest.TestCase):
    def test_enrich_digest_translates_round_robin_and_truncates_summaries(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 8, 12, 9, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[
                FeedDigest(name="LLM", papers=[build_paper("A"), build_paper("B")]),
                FeedDigest(
                    name="SWE",
                    papers=[build_paper("C", "one two three four five")],
                ),
            ],
        )

        enrich_digest_with_translation(
            build_config(Path("model")),
            digest,
            runtime_factory=DummyRuntime,
        )

        first = digest.feeds[0].papers[0]
        second = digest.feeds[1].papers[0]
        self.assertEqual(first.translation.title, "中文：A")
        self.assertEqual(second.translation.title, "中文：C")
        self.assertEqual(second.translation.summary, "中文：one two...")
        self.assertIsNone(digest.feeds[0].papers[1].translation)
        self.assertEqual(translated_title(first), "中文：A")
        self.assertEqual(translated_summary(first), "中文：A summary")

    def test_enrich_digest_skips_runtime_for_empty_digest(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 8, 12, 9, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[])],
        )

        with patch("paper_digest.translation._ArgosRuntime") as runtime:
            enrich_digest_with_translation(build_config(Path("model")), digest)

        runtime.assert_not_called()

    def test_enrich_digest_falls_back_or_raises_by_policy(self) -> None:
        paper = build_paper("A")
        digest = DigestRun(
            generated_at=datetime(2026, 8, 12, 9, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[paper])],
        )

        with patch("sys.stderr"):
            enrich_digest_with_translation(
                build_config(Path("model")),
                digest,
                runtime_factory=FailingRuntime,
            )
        self.assertIsNone(paper.translation)
        self.assertEqual(translated_title(paper), "A")
        self.assertEqual(translated_summary(paper), "A summary")

        with self.assertRaisesRegex(TranslationError, "model unavailable"):
            enrich_digest_with_translation(
                build_config(Path("model"), fail_on_error=True),
                digest,
                runtime_factory=FailingRuntime,
            )

    def test_translation_is_applied_only_after_the_batch_succeeds(self) -> None:
        class PartialFailureRuntime:
            def __init__(self, _model_path: Path) -> None:
                self.calls = 0

            def translate(self, text: str) -> str:
                self.calls += 1
                if self.calls == 3:
                    raise TranslationError("second paper failed")
                return f"中文：{text}"

        first = build_paper("A")
        second = build_paper("B")
        digest = DigestRun(
            generated_at=datetime(2026, 8, 12, 9, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[FeedDigest(name="LLM", papers=[first, second])],
        )

        with patch("sys.stderr"):
            enrich_digest_with_translation(
                build_config(Path("model")),
                digest,
                runtime_factory=PartialFailureRuntime,
            )

        self.assertIsNone(first.translation)
        self.assertIsNone(second.translation)

    def test_text_helpers_cover_chunking_and_normalization(self) -> None:
        self.assertEqual(_truncate_source(" a   short text ", 20), "a short text")
        self.assertEqual(_truncate_source("one two three", 8), "one two...")
        self.assertEqual(_truncate_source("abcdefgh", 3), "abc...")
        self.assertEqual(_split_text(""), [])
        self.assertEqual(
            _split_text("First. Second? Third!"),
            ["First. Second? Third!"],
        )
        chunks = _split_text("word " * 150)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 480 for chunk in chunks))
        self.assertEqual(
            _normalize_translation("▁软件工程 代理 , 推论成本 。"),
            "软件工程代理, 推论成本。",
        )
        long_token_chunks = _split_text("x" * 1000)
        self.assertEqual([len(chunk) for chunk in long_token_chunks], [480, 480, 40])
        mixed_chunks = _split_text("Short. " + "word " * 120)
        self.assertGreater(len(mixed_chunks), 1)
        bounded_sentences = _split_text(
            f"{'a' * 300}. {'b' * 300}."
        )
        self.assertEqual([len(chunk) for chunk in bounded_sentences], [301, 301])
        short_then_long = _split_text("Short. " + "x" * 600)
        self.assertEqual([len(chunk) for chunk in short_then_long], [6, 480, 120])
        word_then_long_token = _split_text("short " + "x" * 600)
        self.assertEqual(
            [len(chunk) for chunk in word_then_long_token],
            [5, 480, 120],
        )

    def test_select_papers_handles_multiple_depths(self) -> None:
        digest = DigestRun(
            generated_at=datetime(2026, 8, 12, 9, 0, tzinfo=UTC),
            timezone="UTC",
            lookback_hours=24,
            feeds=[
                FeedDigest(name="LLM", papers=[build_paper("A"), build_paper("B")]),
                FeedDigest(name="SWE", papers=[build_paper("C")]),
            ],
        )
        self.assertEqual(
            [paper.title for paper in _select_papers(digest, 3)],
            ["A", "C", "B"],
        )

    def test_argos_runtime_validates_model_and_optional_dependencies(self) -> None:
        with TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            with self.assertRaisesRegex(TranslationError, "model is incomplete"):
                _ArgosRuntime(model_path)

            (model_path / "model").mkdir()
            (model_path / "sentencepiece.model").write_bytes(b"model")
            with patch(
                "paper_digest.translation.import_module",
                side_effect=ImportError("missing"),
            ):
                with self.assertRaisesRegex(
                    TranslationError,
                    "translation dependencies are missing",
                ):
                    _ArgosRuntime(model_path)

    def test_argos_runtime_translates_and_wraps_runtime_errors(self) -> None:
        class Tokenizer:
            def __init__(self, *, model_file: str) -> None:
                self.model_file = model_file

            def encode(self, text: str, *, out_type: type[str]) -> list[str]:
                self.assert_out_type = out_type
                return text.split()

            def decode(self, tokens: list[str]) -> str:
                return "▁" + " ".join(tokens)

        class Translator:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                self.fail = False

            def translate_batch(self, sources, **_kwargs):
                if self.fail:
                    raise RuntimeError("inference failed")
                return [
                    SimpleNamespace(hypotheses=[["中文", *source[1:-1]]])
                    for source in sources
                ]

        with TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            (model_path / "model").mkdir()
            (model_path / "sentencepiece.model").write_bytes(b"model")
            (model_path / "model" / "config.json").write_text(
                json.dumps({"bos_token": ">>cmn_Hans<<", "eos_token": "</s>"}),
                encoding="utf-8",
            )
            modules = {
                "ctranslate2": SimpleNamespace(Translator=Translator),
                "sentencepiece": SimpleNamespace(SentencePieceProcessor=Tokenizer),
            }
            with patch(
                "paper_digest.translation.import_module",
                side_effect=modules.__getitem__,
            ):
                runtime = _ArgosRuntime(model_path)

            self.assertEqual(runtime.translate(""), "")
            self.assertEqual(
                runtime.translate("Agent benchmark"),
                "中文 Agent benchmark",
            )
            runtime._translator.fail = True
            with self.assertRaisesRegex(TranslationError, "inference failed"):
                runtime.translate("Agent benchmark")

    def test_argos_runtime_wraps_invalid_model_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            (model_path / "model").mkdir()
            (model_path / "sentencepiece.model").write_bytes(b"model")
            (model_path / "model" / "config.json").write_text("{}", encoding="utf-8")
            modules = {
                "ctranslate2": SimpleNamespace(Translator=object),
                "sentencepiece": SimpleNamespace(SentencePieceProcessor=object),
            }
            with patch(
                "paper_digest.translation.import_module",
                side_effect=modules.__getitem__,
            ):
                with self.assertRaisesRegex(TranslationError, "failed to load"):
                    _ArgosRuntime(model_path)


if __name__ == "__main__":
    unittest.main()
