# Saved Replies

GitHub saved replies are tied to individual maintainer accounts, not the
repository itself. This file keeps the canonical reply text in version control
so maintainers can create or update their personal saved replies consistently.

## `needs-info`

Thanks for the report. This issue is still missing some of the minimum context
required for deeper triage.

Please update the issue with:

- the exact command or workflow path
- a minimal config snippet with secrets removed
- the observed result and expected result
- Python version, OS, and project version or commit

Once that context is added, maintainers can evaluate the report on a supported
path.

## `needs-repro`

Thanks for the report. Maintainers still need a minimal reproduction before
this can move forward.

Please narrow the report to the smallest config, command, or workflow path that
still shows the problem, and include the exact output you see.

## `support-redirect`

This looks more like a usage or configuration question than a confirmed defect.

Please continue through the support path in `SUPPORT.md` after checking the
pre-read docs listed there, and include:

- What you are trying to do, and where you are blocked.
- The exact command you ran.
- A minimal config snippet with secrets removed.
- The Python version and operating system.
- The project version, tag, or commit hash.
- The exact error output or the smallest observable incorrect behavior.

If the behavior turns out to be a reproducible bug on a supported path, we can
reopen or convert it.

## `security-redirect`

Please do not continue this report in public.

Potential security issues should follow the private reporting path documented in
`SECURITY.md`. If you can still edit the public issue, remove any exploit
details, secrets, tokens, or private configuration before maintainers continue.

## `duplicate`

Thanks for the report. This is being tracked elsewhere, so I am closing this as
a duplicate.

Canonical tracking issue or pull request:
- link here

If you have new reproduction details that are not already covered there, add
them on the canonical thread.

## `out-of-scope`

Thanks for the proposal. This is outside the current documented scope of Paper
Digest, so maintainers are not planning to take it on right now.

If the repository scope changes later, or if you want to prototype the idea in
a fork first, a future proposal can link back to that work.

## `docs-follow-up`

Thanks. This surfaced a docs gap even if the immediate report is being closed
or redirected.

Maintainers should either:

- update the relevant public docs in this cycle, or
- file/link a follow-up documentation issue so the gap stays tracked.

## Maintenance Notes

- Keep the titles short enough to be easy to pick from GitHub's saved-reply UI.
- When these canonical texts change, update the corresponding saved replies in
  personal GitHub settings.
- If a maintainer adds a new high-frequency reply, add it here so the shared
  baseline stays visible.
