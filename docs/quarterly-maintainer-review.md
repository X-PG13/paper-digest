# Quarterly Maintainer Review

This document defines the recurring quarterly review that keeps repository
settings, maintainer access, and public governance docs aligned.

The scheduled issue created by
`.github/workflows/quarterly-maintainer-review.yml` should use this checklist
as its source of truth.

## Goals

- Confirm that repository access still follows least-privilege rules.
- Catch drift between live GitHub settings and documented repository policy.
- Leave a dated public record of repository-operations review work.

## Review Inputs

Compare the live repository state against:

- `docs/maintainer-access-policy.md`
- `docs/repository-settings-checklist.md`
- `docs/ruleset-policy.md`
- `docs/review-policy.md`
- `docs/branch-protection-policy.md`
- `docs/maintainer-guide.md`
- `docs/saved-replies.md`
- `.github/CODEOWNERS`
- `GOVERNANCE.md`
- `docs/maintainer-rotation.md`

## Required Checks

During the quarterly review, confirm:

- the collaborator list still matches the expected maintainer set
- each maintainer still needs their current GitHub repository role
- admin access is limited to maintainers who actively manage repository-admin
  settings
- branch protection, required checks, and rulesets still match the documented
  policy
- merge strategy, Pages, Discussions, environments, and dependency/security
  settings still match `docs/repository-settings-checklist.md`
- `CODEOWNERS`, governance docs, and maintainer-rotation docs still reflect
  the real ownership model
- saved replies, support routing, and security routing still point to the
  right maintainers and docs
- secrets, environments, and release credentials still have clear current
  ownership

## Close-Out Expectations

When the review finishes:

<!-- BEGIN GENERATED: quarterly-review-close-out -->
- close the issue with a short summary of what changed or that no changes were needed
- update any affected docs in the same pull request if drift was found
- mention follow-up work explicitly if the review uncovered deferred cleanup
<!-- END GENERATED: quarterly-review-close-out -->

## Review Summary Template

Use a short closing summary in the issue so quarterly reviews stay searchable
and comparable over time.

<!-- BEGIN GENERATED: quarterly-review-summary -->
```md
## Review Summary

- Review date: YYYY-MM-DD
- Reviewed by: @maintainer
- Access changes: none | short summary
- Repository-settings drift: none | short summary
- Docs updated: none | PR or file list
- Follow-up work: none | issue or PR links
- Release impact: none | operator-facing note
- Next review due: YYYY-MM-DD
```

Write `none` explicitly when no changes were required.
The scheduled workflow should prefill the mutable summary fields with `none`;
replace `none` with a short summary, file list, or issue/PR links only where
the review changed something.
<!-- END GENERATED: quarterly-review-summary -->

## Release Linkage

- If the release cycle changed repository settings, required checks, rulesets,
  maintainer access, or other operator-facing GitHub configuration, link the
  latest quarterly review issue from the release-preparation pull request or
  maintainer notes for that cycle.
- If a release is being prepared and the latest quarterly review is overdue,
  complete the review first or document the deferral explicitly in release
  preparation work.

## Missed Or Manual Reviews

- If the scheduled workflow cannot open the issue, create one manually with the
  same quarter naming scheme and use this checklist.
- If the review happens off-schedule because of incident response, maintainer
  changes, or settings migration, link that work back to the quarterly review
  record when possible.
