# Post-Release Checklist

This document defines the maintainer follow-up work that should happen after a
tagged GitHub release is published.

The post-release follow-up issue created by
`.github/workflows/post-release-follow-up.yml` should use this checklist as its
source of truth.

## Immediate Validation

After the release is live, confirm:

- the GitHub release contains the expected wheel and source archive
- the generated release notes match `CHANGELOG.md`
- compatibility claims in `README.md` and
  `docs/compatibility-matrix.md` still match the published release
- any operator-facing workflow, settings, or repository-operations notes are
  visible in the release-preparation issue and release notes

## Repository Follow-Up

For the next development cycle, confirm:

- the next-version or development-version follow-up is tracked if needed
- `CHANGELOG.md` has an `Unreleased` section ready for new work
- any quarterly maintainer review linkage remains valid for repository-setting
  or access changes that shipped in the release
- any deferred release-preparation follow-up work is linked from the post-release
  issue
- `docs/operations-history.md` reflects the published release and its linked
  lifecycle artifacts

## Retrospective Prompts

Use the follow-up issue to capture anything maintainers should learn from the
release process:

- What went smoothly?
- What was manual, repetitive, or unclear?
- Did any docs, labels, or templates drift during release prep?
- Is any workflow, policy, or automation follow-up needed before the next tag?

## Close-Out Expectations

When the post-release follow-up finishes:

<!-- BEGIN GENERATED: post-release-close-out -->
- close the issue with a short summary of what was verified or changed
- link any follow-up pull request or maintenance issue
- note explicitly if no additional work was needed
<!-- END GENERATED: post-release-close-out -->

## Follow-Up Summary Template

<!-- BEGIN GENERATED: post-release-summary -->
```md
## Post-Release Summary

- Release: vX.Y.Z
- Verified by: @maintainer
- Artifacts and release notes: confirmed | short summary
- Compatibility and docs drift: none | short summary
- Next-cycle setup: complete | short summary
- Retro follow-up: none | issue or PR links
- Additional repository-operations follow-up: none | short summary
```

Write `none` explicitly when no additional work was required.
The release-triggered workflow should prefill the mutable status fields as
`confirmed`, `none`, `complete`, `none`, and `none`; replace those defaults
with a short summary or issue/PR links only where follow-up exists.
<!-- END GENERATED: post-release-summary -->

## Manual Fallback

- If the post-release workflow cannot open the issue, create one manually from
  the post-release follow-up issue form under `.github/ISSUE_TEMPLATE/`.
