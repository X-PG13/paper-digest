# Maintainer Operations Hub

This page is the maintainer-facing index for Paper Digest repository
operations.

Use it as the first stop when you need to decide which maintainer doc, issue
form, or workflow is the source of truth for a given task.

## Start Here

If you only need one entry point, use this page first and then jump to the
specialized source-of-truth doc.

## Task Map

| If you need to... | Start here | Then use |
| --- | --- | --- |
| review or merge a pull request | `docs/review-policy.md` | `docs/branch-protection-policy.md`, `docs/repository-settings-checklist.md` |
| audit repository settings or maintainer access | `docs/quarterly-maintainer-review.md` | `docs/maintainer-access-policy.md`, `docs/repository-settings-checklist.md`, `docs/ruleset-policy.md` |
| prepare a release | `RELEASING.md` | `docs/release-cadence-policy.md`, `docs/release-lifecycle-runbook.md`, `.github/ISSUE_TEMPLATE/release_preparation.yml` |
| follow up after a release | `docs/post-release-checklist.md` | `.github/ISSUE_TEMPLATE/post_release_follow_up.yml`, `.github/workflows/post-release-follow-up.yml`, `docs/operations-history.md` |
| understand release history or maintainer-process changes | `docs/operations-history.md` | `CHANGELOG.md`, `docs/release-lifecycle-runbook.md` |
| route issues or support requests | `docs/issue-triage.md` | `SECURITY.md`, `SUPPORT.md`, `docs/label-taxonomy.md` |
| change governance or ownership | `GOVERNANCE.md` | `docs/maintainer-rotation.md`, `docs/maintainer-access-policy.md`, `docs/roadmap-policy.md` |
| change release cadence or lifecycle rules | `docs/release-cadence-policy.md` | `docs/release-lifecycle-runbook.md`, `RELEASING.md`, `docs/operations-history.md` |

## Cadence Map

| Cadence | Primary doc | Typical artifacts |
| --- | --- | --- |
| every pull request that changes policy or operations | `CONTRIBUTING.md` | PR template, matching policy docs, changelog |
| quarterly or when repository-admin settings change | `docs/quarterly-maintainer-review.md` | quarterly review issue, settings doc updates |
| when deciding whether to cut a release | `docs/release-cadence-policy.md` | release-preparation issue, changelog, compatibility checks |
| during release prep | `RELEASING.md` | release-preparation issue, release-preparation PR, quarterly-review link when needed |
| after release publication | `docs/post-release-checklist.md` | post-release follow-up issue, operations-history update |

## Source-Of-Truth Map

| Area | Source of truth |
| --- | --- |
| maintainer onboarding and access review | `docs/maintainer-access-policy.md` |
| repository-admin settings | `docs/repository-settings-checklist.md` |
| rulesets and merge queue | `docs/ruleset-policy.md` |
| pull-request review expectations | `docs/review-policy.md` |
| release timing and scope | `docs/release-cadence-policy.md` |
| release artifact linkage | `docs/release-lifecycle-runbook.md` |
| post-release verification | `docs/post-release-checklist.md` |
| long-lived operations history | `docs/operations-history.md` |
| issue triage and labeling | `docs/issue-triage.md`, `docs/label-taxonomy.md` |
| governance and ownership changes | `GOVERNANCE.md`, `docs/maintainer-rotation.md` |

## Lifecycle Shortcuts

Use these doc chains for the most common maintainer paths:

- Quarterly review path:
  `docs/quarterly-maintainer-review.md` ->
  `docs/maintainer-access-policy.md` ->
  `docs/repository-settings-checklist.md` ->
  `docs/operations-history.md`
- Release path:
  `docs/release-cadence-policy.md` ->
  `RELEASING.md` ->
  `.github/ISSUE_TEMPLATE/release_preparation.yml` ->
  `docs/release-lifecycle-runbook.md`
- Post-release path:
  `docs/post-release-checklist.md` ->
  `.github/ISSUE_TEMPLATE/post_release_follow_up.yml` ->
  `.github/workflows/post-release-follow-up.yml` ->
  `docs/operations-history.md`

## Records

When maintainer work leaves a durable record, prefer these locations:

- release-to-release history: `docs/operations-history.md`
- user-facing shipped changes: `CHANGELOG.md`
- long-lived design or governance decisions: `docs/adr/` and `GOVERNANCE.md`
- live repository rules and maintenance policy: the docs linked in the
  source-of-truth map above
