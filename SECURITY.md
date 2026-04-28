# Security Policy

## Supported Versions

Security fixes are only guaranteed for the newest supported line.

| Version surface | Security support |
| --- | --- |
| Latest released version | Supported |
| Current `main` branch | Best effort while preparing the next release |
| Older released versions | Not supported |
| Local forks or modified deployments | Best effort reproduction only |

## Reporting a Vulnerability

Do not open a public issue for a suspected security problem.

Instead, report the issue privately through GitHub private vulnerability
reporting for this repository when available. If private reporting is not
available, contact the maintainer through an already-established private
channel before sharing technical details publicly.

Include:

- A clear description of the vulnerability.
- Reproduction steps or a proof of concept.
- The affected version or commit hash.
- Any suggested mitigation if available.
- Any credential, token, or deployment assumptions required to reproduce it.

You should receive an acknowledgement within 5 business days.

## Disclosure Expectations

- Do not post exploit details, secrets, raw tokens, or private configuration in
  public issues, pull requests, or discussions.
- Give maintainers a reasonable chance to reproduce and mitigate the issue
  before public disclosure.
- If the report turns out to be a normal bug rather than a security issue, it
  may be redirected to the public bug-report path after sensitive details are
  removed.

## Out Of Scope

The following are generally not treated as security vulnerabilities on their
own:

- Requests for broader support of old Python versions or unsupported platforms.
- Failures caused only by invalid local configuration.
- Issues that require maintainers to inspect third-party secrets or personal
  production data.
- Availability problems in external APIs unless the project itself mishandles
  them in a security-relevant way.

For normal defects, feature requests, or usage questions, use the public
community paths described in [`SUPPORT.md`](./SUPPORT.md).
