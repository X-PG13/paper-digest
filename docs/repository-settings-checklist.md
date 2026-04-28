# Repository Settings Checklist

This document records the GitHub repository settings that cannot be enforced
purely through files in the repository. Treat it as the manual source of truth
for admin-facing configuration.

Maintainer role grants and access-review cadence are documented separately in
`docs/maintainer-access-policy.md`.

Use `docs/quarterly-maintainer-review.md` for the recurring issue checklist
that records repository-settings review work.

## Default Branch And Merge Strategy

- Default branch: `main`
- Allow squash merges: enabled
- Allow merge commits: disabled
- Allow rebase merges: disabled
- Automatically delete head branches after merge: enabled

If any of these differ temporarily, note the reason in maintainer work and
update this checklist if the difference becomes the new steady state.

## Branch Protection For `main`

Configure `main` so it matches `docs/branch-protection-policy.md`:

1. Require a pull request before merging.
2. Require at least one approval.
3. Dismiss stale approvals on new commits.
4. Require review from code owners.
5. Require all conversations to be resolved.
6. Require these status checks:
   `CI`, `Dependency Review`, `Workflow Lint`, `PR Hygiene`.
7. Disable force pushes.
8. Disable branch deletion.

If repository rulesets are used, keep them aligned with
`docs/ruleset-policy.md`.

## Actions And Pages

- Actions permissions default: read repository contents unless a workflow needs
  broader permissions.
- Allow GitHub Actions to create and approve pull requests: disabled unless a
  future automation explicitly requires it.
- GitHub Pages source: GitHub Actions.
- Environments:
  `github-pages` exists and is used by the Pages deployment workflows.

## Security And Dependency Settings

- Dependabot alerts: enabled if available for the repository tier.
- Dependabot security updates: enabled if available.
- Secret scanning and push protection: enabled when GitHub plan features allow
  it.
- Private vulnerability reporting: enabled when available.

These settings may depend on repository visibility or plan limits. When a
setting cannot be enabled, document that limitation in maintainer notes rather
than silently assuming it exists.

## Discussions And Intake

- GitHub issue forms are enabled through `.github/ISSUE_TEMPLATE/*.yml`.
- Blank issues remain disabled.
- Contact links route to security, support, and proposal guidance.
- If GitHub Discussions is enabled later, configure categories to match
  `docs/discussions-policy.md`.
- Personal GitHub saved replies used by maintainers should be based on
  `docs/saved-replies.md`.

## Rulesets And Merge Queue

- If repository rulesets are enabled, configure them to match
  `docs/ruleset-policy.md`.
- If merge queue is enabled in the future, document the reason, availability
  assumptions, and required-check alignment in `docs/ruleset-policy.md` and
  this checklist.
- If merge queue is not available because of repository ownership or plan
  limits, leave it disabled and keep that assumption documented rather than
  treating it as silently pending.

## Audit Checklist

Review these settings whenever:

- the quarterly access review is due
- Required workflow names change.
- Branch-protection or review policy changes.
- A new maintainer gains admin access.
- Discussions, security, or Pages settings change.
- A release cycle includes repository-operations changes.

When reviewing settings, compare:

- this file
- `docs/branch-protection-policy.md`
- `docs/review-policy.md`
- `docs/discussions-policy.md`
- `docs/maintainer-guide.md`
- `docs/ruleset-policy.md`
- `docs/saved-replies.md`
- `docs/maintainer-access-policy.md`
- `docs/quarterly-maintainer-review.md`
