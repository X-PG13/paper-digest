# Roadmap Policy

This document defines how ideas become roadmap items and how roadmap language
should be interpreted.

## What The Roadmap Means

- The roadmap is directional, not a promise.
- Items listed in `README.md` are intentionally high-level.
- Detailed discussion should happen in linked issues or pull requests, not in
  the roadmap summary itself.

## Intake Sources

Potential roadmap work can come from:

- Feature request issues.
- Maintainer-driven workflow or maintenance needs.
- Compatibility or release-process gaps.
- Repeated support or bug-report patterns that point to missing product work.

## Promotion Criteria

An item is a good roadmap candidate when it:

- Fits the documented project scope.
- Improves a supported user or maintainer path.
- Has a plausible maintenance cost for the current maintainer set.
- Can be explained clearly enough for contributors to understand the target.

Items are less likely to be promoted when they:

- Depend on unsupported runtimes or platforms.
- Require broad product surface area outside the repository's current scope.
- Add long-term maintenance burden without clear user benefit.

## Proposal Expectations

Major proposals should include:

- The problem statement.
- The intended user or maintainer outcome.
- Alternatives considered.
- Compatibility, operational, and documentation impact.
- Whether the change should be called out with the `release-note` label.
- Whether the proposal should be tracked with the `proposal` label.
- Whether the accepted outcome should be recorded as an ADR.

Until Discussions is enabled, the proposal issue template and feature-request
issue template are the default entrypoints. Category intent and fallback paths
are documented in `docs/discussions-policy.md`.

## Prioritization Buckets

Use these meanings consistently when maintainers talk about roadmap priority:

- `Now`: actively being implemented or prepared.
- `Next`: likely near-term work once current priorities land.
- `Later`: aligned with direction, but not committed to a specific cycle.
- `Not planned`: outside scope or not justified right now.

## Breaking And High-Impact Changes

Changes that alter compatibility, support policy, workflow ownership, or public
configuration expectations should:

1. Have explicit rationale in the issue or pull request.
2. Update the affected docs in the same change.
3. Be reflected in `CHANGELOG.md`.
4. Use `release-note` and, when appropriate, `breaking`.

## Review Cadence

- Revisit the roadmap when a release is being prepared.
- Revisit it when repeated issues reveal a missing priority.
- Prefer removing stale roadmap bullets over leaving unclear commitments in
  place.
