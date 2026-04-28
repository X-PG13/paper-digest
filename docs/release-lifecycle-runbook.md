# Release Lifecycle Runbook

This document defines the canonical release lifecycle for Paper Digest.

Use it as the source of truth for how quarterly maintainer review, release
preparation, tag publishing, and post-release follow-up should connect.

## Lifecycle Order

The normal order is:

1. Quarterly maintainer review if repository-settings, rulesets, or access work
   changed in the cycle.
2. Release-preparation issue and release-preparation pull request.
3. Tag push and GitHub release publication.
4. Post-release follow-up issue and next-cycle setup.

Not every release needs fresh quarterly-review work, but every release should
explicitly decide whether the latest quarterly review is still current.

## Required Artifacts

The lifecycle should leave these public records when applicable:

- a quarterly maintainer review issue
- a release-preparation issue
- a release-preparation pull request or equivalent maintainer notes
- the Git tag and GitHub release
- a post-release follow-up issue

## Linkage Rules

Keep these links explicit:

- The release-preparation issue should link the latest quarterly review issue
  whenever repository-operations changes shipped or were validated during the
  cycle.
- The release-preparation pull request should link the release-preparation
  issue.
- The post-release follow-up issue should link the release-preparation issue.
- Once the post-release issue exists, update the release-preparation issue so
  the forward link is visible from both ends.
- If repository-operations changes shipped in the release, the post-release
  follow-up issue should link the latest quarterly review issue or explain why
  the previous review still remains current.
- If the post-release issue uncovers follow-up work, link the resulting issue
  or pull request before closing it.
- Once the release is complete, update `docs/operations-history.md` so the
  lifecycle artifacts are visible from the long-lived index.

## Release-Prep Responsibilities

During release preparation, maintainers should:

- confirm scope, changelog intent, and compatibility claims
- run the local release dry run before the tag is pushed
- use the GitHub Actions dry run when workflow or packaging behavior changed
- decide whether the latest quarterly review is still current
- prepare operator-facing notes for workflow, settings, or repository-operations
  changes
- leave enough context in the release-preparation issue that the tag choice is
  reviewable later

## Post-Release Responsibilities

After publication, maintainers should:

- verify the published release artifacts and release notes
- verify that compatibility claims still match `README.md` and
  `docs/compatibility-matrix.md`
- confirm next-cycle setup such as a fresh `Unreleased` section
- capture release retrospective notes while they are still fresh
- close the post-release issue with a short summary of what was verified and
  what remains tracked elsewhere

## Issue Close-Out Expectations

- Close quarterly maintainer review issues with a short summary, and write
  `none` explicitly when no changes or follow-up work were needed.
- Close release-preparation issues only after the post-release follow-up issue
  is linked. If immediate follow-up work remains, link it there; otherwise say
  `none` explicitly in the closing handoff note.
- Close post-release follow-up issues with a short summary that links any
  remaining follow-up work, or says `none` explicitly when nothing remains.

## Manual Fallback

- If a workflow cannot create the expected issue automatically, create the
  matching issue manually from the issue form and keep the same linkage rules.
- If a release happens under incident pressure, record the deviation in the
  release-preparation or post-release issue rather than pretending the normal
  path occurred.
