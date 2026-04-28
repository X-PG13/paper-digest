# Governance

Paper Digest is currently a maintainer-led project with a narrow scope. The
goal of this document is to make ownership and decision-making explicit rather
than implicit.

## Project Model

- The project aims for clear technical discussion, rough consensus where
  practical, and maintainable implementation over broad process overhead.
- There is no formal voting system today.
- Public proposals, design tradeoffs, and compatibility changes should be
  discussed in issues or pull requests so the reasoning is visible later.
- Intended Discussions categories and fallback paths are documented in
  [`docs/discussions-policy.md`](./docs/discussions-policy.md).

## Roles

### Maintainer

Maintainers are responsible for:

- Triage and issue routing.
- Reviewing and merging pull requests.
- Release ownership and changelog quality.
- Compatibility, support, and workflow policy decisions.
- Keeping repository access aligned with public ownership and review-routing
  docs.

The live review-routing source of truth is [`.github/CODEOWNERS`](./.github/CODEOWNERS).
At the moment, those ownership sections still route to `@X-PG13`, but the file
is structured by repository surface rather than relying on a single catch-all
line.

### Contributor

Contributors can:

- Report bugs, request features, and propose workflow improvements.
- Submit documentation, test, or implementation changes.
- Participate in technical discussion on open issues and pull requests.

## Decision Model

- Small fixes and documentation changes can be decided directly in the pull
  request that implements them.
- User-visible behavior changes, compatibility changes, workflow policy
  changes, and governance changes should have explicit rationale in an issue or
  pull request description.
- When consensus is unclear or time is limited, maintainers make the final
  decision.
- Security handling follows [`SECURITY.md`](./SECURITY.md), not the normal
  public issue path.

## Proposal Path

Until GitHub Discussions is enabled as a first-class intake path, proposals
should go through:

1. A proposal or feature-request issue for the problem statement.
2. A pull request for the proposed implementation or doc change.

Major proposals should explain:

- The user or maintainer problem being solved.
- Why the change fits the current project scope.
- Compatibility, maintenance, and workflow costs.
- Any migration or rollback expectations.

Roadmap intake and prioritization rules live in
[`docs/roadmap-policy.md`](./docs/roadmap-policy.md).

## Decision Records

- Larger architecture, workflow, governance, or dependency-policy decisions
  should capture their rationale through ADRs in
  [`docs/adr/README.md`](./docs/adr/README.md).
- New ADRs should start from
  [`docs/adr/0000-template.md`](./docs/adr/0000-template.md).

## Review And Protection

- Default pull-request review expectations live in
  [`docs/review-policy.md`](./docs/review-policy.md).
- Intended `main` branch protection settings live in
  [`docs/branch-protection-policy.md`](./docs/branch-protection-policy.md).
- Maintainer onboarding, offboarding, and access-review rules live in
  [`docs/maintainer-access-policy.md`](./docs/maintainer-access-policy.md).

## Ownership Changes

When maintainer ownership changes:

1. Update `.github/CODEOWNERS`.
2. Update this file.
3. Update [`docs/maintainer-rotation.md`](./docs/maintainer-rotation.md).
4. Update [`docs/maintainer-access-policy.md`](./docs/maintainer-access-policy.md).
5. Update any support, security, or release docs affected by the change.

## Policy Changes

Changes to governance should land through normal pull requests and should
update all affected public docs in the same change.
