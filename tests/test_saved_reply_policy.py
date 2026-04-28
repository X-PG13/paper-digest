from __future__ import annotations

import unittest

from tests.policy_assertions import assert_file_contains_snippets
from tools.saved_reply_policy import (
    DOCS_FOLLOW_UP_REPLY_ITEMS,
    DUPLICATE_REPLY_ITEMS,
    NEEDS_INFO_REPLY_ITEMS,
    NEEDS_REPRO_REPLY_LINES,
    OUT_OF_SCOPE_REPLY_LINES,
    SAVED_REPLY_SPECS,
    SECURITY_REDIRECT_REPLY_HEADER,
    SUPPORT_REDIRECT_REPLY_FOOTER,
    SUPPORT_REDIRECT_REPLY_HEADER,
    SUPPORT_REDIRECT_REPLY_INTRO,
    get_saved_reply,
    required_saved_reply_snippets,
    validate_saved_reply_contract,
)


class SavedReplyPolicyTests(unittest.TestCase):
    def test_saved_reply_contract_is_self_consistent(self) -> None:
        validate_saved_reply_contract()
        self.assertEqual(len(SAVED_REPLY_SPECS), 7)
        self.assertEqual(get_saved_reply("needs-info").slug, "needs-info")
        self.assertEqual(
            get_saved_reply("support-redirect").header,
            SUPPORT_REDIRECT_REPLY_HEADER,
        )
        self.assertEqual(
            get_saved_reply("duplicate").bullet_items,
            DUPLICATE_REPLY_ITEMS,
        )
        self.assertIn("workflow path", NEEDS_INFO_REPLY_ITEMS[0])
        self.assertIn("exact output", NEEDS_REPRO_REPLY_LINES[0])
        self.assertIn("usage or configuration question", SUPPORT_REDIRECT_REPLY_HEADER)
        self.assertIn("pre-read docs", SUPPORT_REDIRECT_REPLY_INTRO)
        self.assertIn("reproducible bug", SUPPORT_REDIRECT_REPLY_FOOTER)
        self.assertIn("future proposal", OUT_OF_SCOPE_REPLY_LINES[0])
        self.assertIn("follow-up documentation issue", DOCS_FOLLOW_UP_REPLY_ITEMS[1])
        self.assertEqual(
            SECURITY_REDIRECT_REPLY_HEADER,
            "Please do not continue this report in public.",
        )

    def test_get_saved_reply_rejects_unknown_slug(self) -> None:
        with self.assertRaisesRegex(KeyError, "unknown saved reply slug"):
            get_saved_reply("missing")

    def test_saved_replies_doc_contains_required_contract_snippets(self) -> None:
        assert_file_contains_snippets(
            self,
            "docs/saved-replies.md",
            required_saved_reply_snippets(),
        )


if __name__ == "__main__":
    unittest.main()
