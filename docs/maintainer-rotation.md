# Maintainer Rotation

Paper Digest is still effectively a single-maintainer project, but this file
defines how ownership should be distributed as additional maintainers appear.

## Current State

- Review routing currently points to `@X-PG13` through `.github/CODEOWNERS`.
- Until more maintainers are added, no formal rotation is active.
- Even without active rotation, this document exists so the project does not
  rely on undocumented habits.

## Responsibility Areas

When multiple maintainers exist, rotate or explicitly assign these areas:

- Issue triage and support routing.
- Pull request review and merge decisions.
- Release preparation and post-release follow-up.
- Workflow and documentation maintenance.

## Rotation Guidance

- Rotate release ownership by release or by explicit agreement.
- Rotate issue-triage ownership on a lightweight cadence that the current
  maintainer set can actually sustain.
- Announce ownership changes in pull requests when they affect public docs or
  workflow expectations.

## Adding A Maintainer

When adding a maintainer:

1. Update `.github/CODEOWNERS`.
2. Update [`GOVERNANCE.md`](../GOVERNANCE.md).
3. Update [`docs/maintainer-access-policy.md`](./maintainer-access-policy.md).
4. Update this file if responsibilities or rotation expectations changed.
5. Update support, security, or release docs if contact or ownership language
   changed.

## Inactivity And Handoffs

- If a maintainer expects a period of unavailability, document the temporary
  handoff in the relevant pull request or release preparation work.
- If rotation is active, hand off open release or triage work explicitly rather
  than leaving it implied.
- If availability changes also require repository-role changes, follow
  `docs/maintainer-access-policy.md` rather than treating that as an informal
  side effect of the handoff.
- If the project remains single-maintainer, treat this file as the checklist
  for future expansion rather than pretending a rotation already exists.
