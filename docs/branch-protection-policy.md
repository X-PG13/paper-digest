# Branch Protection Policy

This document records the intended branch-protection posture for the `main`
branch. GitHub repository settings must be configured manually to match it.

## Protected Branch

- Protect `main`.
- Treat `main` as the only supported default branch unless the public docs say
  otherwise.

## Intended Rules

When GitHub settings allow it, enable at least these protections:

1. Require pull requests before merging.
2. Require at least one approving review.
3. Dismiss stale approvals when new commits are pushed.
4. Require review from code owners.
5. Require all review conversations to be resolved.
6. Require the stable branch-protection check contexts to pass.
7. Block force pushes and branch deletion.

The required GitHub check contexts are:

| Required workflow | Required check context |
| --- | --- |
| `CI` | `verify / verify` |
| `Dependency Review` | `dependency-review` |
| `Workflow Lint` | `actionlint` |

`PR Hygiene` remains an advisory `pull_request_target` workflow. It should
comment on missing docs, changelog, or issue-link context, but it should not be
configured as a required branch-protection check unless the review policy also
changes from advisory to blocking.

## Merge Hygiene

- Prefer squash merges on `main`.
- Keep direct pushes disabled unless a maintainer is handling a narrow repair
  that cannot reasonably wait for the normal pull-request path.
- If repository settings temporarily diverge from this policy, note the reason
  in the relevant pull request or maintainer work item.

## Keeping Policies Aligned

When changing review or protection expectations, update together:

- `docs/review-policy.md`
- this document
- `docs/maintainer-guide.md`
- any workflow names or labels referenced by protected status checks

## Repository Features Not Enforced Here

- GitHub Discussions category setup should follow `docs/discussions-policy.md`.
- Proposal and ADR handling should follow `GOVERNANCE.md`,
  `docs/roadmap-policy.md`, and `docs/adr/README.md`.
- Other repository-admin settings such as merge strategy, Pages source, and
  security toggles should follow `docs/repository-settings-checklist.md`.
- Repository rulesets and future merge-queue posture should follow
  `docs/ruleset-policy.md`.
