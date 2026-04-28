# Releasing

This project uses Git tags to trigger release builds.

Open a `Release preparation` issue from `.github/ISSUE_TEMPLATE/` before
pushing the tag, and keep that issue updated through the release cut.
After the GitHub release is published, use the post-release follow-up issue
from `.github/ISSUE_TEMPLATE/` or the release-triggered follow-up workflow to
track immediate verification and next-cycle setup.
Use `docs/release-cadence-policy.md` for timing and scope expectations, and
`docs/release-lifecycle-runbook.md` for the artifact-linkage order across the
whole release lifecycle.
Use `docs/operations-history.md` as the canonical index for release-cycle
history once a release is published.

## Before Tagging

1. Ensure `CHANGELOG.md` is updated.
2. Confirm the version in `paper_digest/__about__.py`.
3. Confirm any compatibility or workflow claim changes are reflected in:

- `README.md`
- `docs/compatibility-matrix.md`
- `docs/maintainer-guide.md`
- `docs/review-policy.md` or `docs/branch-protection-policy.md` when review or
  required-check expectations changed
- `.github/release.yml` when release-note categories changed

4. Run the full verification suite:

```bash
make check
make build
make release-check
make release-dry-run
```

`make release-dry-run` is the single local pre-tag command for the release
path. It composes `make check`, `make build`, and `make release-check`, so use
the component commands above only when you need to isolate a failure.

If the cycle changed required GitHub checks, confirm
`docs/branch-protection-policy.md` still names the active set.
If the cycle changed merge policy, Pages behavior, or other repository-admin
settings, confirm `docs/repository-settings-checklist.md` still matches the
intended GitHub configuration.
If the cycle changed maintainer access, repository-admin settings, rulesets, or
other operator-facing GitHub configuration, confirm the latest quarterly review
issue is current and links back to the relevant follow-up work.
Keep the release-preparation issue linked from the release-preparation pull
request or maintainer notes for the cycle.
If the cycle is being deferred rather than released, note that decision in the
release-preparation issue and follow `docs/release-cadence-policy.md`.

## Draft Release Notes

Before pushing the tag, prepare a short release summary using the same
categories every time:

1. Highlights: the most important user-visible additions or fixes.
2. Config or workflow changes: anything operators need to reconfigure.
3. Compatibility notes: Python, runner, or integration support changes.
4. Upgrade notes: anything that requires manual follow-up after release.
5. Repository-operations notes: any maintainer-facing setting, access, or
   workflow policy changes worth linking back to the latest quarterly review.

Generated GitHub release notes are categorized through `.github/release.yml`.
If labels or categories changed during the cycle, confirm the generated notes
still group changes as expected before publishing.
If workflow names or required checks changed, confirm
`docs/branch-protection-policy.md` still matches the intended repository
settings before publishing.
If repository-settings or access-review work happened in the cycle, link the
latest quarterly review issue in the release-preparation pull request or
maintainer notes.
Use the release-preparation issue to record changelog intent, compatibility
checks, and operator-facing release notes before the tag is pushed.

## Release Dry Run

Before pushing a tag, run a release dry run locally:

```bash
make release-dry-run
```

For a GitHub Actions dry run, dispatch the release workflow without publishing:

```bash
gh workflow run release.yml --ref <branch-or-tag> -f dry_run=true
```

The dry run builds the same `package-dist` artifact as the tag path and verifies
that both a wheel and source archive are present. Publishing remains gated to a
tag push, or to an explicit manual dispatch on a tag with `dry_run=false`.

## Create a Release

1. Commit the release changes.
2. Create and push a tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

3. The GitHub Actions release workflow will build the package, validate it, and
   attach the artifacts to a GitHub release.

## After Release

1. Open or confirm the `Post-release follow-up` issue and keep it linked from
   the release-preparation issue.
   If repository-operations changes shipped, record the linked quarterly review
   issue there as well.
2. Close the release-preparation issue only after the post-release follow-up
   issue is linked there and any remaining immediate follow-up work is linked
   or stated as `none`.
3. Verify that the GitHub release contains both the wheel and source archive.
4. Verify that the generated release notes match the final `CHANGELOG.md`
   entry and any compatibility statements made in `README.md` and
   `docs/compatibility-matrix.md`.
5. Bump the version for the next development cycle if needed.
6. Add or confirm a fresh `Unreleased` section in `CHANGELOG.md`.
7. Capture any release retrospective or operator-facing follow-up in the
   post-release issue before closing it, and link remaining work or say
   `none` explicitly.
8. If the cycle exposed cadence or process strain, capture that in the
   post-release issue and update `docs/release-cadence-policy.md` or
   `docs/release-lifecycle-runbook.md` when the process itself changed.
9. Update `docs/operations-history.md` so the published release and any
   lifecycle artifacts are visible from the long-lived index.
