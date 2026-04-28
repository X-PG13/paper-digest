# Label Taxonomy

This document defines the repository label set that maintainers should keep in
sync with GitHub.

## Routing Labels

| Label | Purpose |
| --- | --- |
| `bug` | Confirmed or suspected defects on supported paths |
| `enhancement` | New capabilities, workflow changes, or product improvements |
| `support` | Usage and setup questions |
| `documentation` | Missing, unclear, or outdated docs |
| `maintenance` | Tooling, CI, dependency, or repository-health work |
| `security` | Security-sensitive work that should stay private unless cleared |

## Planning Labels

| Label | Purpose |
| --- | --- |
| `proposal` | Larger design, workflow, governance, or roadmap proposals |
| `dependencies` | Dependency updates and ecosystem-maintenance changes |

## Triage Status Labels

| Label | Purpose |
| --- | --- |
| `breaking` | Behavior or compatibility changes that require extra release-note attention |
| `needs-info` | The report is missing required context |
| `needs-repro` | The report needs a minimal reproduction |
| `blocked` | Maintainers cannot proceed yet |
| `stale` | No recent activity after the documented grace period |
| `ops-review` | Scheduled repository-operations review and access-audit work |
| `release-prep` | Maintainer release-preparation tracking work |
| `release-follow-up` | Maintainer post-release verification and follow-up work |
| `release-note` | The change should be called out in release notes |

## Contribution Labels

| Label | Purpose |
| --- | --- |
| `good first issue` | Suitable for a first contribution |
| `help wanted` | Maintainers welcome external implementation help |

## Resolution Labels

| Label | Purpose |
| --- | --- |
| `duplicate` | Covered by another tracked issue or pull request |
| `invalid` | Not actionable as filed |
| `wontfix` | Intentionally not planned |

## Usage Rules

1. Every public issue should have one routing label.
2. `proposal` and `dependencies` are optional amplifying labels, not required
   routing labels.
3. Add at most one or two status labels at a time; do not turn labels into a
   timeline dump.
4. `needs-info` and `needs-repro` should be paired with a concrete maintainer
   reply explaining what is missing.
5. `release-note` means the change should appear in both `CHANGELOG.md` and the
   generated GitHub release notes categories.
6. `security` should not be used for public disclosure of unpatched
   vulnerabilities. Redirect those reports to `SECURITY.md`.
7. `documentation` should be used for docs-only follow-up work, including gaps
   surfaced by a closed or redirected report.
8. `documentation` may be applied automatically to pull requests that touch
   public docs or Markdown entry points, and maintainers should also use it for
   docs-only follow-up work.
9. `duplicate` and `wontfix` are manual resolution labels. Automation should
   not add them; maintainers should apply them when closing with the canonical
   tracking link or the relevant scope or policy reason.
10. `invalid` is a manual resolution label. Automation should not add it; use
    it only when a report is not actionable as filed and the concrete reason or
    correct intake path has already been explained.
11. Use `blocked` when maintainers cannot proceed because an external
    dependency or explicit maintainer decision is still pending, and the
    blocker should be linked.
12. `release-note` means the change should appear in both `CHANGELOG.md` and
    the generated GitHub release notes, and `.github/release.yml` should stay
    aligned with that label.
13. `documentation` follow-up issues still use the standard stale timer unless
    another exempt maintainer-work label applies.
14. `blocked` and `release-note` stay exempt from stale on both issues and
    pull requests until the label is cleared.
15. `enhancement` is the routing label for scoped feature work that does not
    need proposal-level scoping, and the feature-request and proposal forms
    should keep that label aligned.
16. `maintenance` covers CI, tooling, dependency, and repository-health work,
    including scheduled maintainer review and post-release follow-up issues.
17. `breaking` should be used only when compatibility or workflow behavior
    changes require explicit upgrade guidance; pair it with `release-note`
    when the shipped change must be called out publicly.
18. `good first issue` and `help wanted` are manual contributor-facing labels.
    Use `good first issue` only when the task is intentionally small,
    well-scoped, and suitable for a first external contribution.
19. `help wanted` should mark work where maintainers welcome outside
    implementation help even if the task still needs more repository context.
20. `good first issue` and `help wanted` stay exempt from stale on issues so
    curated contributor entry points remain discoverable.
21. `needs-info` and `needs-repro` are maintainer follow-up labels, not
    routing labels. `needs-repro` should mean a concrete minimal reproduction
    is still required before work can continue.
22. `stale` is the automation-managed inactivity label and should not replace
    direct maintainer triage or closure decisions.
23. `ops-review`, `release-prep`, and `release-follow-up` are reserved for
    scheduled maintainer lifecycle issues and stay exempt from stale issue
    closure.

## Automation

- `.github/labels.json` is the source of truth for label names, colors, and
  descriptions.
- `.github/ISSUE_TEMPLATE/feature_request.yml` uses `enhancement`, and
  `.github/ISSUE_TEMPLATE/proposal.yml` keeps `enhancement` plus `proposal`
  aligned for design-first work.
- `.github/ISSUE_TEMPLATE/config.yml` keeps security, support, and proposal
  contact links aligned with the public routing docs.
- `.github/workflows/label-sync.yml` syncs that file into the repository label
  set through `tools/sync_repository_labels.py`.
- `.github/workflows/stale.yml` uses the taxonomy for inactivity handling and
  keeps `blocked` and `release-note` exempt on both issues and pull requests,
  while `good first issue` and `help wanted` stay exempt on issues so curated
  contributor entry points remain visible.
- `.github/workflows/community-triage.yml` adds `needs-info` to incomplete bug
  and support intake, while `needs-repro` remains maintainer-applied after a
  concrete reproduction request.
- `.github/workflows/community-triage.yml` uses `needs-info`,
  `documentation`, `maintenance`, `dependencies`, and `proposal` for intake
  automation, while `duplicate`, `invalid`, and `wontfix` remain
  maintainer-applied resolution labels.
- `.github/workflows/community-triage.yml` path-based PR intake uses
  `maintenance` for workflow, tooling, and repository-health changes.
- `.github/dependabot.yml` and dependency-maintenance workflows use
  `dependencies` together with `maintenance` for automated dependency intake.
- `.github/release.yml` uses `breaking`, `enhancement`, `maintenance`, and
  `release-note` to keep generated GitHub release-note categories aligned.
- `.github/release.yml` uses `release-note` to keep generated GitHub release
  notes categories aligned, while `invalid` stays excluded from generated
  notes.
- `.github/workflows/quarterly-maintainer-review.yml` uses `maintenance` and
  `ops-review` for scheduled maintainer review issues.
- `.github/ISSUE_TEMPLATE/release_preparation.yml` keeps `release-prep`
  aligned with the maintainer release lifecycle.
- `.github/ISSUE_TEMPLATE/post_release_follow_up.yml` and
  `.github/workflows/post-release-follow-up.yml` keep `release-follow-up`
  aligned with the maintainer release lifecycle.
- `.github/workflows/post-release-follow-up.yml` uses `maintenance` and
  `release-follow-up` for post-release verification issues.
