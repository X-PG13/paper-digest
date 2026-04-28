# Review Policy

This document defines the default pull-request review expectations for Paper
Digest.

## Goals

- Keep user-visible changes reviewable.
- Make workflow, governance, and release-impacting changes visible before they
  land.
- Keep review overhead light enough for a small maintainer set.

## Default Merge Path

- Pull requests are the default path for changes to `main`.
- Direct pushes to `main` should be rare and limited to urgent maintainer
  repairs such as broken automation or repository-setting recovery.
- Even in a single-maintainer phase, prefer a pull request when the change
  affects workflows, compatibility claims, governance, or release behavior.

## Approval Expectations

- Require at least one approval before merging when the repository settings can
  enforce it.
- Use `CODEOWNERS` as the review-routing source of truth.
- Re-request review when a pull request changes substantially after review or
  when unresolved review comments would otherwise become stale.

## Changes That Need Extra Care

Treat these changes as higher-review-signal work:

- Workflow or release-pipeline changes under `.github/`.
- Compatibility or support-policy changes.
- Governance, roadmap, proposal, or maintainer-ownership changes.
- New dependencies, dependency-policy changes, or large tooling upgrades.

For those changes, the pull request should clearly call out:

- User or maintainer impact.
- Rollout or rollback expectations.
- Any doc, changelog, or ADR updates that landed with the change.

## PR Hygiene

- Pull requests should make docs and changelog intent explicit.
- Pull requests that change runtime, workflows, or repository-operations
  surfaces should also link the relevant issue or proposal, or state clearly
  why no linked issue is needed.
- If `CHANGELOG.md` or public docs are intentionally unchanged, mark that
  clearly in the PR template rather than leaving maintainers to infer intent.
- `PR Hygiene` automation should stay advisory: it should remind contributors to
  tighten the PR, not replace human review.
- Do not configure `PR Hygiene` as a required branch-protection check unless
  this section is changed to make the reminder workflow explicitly blocking.

## Self-Merge Guidance

- A single maintainer may still need to merge their own pull requests.
- When self-merging, wait for required checks to pass and leave enough context
  in the pull request description that the rationale remains reviewable later.
- Avoid self-merging broad product or governance changes without first making
  the tradeoffs visible in the issue, proposal, ADR, or pull request thread.

## Merge Strategy

- Prefer squash merges for most pull requests so history stays readable.
- Keep commit titles and pull-request titles release-note friendly.
- If merge strategy or required-review settings change, update this document
  and `docs/branch-protection-policy.md` in the same pull request.
- If rulesets or merge queue enter the workflow, update `docs/ruleset-policy.md`
  in the same pull request.
