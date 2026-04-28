# ADR Guide

Architecture Decision Records capture decisions that create lasting technical or
operational constraints for the repository.

## When To Write An ADR

Write an ADR when a change:

- Introduces a lasting architecture boundary or extension strategy.
- Changes governance, workflow ownership, or release-critical maintenance
  rules.
- Adds a dependency or platform commitment that is expensive to reverse later.
- Resolves a design tradeoff where the rationale should stay visible after the
  pull request is merged.

## Format

- Store ADRs in `docs/adr/`.
- Use zero-padded numeric prefixes such as `0001-...md`.
- Start from `docs/adr/0000-template.md`.
- Keep the status explicit: `Proposed`, `Accepted`, `Superseded`, or
  `Rejected`.

## Maintenance Rules

- Do not rewrite accepted ADRs as if the decision never happened. Add updates,
  superseding ADRs, or status changes instead.
- Link the relevant issue or pull request when the ADR is proposed or accepted.
- If an ADR changes contributor, governance, release, or support expectations,
  update the public docs in the same change.
