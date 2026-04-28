# Discussions Policy

This document defines the discussion categories the project intends to use once
GitHub Discussions is enabled, and the fallback paths that apply until then.

## Current State

- GitHub Discussions is not the primary intake path today.
- Until it is enabled, use the issue templates and pull requests that already
  exist in the repository.
- This file exists so future discussions do not start with unclear category
  rules.

## Intended Categories

Use these category meanings consistently when Discussions becomes available:

- `Announcements`: maintainer-posted release, governance, or maintenance
  updates.
- `Ideas`: early, open-ended product or workflow direction discussion before a
  concrete proposal is ready.
- `Q&A`: usage, setup, and operator questions that do not yet look like
  reproducible bugs.
- `Show and tell`: examples of local setups, archive pages, or automation
  patterns other users may learn from.
- `Polls`: narrow maintainer-run questions when several plausible directions
  need lightweight community feedback.

## Routing Rules

- Security reports do not belong in Discussions. Follow `SECURITY.md`.
- Reproducible defects should still use the bug-report issue template.
- Concrete feature or workflow proposals should use the proposal or feature
  issue templates so they can be tracked and labeled.
- Accepted design decisions that create long-lived constraints should be
  recorded as ADRs under `docs/adr/`.

## Fallback Paths Until Discussions Is Enabled

- `Ideas` -> feature request or proposal issue.
- `Q&A` -> support request.
- `Announcements` -> release notes, `CHANGELOG.md`, or maintainer docs.
- `Show and tell` -> pull request, linked issue, or external blog post linked
  from a relevant issue.
- `Polls` -> issue comments or pull-request discussion.

## Moderation Expectations

- `CODE_OF_CONDUCT.md` applies to discussions the same way it applies to issues
  and pull requests.
- Redirect conversations when they are filed through the wrong path rather than
  letting categories drift.
- Close or redirect threads that expose security details, private credentials,
  or unsupported-support requests.
