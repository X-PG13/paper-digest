from __future__ import annotations

import json
import os
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from paper_digest.arxiv_client import Paper
from paper_digest.config import AnalysisConfig
from paper_digest.openai_analysis import (
    OpenAIAnalysisError,
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
        top_highlights=3,
        feed_key_points=3,
        language="English",
        reasoning_effort="minimal",
        template="default",
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


class OpenAIAnalysisTests(unittest.TestCase):
    @patch("paper_digest.openai_analysis.urlopen")
    def test_analyze_paper_with_openai_builds_request_and_parses_response(
        self,
        mock_urlopen,
    ) -> None:
        mock_urlopen.return_value = DummyHTTPResponse(
            json.dumps(
                {
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(
                                        {
                                            "conclusion": "Strong digest conclusion.",
                                            "contributions": ["Adds a benchmark"],
                                            "audience": "Agent researchers.",
                                            "limitations": ["Abstract-only evidence."],
                                        }
                                    ),
                                }
                            ],
                        }
                    ],
                }
            ).encode("utf-8")
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}, clear=False):
            analysis = analyze_paper_with_openai(build_config(), build_paper())

        self.assertEqual(analysis.conclusion, "Strong digest conclusion.")
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "gpt-5-mini")
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertEqual(request.headers["Authorization"], "Bearer secret")

    def test_analyze_paper_with_openai_requires_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(OpenAIAnalysisError):
                analyze_paper_with_openai(build_config(), build_paper())
