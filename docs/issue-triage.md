# Issue Triage Policy

This document defines how maintainers classify and respond to incoming issues.

The maintained label set is documented in `docs/label-taxonomy.md`.

## Intake Categories

- Security: must be redirected to the private path in `SECURITY.md`.
- Bug: a supported-path behavior regression or defect with a reproducible case.
- Feature request: a proposal for a new capability, API surface, or workflow.
- Proposal: a larger product, workflow, or governance change that needs scoped
  discussion before implementation.
- Support: a usage, setup, or configuration question that is not yet a
  confirmed bug.
- Documentation: missing, ambiguous, or outdated public guidance.

## First Triage Pass

On the first pass, maintainers should answer three questions:

1. Is this filed through the right channel?
2. Is the report in a supported environment according to
   `docs/compatibility-matrix.md`?
3. Is there enough information to act on it?

If the answer to any of these is "no", the next maintainer action should be a
redirect, a support-boundary clarification, or a concrete information request.

## Minimum Information Bar

A report is actionable when it contains:

- The Paper Digest version, tag, or commit.
- The Python version and operating system.
- The command or workflow path being used.
- A minimal config snippet with secrets removed.
- A clear observed result and expected result.

Issues that do not meet that bar may be labeled or replied to as
"needs-repro" or "needs-info" by maintainers, even if the exact GitHub label
set changes over time.

## Label Usage

- Apply one routing label such as `bug`, `enhancement`, `support`,
  `documentation`, or `maintenance`.
- Use `enhancement` for scoped new capabilities, product improvements, or
  workflow changes that do not need proposal-level scoping.
- Use `documentation` for docs-only reports or documentation follow-up issues.
  `documentation` may be applied automatically to pull requests that touch
  public docs or Markdown entry points, and maintainers should also use it for
  docs-only follow-up work.
- Use `maintenance` for CI, tooling, dependency, or repository-health work,
  including scheduled maintainer operations or release-tracking issues.
- Add `proposal` when an issue is intended to shape roadmap, governance, or a
  larger design direction before implementation starts.
- Add `dependencies` to dependency-update PRs or issues that exist mainly to
  track ecosystem maintenance.
- Treat `needs-info` and `needs-repro` as maintainer follow-up labels, not
  routing labels.
- Add `needs-info` or `needs-repro` only when the maintainer reply clearly says
  what is missing.
- Use `needs-repro` when a concrete minimal reproduction is still required
  before work can continue.
- Use `duplicate` when closing a report that is already tracked elsewhere, and
  link the canonical issue or pull request in the closing reply.
- Use `invalid` only when a report is not actionable as filed and the correct
  reason or intake path has already been explained; do not use it as a
  substitute for `needs-info`.
- Use `blocked` when maintainers cannot proceed because an external dependency
  or explicit maintainer decision is still pending, and the blocker should be
  linked.
- Use `wontfix` when maintainers intentionally decide not to plan a report
  after scope or product review, and link the relevant scope or policy reason
  in the closing reply.
- Add `breaking` when a change alters documented behavior, compatibility, or
  workflow expectations and needs explicit upgrade guidance.
- Add `release-note` when the eventual change should be called out in both
  `CHANGELOG.md` and the generated GitHub release notes.
- Pair `breaking` with `release-note` when the shipped change must be called
  out publicly in `CHANGELOG.md` and release notes.
- Reserve `security` for internal coordination after a private report has
  already been routed correctly.
- `good first issue` and `help wanted` are manual contributor-facing labels.
  Use them only when scope, acceptance criteria, and relevant docs are
  explicit.
- Use `good first issue` only for deliberately small, well-scoped
  contributions that are suitable for a first external contribution.
- Use `help wanted` when maintainers welcome outside implementation help but
  the task may still require more repository context.
- Reserve `ops-review` for scheduled repository-operations review and
  access-audit issues.
- Reserve `release-prep` for maintainer release-preparation tracking issues.
- Reserve `release-follow-up` for maintainer post-release verification and
  immediate follow-up issues.

## Automation

- `.github/workflows/community-triage.yml` adds `needs-info` to bug reports
  that still miss the minimum reproducibility fields from the bug template.
- The same workflow also adds `needs-info` to support requests that still miss
  confirmation that the pre-read docs were checked or the minimum environment
  context from the support template.
- `needs-repro` remains maintainer-applied after a concrete reproduction
  request; community-triage should not add it automatically.
- `.github/ISSUE_TEMPLATE/feature_request.yml` uses `enhancement`, and
  `.github/ISSUE_TEMPLATE/proposal.yml` keeps `enhancement` plus `proposal`
  aligned for larger design work.
- The same workflow applies `documentation`, `maintenance`, `dependencies`,
  and `proposal` to pull requests based on changed paths and actor metadata.
- `.github/workflows/community-triage.yml` path-based PR intake uses
  `maintenance` for workflow, tooling, and repository-health changes.
- Dependabot and dependency-review flows use `dependencies` and `maintenance`
  for dependency maintenance intake.
- `.github/ISSUE_TEMPLATE/config.yml` routes security, support, and proposal
  contact links to the correct public policy docs.
- `.github/workflows/quarterly-maintainer-review.yml`,
  `.github/workflows/post-release-follow-up.yml`, and the maintainer lifecycle
  issue forms keep scheduled repository-health work under `maintenance`.
- `.github/release.yml` uses `breaking`, `enhancement`, and `maintenance` to
  keep generated release categories aligned with release intent.
- `.github/release.yml` should continue to map `release-note` into the
  generated GitHub release-note categories, while `invalid` stays excluded
  from generated notes.
- `.github/workflows/stale.yml` applies `stale` after 21 inactive issue days
  and 30 inactive pull-request days, closes issues 7 days later, and does not
  auto-close pull requests.
- `.github/workflows/quarterly-maintainer-review.yml` uses `maintenance` and
  `ops-review` for scheduled maintainer review issues.
- `.github/ISSUE_TEMPLATE/release_preparation.yml` keeps `release-prep`
  aligned with the maintainer release lifecycle.
- `.github/ISSUE_TEMPLATE/post_release_follow_up.yml` and
  `.github/workflows/post-release-follow-up.yml` keep `release-follow-up`
  aligned with the maintainer release lifecycle.
- Bug, feature, proposal, support, release-preparation, and post-release
  follow-up intake should use the GitHub issue forms under
  `.github/ISSUE_TEMPLATE/` so the collected fields stay structured.
- Automation should stay conservative: it should add or clarify labels, not
  replace maintainer judgment.

## Supported-Surface Rule

Maintainers should prioritize:

- The latest release.
- The current `main` branch.
- The documented local CLI and GitHub Actions paths.

Reports targeting unsupported runtimes, old releases, or heavily modified forks
may be closed after a short clarification.

## Closure Guidelines

Maintainers may close issues when:

- The report is a duplicate.
- The report is not actionable as filed and the correct path or reason was
  documented.
- The report is actually a support question and the documented answer was
  provided.
- The issue targets an unsupported environment or version.
- The reporter does not provide requested reproduction details after a
  reasonable follow-up window.
- The request is outside the project scope documented in `README.md` and
  `SUPPORT.md`.

## Stale Policy

- Use `stale` only for inactivity handling under the documented timer; do not
  use it as a substitute for direct triage or closure.
- Issues may be marked `stale` after 21 days without activity.
- Stale issues may be closed 7 days later if no new information arrives.
- Pull requests may be marked `stale` after 30 days without activity, but they
  are not auto-closed by default.
- `blocked` stays exempt from stale on both issues and pull requests until the
  blocker is cleared.
- Reports already resolved as `duplicate` or `wontfix` should be closed
  directly instead of being left open for `stale`.
- `documentation` follow-up issues still use the standard stale timer unless
  another exempt maintainer-work label applies.
- `good first issue` and `help wanted` stay exempt from stale on issues so
  curated contributor entry points remain visible.
- `release-note` stays exempt from stale on both issues and pull requests until
  the label is cleared.
- `ops-review`, `release-prep`, and `release-follow-up` are maintainer
  lifecycle labels and stay exempt from stale issue closure.
- `security`, `blocked`, `release-note`, `good first issue`, `help wanted`,
  `ops-review`, `release-prep`, and `release-follow-up` are exempt from stale
  issue closure.

## Community Expectations

- Keep triage factual and direct.
- Link the exact doc or policy being applied when redirecting or closing.
- If a report is closed or redirected but still exposes a docs gap, update the
  relevant public docs or file/link a follow-up documentation issue.
- Apply the same support and compatibility rules to every reporter.
- Escalate conduct problems under `CODE_OF_CONDUCT.md`.
