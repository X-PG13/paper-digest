# Compatibility Matrix

Paper Digest keeps a deliberately narrow support policy. The goal is to make
it obvious what is guaranteed today, what is expected to work, and what still
needs explicit maintainer validation before it should be advertised.

## Runtime Matrix

| Surface | Status | Validation path | Notes |
| --- | --- | --- | --- |
| CPython 3.12 | Supported | Required in local setup, CI, and release workflow | This is the canonical development and release target. |
| CPython 3.13+ | Expected, not CI-gated yet | Manual validation only until CI expands | Do not claim broader support in release notes until this is tested and documented. |
| CPython < 3.12 | Unsupported | None | Outside the declared `requires-python` range. |
| PyPy | Unsupported | None | Not part of the project scope today. |

## Platform Matrix

| Surface | Status | Validation path | Notes |
| --- | --- | --- | --- |
| GitHub Actions `ubuntu-latest` | Supported | CI, release, scheduled workflows | This is the only workflow runner treated as production-grade. |
| Local macOS | Supported on a best-effort basis | Contributor validation | Common local CLI usage should work. |
| Local Linux | Supported on a best-effort basis | Contributor validation | Matches the workflow shell model most closely. |
| Local Windows | Unverified | None | Path handling should mostly work, but docs and automation currently assume POSIX shell commands. |

## Integration Matrix

| Surface | Status | Notes |
| --- | --- | --- |
| arXiv, Crossref, PubMed, Semantic Scholar, OpenAlex fetchers | Supported | Covered by unit tests and local verification. |
| OpenAI analysis | Optional supported integration | Requires explicit API-key configuration and is disabled by default. |
| SMTP, Feishu, WeCom, Slack, Discord, Telegram delivery | Supported | Covered by unit tests; real credentials remain deployment-specific. |
| GitHub Pages archive deployment | Supported | Driven by the scheduled and backfill workflows on `main`. |

## Support Policy

1. A surface is only "supported" when the repository docs, validation path,
   and release notes all agree.
2. Widening the matrix means updating this file, the `README`, and the
   relevant workflow or packaging metadata in the same change.
3. Breaking compatibility should be called out in `CHANGELOG.md` and the GitHub
   release notes for the first affected version.

## When Widening Support

Before advertising a new runtime or platform:

1. Add or update the validation path.
2. Update this matrix and the summary table in `README.md`.
3. Update `pyproject.toml` metadata when classifiers or minimum-version claims
   change.
4. Mention the compatibility change in `CHANGELOG.md` and the release notes.
