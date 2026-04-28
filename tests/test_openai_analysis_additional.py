from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import patch

from paper_digest.arxiv_client import Paper
from paper_digest.config import AnalysisConfig
from paper_digest.openai_analysis import (
    OpenAIAnalysisError,
    _build_input,
    _build_instructions,
    _extract_response_text,
    _load_response_json,
    _parse_paper_analysis,
    analyze_paper_with_openai,
)


class DummyHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def build_config() -> AnalysisConfig:
    return AnalysisConfig(
        provider="openai",
        model="gpt-5-mini",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1/responses",
        timeout_seconds=60,
        max_papers=10,
        max_output_tokens=600,
        language="English",
        reasoning_effort="minimal",
    )


def build_paper() -> Paper:
    published_at = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)
    return Paper(
        title="Agent systems",
        summary="A benchmark for agent evaluation.",
        authors=["Alice"],
        categories=["cs.AI"],
        paper_id="https://arxiv.org/abs/1",
        abstract_url="https://arxiv.org/abs/1",
        pdf_url=None,
        published_at=published_at,
        updated_at=published_at,
    )


class OpenAIAnalysisAdditionalTests(unittest.TestCase):
    @patch("paper_digest.openai_analysis.urlopen")
    def test_analyze_paper_uses_output_text_and_omits_reasoning_when_disabled(
        self,
        mock_urlopen,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(
            json.dumps(
                {
                    "output_text": json.dumps(
                        {
                            "conclusion": " concise conclusion ",
                            "contributions": ["  adds benchmark  ", ""],
                            "audience": "  digest readers ",
                            "limitations": [" abstract only "],
                        }
                    )
                }
            ).encode("utf-8")
        )
        config = replace(
            build_config(),
            language="Chinese",
            reasoning_effort="none",
        )
        paper = replace(build_paper(), authors=[], categories=[])

        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}, clear=False):
            analysis = analyze_paper_with_openai(
                config,
                paper,
                template="zh_daily_brief",
            )

        self.assertEqual(analysis.conclusion, "concise conclusion")
        self.assertEqual(analysis.contributions, ["adds benchmark"])
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertNotIn("reasoning", payload)
        self.assertIn("Chinese", payload["instructions"])
        self.assertIn("Chinese daily research briefing", payload["instructions"])
        self.assertIn("Unknown authors", payload["input"])
        self.assertIn("Unknown categories", payload["input"])

    @patch("paper_digest.openai_analysis.urlopen", side_effect=OSError("network down"))
    def test_analyze_paper_wraps_network_errors(self, _mock_urlopen) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}, clear=False):
            with self.assertRaisesRegex(OpenAIAnalysisError, "network down"):
                analyze_paper_with_openai(build_config(), build_paper())

    @patch("paper_digest.openai_analysis.urlopen")
    def test_analyze_paper_rejects_non_json_response_text(
        self,
        mock_urlopen,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(
            json.dumps({"output_text": "not-json"}).encode("utf-8")
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}, clear=False):
            with self.assertRaisesRegex(OpenAIAnalysisError, "not valid JSON"):
                analyze_paper_with_openai(build_config(), build_paper())

    def test_instruction_and_input_helpers_cover_template_and_unknown_metadata(
        self,
    ) -> None:
        config = replace(build_config(), language="Chinese")
        paper = replace(build_paper(), authors=[], categories=[])

        instructions = _build_instructions(config, template="zh_daily_brief")
        prompt_input = _build_input(paper)

        self.assertIn("Write every field in Chinese.", instructions)
        self.assertIn("Chinese daily research briefing", instructions)
        self.assertIn("Unknown authors", prompt_input)
        self.assertIn("Unknown categories", prompt_input)

    def test_load_response_json_validates_shapes_and_status(self) -> None:
        cases = [
            (b"not json", "received malformed JSON from OpenAI"),
            (json.dumps([]).encode("utf-8"), "OpenAI response payload is invalid"),
            (
                json.dumps({"error": {}}).encode("utf-8"),
                "OpenAI returned an error: unknown error",
            ),
            (
                json.dumps({"status": "failed"}).encode("utf-8"),
                "OpenAI response did not complete successfully: failed",
            ),
        ]

        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(OpenAIAnalysisError, message):
                    _load_response_json(payload)

    def test_extract_response_text_validates_content_and_refusals(self) -> None:
        self.assertEqual(
            _extract_response_text({"output_text": "  direct text  "}),
            "direct text",
        )
        self.assertEqual(
            _extract_response_text(
                {
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {"type": "text", "text": "first"},
                                {"type": "output_text", "text": "second"},
                            ],
                        }
                    ]
                }
            ),
            "first\nsecond",
        )
        self.assertEqual(
            _extract_response_text(
                {
                    "output": [
                        "invalid",
                        {"type": "message", "content": "invalid"},
                        {
                            "type": "message",
                            "content": [
                                "invalid",
                                {"type": "output_text", "text": "third"},
                            ],
                        },
                    ]
                }
            ),
            "third",
        )

        error_cases = [
            (
                {"output": [{"type": "refusal"}]},
                "OpenAI refused to analyze the paper",
            ),
            (
                {"output": [{"type": "message", "content": [{"type": "refusal"}]}]},
                "OpenAI refused to analyze the paper",
            ),
            ({}, "OpenAI response did not include output content"),
            (
                {"output": [{"type": "message", "content": [{"type": "text"}]}]},
                "OpenAI response did not include analysis text",
            ),
        ]
        for payload, message in error_cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(OpenAIAnalysisError, message):
                    _extract_response_text(payload)

    def test_parse_paper_analysis_normalizes_and_validates_fields(self) -> None:
        analysis = _parse_paper_analysis(
            {
                "conclusion": "  concise conclusion ",
                "contributions": [" first ", ""],
                "audience": " research readers ",
                "limitations": [" abstract only "],
            }
        )
        self.assertEqual(analysis.conclusion, "concise conclusion")
        self.assertEqual(analysis.contributions, ["first"])
        self.assertEqual(analysis.audience, "research readers")
        self.assertEqual(analysis.limitations, ["abstract only"])

        error_cases = [
            ([], "OpenAI analysis payload is invalid"),
            (
                {
                    "conclusion": " ",
                    "contributions": [],
                    "audience": "readers",
                    "limitations": [],
                },
                "analysis.conclusion must not be empty",
            ),
            (
                {
                    "conclusion": "ok",
                    "contributions": "bad",
                    "audience": "readers",
                    "limitations": [],
                },
                "analysis.contributions must be an array of strings",
            ),
            (
                {
                    "conclusion": "ok",
                    "contributions": ["ok", 1],
                    "audience": "readers",
                    "limitations": [],
                },
                "analysis.contributions must contain only strings",
            ),
            (
                {
                    "conclusion": "ok",
                    "contributions": [],
                    "audience": 1,
                    "limitations": [],
                },
                "analysis.audience must be a string",
            ),
        ]
        for payload, message in error_cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(OpenAIAnalysisError, message):
                    _parse_paper_analysis(payload)
