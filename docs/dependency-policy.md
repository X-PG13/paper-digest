# Dependency Policy

This project keeps runtime dependencies as small as practical. Dependency
updates should improve repository health without creating unnecessary review
noise.

## Scope

- Runtime dependencies should stay minimal and justify their long-term
  maintenance cost.
- Development dependencies may grow when they clearly improve correctness, test
  quality, release hygiene, or contributor experience.
- GitHub Actions versions are treated as part of the dependency surface because
  they affect CI, releases, and Pages operations.

## Update Channels

- `.github/dependabot.yml` is the automated source of routine update pull
  requests.
- `.github/workflows/dependency-review.yml` is the pull-request guardrail for
  dependency manifest changes.
- Manual upgrades are acceptable when a tooling or platform change needs to
  land faster than the normal batch window.

## Batching And Labels

- Dependabot updates should be grouped by ecosystem to keep the review queue
  readable.
- Dependency pull requests should carry the `dependencies` label and usually
  also `maintenance`.
- Broad toolchain upgrades that change contributor workflow should also update
  `CHANGELOG.md` when maintainers expect users or contributors to notice.

## Review Expectations

When reviewing dependency updates, check:

1. Whether the change affects supported Python or GitHub Actions behavior.
2. Whether CI, build, and release validation still pass.
3. Whether any docs or compatibility claims need to change.
4. Whether the upgrade can be batched with nearby updates instead of merged in
   isolation.

## Security And Urgency

- Security-relevant dependency updates should be prioritized ahead of normal
  batch cadence.
- If an urgent update changes repository operations or compatibility claims,
  update the relevant docs in the same pull request.
- Dependency upgrades that only affect unsupported paths should not expand the
  public support matrix by themselves.

## Release Notes

- Routine patch-level dependency bumps do not need standalone changelog prose.
- Higher-risk upgrades, ecosystem migrations, or GitHub Actions platform
  changes should be called out in `CHANGELOG.md`.
- If a dependency change affects release-note grouping, keep
  `.github/release.yml` aligned with the active labels.
