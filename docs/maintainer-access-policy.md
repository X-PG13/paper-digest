# Maintainer Access Policy

This document defines how maintainer access should be granted, reviewed, and
removed for Paper Digest.

The project is still effectively single-maintainer today, but the policy is
written now so future growth does not rely on undocumented admin habits.

## Principles

- Prefer the lowest GitHub role that still lets a maintainer do their work.
- Treat repository-admin settings as audited infrastructure, not private
  maintainer preference.
- Keep ownership, review routing, and access grants aligned across public docs
  and live repository settings.
- Never share personal accounts, saved replies, access tokens, or local secret
  material between maintainers.
- When access changes, update the related governance and repository-operations
  docs in the same pull request whenever possible.

## Repository Access Levels

Use GitHub repository roles conservatively:

- `Triage`: issue and discussion routing without write access.
- `Write`: normal day-to-day contribution, branch pushes, and pull-request
  work.
- `Maintain`: repository-management tasks that do not require full admin.
- `Admin`: branch protection, rulesets, secrets, Pages, Discussions, or other
  settings that cannot be managed with a lower role.

Admin access should be rare. If a maintainer only needs review and merge
rights, prefer `Write` or `Maintain` over `Admin`.

## Onboarding A Maintainer

When adding or reactivating a maintainer:

1. Decide the responsibility area and the minimum GitHub role required.
2. Update [`.github/CODEOWNERS`](../.github/CODEOWNERS),
   [`GOVERNANCE.md`](../GOVERNANCE.md), and
   [`docs/maintainer-rotation.md`](./maintainer-rotation.md) if review routing
   or public ownership expectations change.
3. Grant the minimum repository role needed for the agreed work.
4. Review the current maintainer source-of-truth docs:
   [`docs/maintainer-guide.md`](./maintainer-guide.md),
   [`docs/repository-settings-checklist.md`](./repository-settings-checklist.md),
   [`docs/ruleset-policy.md`](./ruleset-policy.md),
   [`docs/review-policy.md`](./review-policy.md),
   [`docs/issue-triage.md`](./issue-triage.md),
   [`SECURITY.md`](../SECURITY.md), and [`SUPPORT.md`](../SUPPORT.md).
5. If admin access is required, confirm the maintainer understands that manual
   GitHub setting changes must also update the matching public docs.
6. If the maintainer will manage releases or external credentials, rotate or
   scope those credentials so they do not depend on a previous maintainer's
   personal setup.

## Offboarding Or Access Reduction

When a maintainer leaves or no longer needs elevated access:

1. Remove or downgrade the GitHub repository role first.
2. Update [`.github/CODEOWNERS`](../.github/CODEOWNERS),
   [`GOVERNANCE.md`](../GOVERNANCE.md), and
   [`docs/maintainer-rotation.md`](./maintainer-rotation.md) if the public
   ownership model changed.
3. Remove access to any repository environments, secrets-management paths, or
   external release credentials that were granted for repository operations.
4. Rotate credentials if the departing maintainer could read or export them.
5. Hand off open release, triage, or repository-admin work explicitly rather
   than leaving ownership implied.
6. Update [`docs/repository-settings-checklist.md`](./repository-settings-checklist.md)
   if the live admin roster or manual setting assumptions changed.

## Access Review Cadence

Review maintainer access at least once per quarter and also when:

- a maintainer is added, removed, or changes responsibility areas
- admin access is granted temporarily for incident response or migration work
- rulesets, branch protection, Discussions, Pages, or environments change
- a security incident or credential-rotation event affects repository access

Record the quarterly review in the scheduled maintainer issue created by
`.github/workflows/quarterly-maintainer-review.yml`, or create an equivalent
manual issue if the automation is unavailable.
Close that issue with the standard summary fields from
`docs/quarterly-maintainer-review.md` so access-review outcomes stay auditable.

## Access Review Checklist

During an access review, compare the live repository state against:

- [`.github/CODEOWNERS`](../.github/CODEOWNERS)
- [`GOVERNANCE.md`](../GOVERNANCE.md)
- [`docs/maintainer-rotation.md`](./maintainer-rotation.md)
- [`docs/maintainer-guide.md`](./maintainer-guide.md)
- [`docs/repository-settings-checklist.md`](./repository-settings-checklist.md)
- [`docs/ruleset-policy.md`](./ruleset-policy.md)

Confirm:

- every maintainer still needs their current repository role
- admin access is limited to maintainers who actually manage manual settings
- required-check names and ruleset assumptions still match the live settings
- CODEOWNERS routing still reflects the real review surface
- saved replies, support routing, and security routing still point to the
  current maintainers and docs
- credentials or secrets exposed through repository operations have a clear
  current owner

## Temporary Elevated Access

- Temporary admin access for incident response or settings migration is
  acceptable when a lower role cannot complete the work.
- Downgrade that access after the incident or migration is complete.
- Document the reason and any follow-up settings changes in the pull request,
  issue, or maintainer notes tied to the work.
