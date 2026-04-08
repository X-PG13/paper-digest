# Maintainer Guide

## Local Workflow

Use the standard local checks before merging:

```bash
make check
make coverage
```

If you contribute regularly, install pre-commit hooks:

```bash
pre-commit install
```

## Reviewing Changes

Prefer pull requests that separate these concerns:

- Product behavior changes.
- Refactors with no user-visible effect.
- Tooling or documentation changes.

When reviewing, focus first on:

1. Behavior regressions.
2. API or config compatibility.
3. Test coverage for the changed logic.
4. Documentation drift.

## Dependency Policy

- Runtime dependencies should stay minimal.
- Development tooling can grow when it clearly improves repository health.
- Dependabot updates should be batched when many small upgrades land together.

## Release Ownership

Follow the checklist in `RELEASING.md`.

The tag format is `vX.Y.Z`, for example `v0.2.0`.
