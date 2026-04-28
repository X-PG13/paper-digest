# Release Cadence Policy

This document defines how Paper Digest approaches release timing and release
scope.

The goal is not to promise a fixed shipping schedule. The goal is to make
release timing deliberate, explainable, and consistent with current maintainer
capacity.

## Principles

- Prefer small, reviewable releases over long periods of hidden change.
- Do not publish a release only to satisfy an arbitrary calendar target.
- Treat compatibility, repository-operations changes, and user-facing upgrade
  notes as release-scope signals, not afterthoughts.
- Keep release timing visible through release-preparation and post-release
  follow-up issues rather than through private maintainer memory.

## Default Cadence

Paper Digest does not guarantee a fixed public release calendar, but the
default operating posture is:

- Patch releases: ship when fixes, packaging corrections, or workflow repairs
  are validated and worth publishing on their own.
- Minor releases: batch coherent user-facing or maintainer-facing improvements
  into a release once the docs, changelog, and workflow notes are ready.
- Major releases: reserve for explicit `breaking` changes with visible upgrade
  notes, proposal or ADR history where appropriate, and a deliberate migration
  story.

## Readiness Signals

Prefer to cut a release when most of these are true:

- the release-preparation issue clearly scopes what is shipping
- `CHANGELOG.md` and generated release-note intent agree
- compatibility claims have been checked against the documented support matrix
- any repository-settings, ruleset, or maintainer-access changes are linked to
  a current quarterly review record
- the post-release follow-up work is small enough to manage explicitly

## Reasons To Defer A Release

It is reasonable to defer a release when:

- the changelog or release-preparation issue is still ambiguous
- compatibility claims widened but were not actually validated
- repository-operations changes shipped but the quarterly review linkage is
  stale or missing
- the current cycle still has active churn that would immediately force another
  corrective tag
- maintainers cannot reasonably complete the post-release follow-up in the
  current cycle

## Versioning Expectations

- Patch releases should avoid broad behavioral or workflow-policy surprises.
- Minor releases may contain new capabilities, new integrations, or notable
  maintainer-process improvements.
- Major releases should be rare and should call out upgrade impact in
  `CHANGELOG.md`, the release-preparation issue, and the final release notes.

## Communication Rules

- Use the release-preparation issue to explain why a release is shipping now.
- Use the post-release follow-up issue to record whether the cadence felt
  appropriate or whether the cycle revealed process strain.
- If a release is intentionally deferred, note the reason in maintainer work
  rather than leaving the pause implicit.
