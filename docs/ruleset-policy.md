# Ruleset Policy

This document defines the intended use of GitHub rulesets for this repository.
Use it together with `docs/branch-protection-policy.md` and
`docs/repository-settings-checklist.md`.

## Scope

- Use branch protection on `main` as the baseline review and merge control.
- Use rulesets to make that policy more explicit when repository settings and
  plan features allow it.
- Do not create overlapping or experimental rulesets without documenting why
  the extra layer exists.

## Intended Branch Ruleset

If branch rulesets are available for the repository, create a ruleset that
targets `main` and aligns with the documented branch-protection posture:

1. Require pull requests before merging.
2. Require at least one approval.
3. Require code-owner review.
4. Require conversations to be resolved.
5. Require the documented status checks to pass.
6. Require linear history.
7. Block force pushes and deletions.

Keep the rule names and enforcement readable so contributors can understand why
merges are blocked.

## Enforcement Mode

- Use active enforcement for the main stable path once the rule set matches the
  published maintainer policy.
- Use evaluate mode only when maintainers are intentionally testing a new rule
  before enforcing it.
- If evaluate mode is used, record the reason and expected follow-up in
  maintainer work rather than leaving it indefinite.

## Merge Queue

- Merge queue is not required by default for this repository today.
- Only enable merge queue when repository ownership, GitHub plan features, and
  PR volume make it useful.
- If merge queue is enabled later, update:
  `docs/repository-settings-checklist.md`,
  `docs/branch-protection-policy.md`, and
  `docs/maintainer-guide.md`.
- If merge queue is not available for the repository plan or ownership model,
  document that limitation rather than pretending it is part of the enforced
  workflow.

## Required Checks

Keep ruleset-required checks aligned with the documented branch policy. The
required GitHub check contexts are:

- `verify / verify` for the `CI` workflow
- `dependency-review` for the `Dependency Review` workflow
- `actionlint` for the `Workflow Lint` workflow

Keep `PR Hygiene` advisory unless `docs/review-policy.md` and
`docs/branch-protection-policy.md` are changed in the same pull request to make
PR hygiene blocking.

If check names change, update this file and the related maintainer docs in the
same pull request.

## Review Cadence

Revisit rulesets when:

- branch-protection policy changes
- workflow names change
- a new maintainer receives admin access
- merge contention starts to justify merge queue

If rulesets and branch protection ever diverge, treat this as an operational
bug and reconcile it quickly.
