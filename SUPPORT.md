# Support

This project is maintained with a narrow scope and best-effort community
support. Use the right intake path so issues can be triaged quickly.

## Where To Ask

- Security concern: follow [`SECURITY.md`](./SECURITY.md) and report it
  privately.
- Reproducible defect: open a bug report with a minimal reproduction.
- New capability or workflow idea: open a feature request.
- Larger product, governance, or workflow proposal: open a proposal issue.
- Usage or configuration question: open a support request only after checking
  the docs linked below.

## Read Before Opening A Support Request

- [`README.md`](./README.md)
- [`config.example.toml`](./config.example.toml)
- [`docs/config-recipes.md`](./docs/config-recipes.md)
- [`docs/compatibility-matrix.md`](./docs/compatibility-matrix.md)
- [`docs/discussions-policy.md`](./docs/discussions-policy.md)

## What Support Covers

- Clarifying documented configuration behavior.
- Explaining supported deployment paths such as local CLI runs or GitHub
  Actions workflows.
- Identifying whether a report is a bug, feature gap, unsupported setup, or
  documentation problem.

## What Support Does Not Cover

- Private consulting for research workflow design.
- Debugging third-party credentials or secrets you cannot redact safely.
- Support for unsupported runtimes, old releases, or heavily modified forks.
- Long-term maintenance branches for older versions.

## Response Expectations

- Support and issue triage are best effort, not an SLA.
- Security reports are acknowledged under the timeline in `SECURITY.md`.
- Support requests that skip the documented pre-read list or omit the minimum
  environment context may receive an automated `needs-info` reminder.
- Public issues may be closed when they lack the requested reproduction or
  environment details, target an unsupported setup, or duplicate an existing
  report.
- Maintainers may apply labels such as `needs-info`, `needs-repro`, or
  `stale` according to `docs/issue-triage.md` and `docs/label-taxonomy.md`.

## What To Include

For faster help, include:

- What you are trying to do, and where you are blocked.
- The exact command you ran.
- A minimal config snippet with secrets removed.
- The Python version and operating system.
- The project version, tag, or commit hash.
- The exact error output or the smallest observable incorrect behavior.
