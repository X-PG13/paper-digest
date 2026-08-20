"""Optional offline English-to-Chinese paper translation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .arxiv_client import Paper, PaperTranslation
from .config import TranslationConfig

if TYPE_CHECKING:
    from .digest import DigestRun

_MAX_CHUNK_CHARS = 480
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


class TranslationError(RuntimeError):
    """Raised when configured paper translation fails."""


class _ArgosRuntime:
    def __init__(self, model_path: Path) -> None:
        model_dir = model_path / "model"
        tokenizer_path = model_path / "sentencepiece.model"
        config_path = model_dir / "config.json"
        if not model_dir.is_dir() or not tokenizer_path.is_file():
            raise TranslationError(f"translation model is incomplete: {model_path}")

        try:
            ctranslate2 = import_module("ctranslate2")
            sentencepiece = import_module("sentencepiece")
        except ImportError as exc:
            raise TranslationError(
                "translation dependencies are missing; install "
                "paper-digest[translation]"
            ) from exc

        try:
            raw_config = json.loads(config_path.read_text(encoding="utf-8"))
            self._target_token = str(raw_config["bos_token"])
            self._eos_token = str(raw_config["eos_token"])
            self._tokenizer = sentencepiece.SentencePieceProcessor(
                model_file=str(tokenizer_path)
            )
            self._translator = ctranslate2.Translator(
                str(model_dir),
                device="cpu",
                compute_type="int8",
            )
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            raise TranslationError(
                f"failed to load translation model from {model_path}: {exc}"
            ) from exc

    def translate(self, text: str) -> str:
        chunks = _split_text(text)
        if not chunks:
            return ""

        try:
            sources = [
                [
                    self._target_token,
                    *self._tokenizer.encode(chunk, out_type=str),
                    self._eos_token,
                ]
                for chunk in chunks
            ]
            results = self._translator.translate_batch(
                sources,
                beam_size=4,
                max_decoding_length=512,
            )
            translated = [
                self._tokenizer.decode(result.hypotheses[0]) for result in results
            ]
        except (IndexError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise TranslationError(f"offline translation failed: {exc}") from exc
        return _normalize_translation(" ".join(translated))


def enrich_digest_with_translation(
    config: TranslationConfig,
    digest: DigestRun,
    *,
    runtime_factory: Callable[[Path], Any] = _ArgosRuntime,
) -> None:
    """Add Chinese titles and summaries to selected digest papers in place."""

    papers = _select_papers(digest, config.max_papers)
    if not papers:
        return

    try:
        runtime = runtime_factory(config.model_path)
        translations: list[tuple[Paper, PaperTranslation]] = []
        for paper in papers:
            translations.append(
                (
                    paper,
                    PaperTranslation(
                        title=runtime.translate(paper.title),
                        summary=runtime.translate(
                            _truncate_source(paper.summary, config.max_summary_chars)
                        ),
                    ),
                )
            )
    except TranslationError as exc:
        if config.fail_on_error:
            raise
        print(
            f"Warning: {exc}; continuing without translated paper text",
            file=sys.stderr,
        )
        return

    for paper, translation in translations:
        paper.translation = translation


def translated_title(paper: Paper) -> str:
    if paper.translation is not None and paper.translation.title:
        return paper.translation.title
    return paper.title


def translated_summary(paper: Paper) -> str:
    if paper.translation is not None and paper.translation.summary:
        return paper.translation.summary
    return paper.summary


def _select_papers(digest: DigestRun, max_papers: int) -> list[Paper]:
    selected: list[Paper] = []
    index = 0
    while len(selected) < max_papers:
        added = False
        for feed in digest.feeds:
            if index < len(feed.papers):
                selected.append(feed.papers[index])
                added = True
                if len(selected) >= max_papers:
                    break
        if not added:
            break
        index += 1
    return selected


def _truncate_source(text: str, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    prefix = normalized[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{prefix or normalized[:max_chars]}..."


def _split_text(text: str) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []

    chunks: list[str] = []
    current = ""
    for sentence in _SENTENCE_BOUNDARY.split(normalized):
        if len(sentence) > _MAX_CHUNK_CHARS:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_chunk(sentence))
            continue
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > _MAX_CHUNK_CHARS:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _split_long_chunk(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current = ""
    for word in words:
        if len(word) > _MAX_CHUNK_CHARS:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(
                word[index : index + _MAX_CHUNK_CHARS]
                for index in range(0, len(word), _MAX_CHUNK_CHARS)
            )
            continue
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > _MAX_CHUNK_CHARS:
            chunks.append(current)
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _normalize_translation(text: str) -> str:
    normalized = " ".join(text.replace("▁", " ").split())
    normalized = re.sub(r"\s+([,.;:!?，。；：！？])", r"\1", normalized)
    return re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", normalized)
