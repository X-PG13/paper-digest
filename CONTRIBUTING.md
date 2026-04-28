# Contributing

Thanks for considering a contribution.

## Development Setup

1. Create and activate a virtual environment.
2. Install the project in editable mode with development tools:

```bash
python -m pip install -e '.[dev]'
```

3. Copy the example configuration:

```bash
cp config.example.toml config.toml
```

## Local Checks

Run the full local verification loop before opening a pull request:

```bash
make check
make build
make release-check
```

For release-preparation pull requests, run the composed release dry run:

```bash
make release-dry-run
```

If a pull request is mostly documentation or policy work, you can use the
faster docs-only guardrail while iterating:

```bash
make docs-check
```

If a pull request changes issue forms, labels, saved replies, triage policy, or
release-lifecycle contract data, run the policy-only guardrail while iterating:

```bash
make policy-check
```

For a machine-readable policy report, use:

```bash
make policy-check-json
```

For a GitHub-step-summary-friendly policy Markdown report, use:

```bash
make policy-check-markdown
```

To write that same policy report to a stable file for CI upload or local
post-processing, use `python tools/check_policies.py --json-report-file
reports/policy-check-report.json`.

To re-render policy-check GitHub Actions annotations or Markdown from that JSON
artifact, use `python tools/render_policy_report.py
reports/policy-check-report.json --format github-annotations` or `python
tools/render_policy_report.py reports/policy-check-report.json --format
markdown`.

If you need the same guardrail in machine-readable form, use:

```bash
make docs-check-json
```

If you need the same guardrail as a GitHub-step-summary-friendly Markdown
report, use:

```bash
make docs-check-markdown
```

If you need the JSON report and Markdown summary persisted to files for
debugging or CI experiments, use `python tools/check_docs.py
--json-report-file reports/docs-check-report.json --markdown-report-file
reports/docs-check-summary.md`.

If you need to render GitHub Actions annotations or re-render Markdown from
that JSON artifact, use `python tools/render_docs_report.py
reports/docs-check-report.json --format github-annotations` or
`python tools/render_docs_report.py reports/docs-check-report.json --format
markdown` or `python tools/render_docs_report.py
reports/docs-check-report.json --format pr-comment`.

The current docs-check JSON artifact is schema v4 and carries stable `check_id`
values plus structured findings with `message`, `severity`, and best-effort
`path` / `line` / `end_line` metadata.
Most repository-local checks now emit those findings natively, so annotations do
not depend solely on legacy string parsing.
Markdown-section, issue-form, and workflow-template checks now also attach
source line ranges when their parser can resolve a stable origin.
The reusable Python verification workflow now also publishes a PR-comment body
artifact rendered from the same JSON report, and a trusted `workflow_run`
follows that CI run to mirror failing docs-check results into the pull request
thread from the default branch renderer.
The dedicated `Workflow Lint` CI job now also uses the same pinned
`make workflow-tools` + `make workflow-check` path as local workflow linting,
so `actionlint` version drift is not hidden behind different local/CI setup.

If you change quarterly-review or post-release lifecycle templates, sync the
managed lifecycle blocks first:

```bash
python tools/sync_lifecycle_docs.py
```

To generate a sample digest locally:

```bash
make run
```

To keep local commits clean, install the pre-commit hooks:

```bash
pre-commit install
```

To lint GitHub Actions workflows locally:

```bash
make workflow-tools
make workflow-check
```

`tools/check_workflows.py` looks for `actionlint` in `ACTIONLINT_BIN`, then
`.tools/actionlint/actionlint`, then `PATH`.
`make workflow-tools` installs the pinned `actionlint` release into
`.tools/actionlint/actionlint` and verifies its checksum before replacing the
repo-local binary.
`make workflow-check` validates workflow YAML with `actionlint`; `make check`
also runs the workflow contract suite, which verifies behavior wiring such as
permissions, triggers, artifact paths, and repo-local helper calls.

## User Feedback And Support Signals

Use the public issue forms to turn real usage into maintainable follow-up:

- Bug reports should include the source, delivery channel, config surface, or
  workflow involved, plus the failing command or run link when available.
- Support requests should describe the setup path, such as local CLI, Feishu
  webhook, GitHub Actions schedule, or archive Pages deployment.
- Feature requests should state the source, delivery, ranking, archive, or
  maintainer workflow being proposed and whether the request affects config.

Security issues should follow `SECURITY.md`. General support expectations live
in `SUPPORT.md`.

## Pull Request Guidelines

- Keep changes focused and explain the user-facing impact.
- Add or update tests for behavior changes.
- Update `README.md` and `CHANGELOG.md` when the change affects usage or release notes.
- Update `config.example.toml` and `docs/config-recipes.md` when common setup paths change.
- Update `docs/compatibility-matrix.md` when runtime, platform, or workflow support claims change.
- Update `docs/maintainer-guide.md` and `RELEASING.md` when workflows, release steps, or repository operations change.
- Update `docs/maintainer-operations-hub.md` when the maintainer docs set gains
  a new source-of-truth page or the maintainer navigation model changes.
- Keep repository-local Markdown links and heading anchors valid by running
  `make docs-check` when docs or policy pages move, and when GitHub issue forms
  or workflows reference repository docs. The same guardrail also checks that
  the README docs map, maintainer source-of-truth pages, and release-lifecycle
  docs stay aligned, and that maintainer issue summary templates do not drift
  from their source-of-truth docs. It also checks release-lifecycle cross-link
  fields, close-out rules, and default summary semantics across quarterly
  review, release-preparation, and post-release artifacts, using structured
  parsing of workflow body sections and issue-form fields against the repo-local
  schema in `tools/lifecycle_contracts.py` plus maintainer-doc registry
  contracts and docs-check repository-boundary config in
  `tools/docs_contracts.py`, plus generic repository-link resolution and anchor
  validation in `tools/docs_links.py`, plus generic source reading and
  workflow-section caching in `tools/docs_sources.py`, plus generic
  contract-assertion and text-normalization helpers in
  `tools/docs_assertions.py`, plus maintainer-doc registry checks in
  `tools/docs_registry_checks.py` and lifecycle contract executors in
  `tools/lifecycle_checks.py`, plus the declarative docs-check pipeline in
  `tools/docs_pipeline.py`, including phase report labels and
  command/reporting config plus JSON/Markdown report rendering, and it fails if
  managed lifecycle blocks were not re-synced. The shared GitHub Actions
  verification workflow now publishes that Markdown summary to the GitHub step
  summary, emits GitHub annotations through `tools/render_docs_report.py`, and
  uploads both report files as the `docs-check-report` artifact. A trusted
  `workflow_run` then re-renders the same PR-comment body from the JSON artifact
  before updating or deleting the PR comment. That JSON artifact now carries
  structured findings rather than only flat error strings, so annotations and
  PR diagnostics can use best-effort file/line locations when they are known.
- Update `tools/docs_contracts.py` in the same pull request when the README
  docs map, maintainer-operations hub source-of-truth table, maintainer guide
  governance-doc coverage rules, or docs-check repository reference / skip
  boundaries change.
- Update `tools/docs_parser.py` in the same pull request when the generic
  Markdown or GitHub metadata scanning, link extraction, issue-form parsing,
  or workflow-body parsing behavior changes.
- Update `tools/docs_links.py` in the same pull request when the generic
  repository-link resolution, anchor validation, or Markdown/GitHub metadata
  reference checking behavior changes.
- Update `tools/docs_sources.py` in the same pull request when the generic
  `TextSource` reading, Markdown section lookup, or workflow-section caching
  behavior changes.
- Update `tools/docs_assertions.py` in the same pull request when the generic
  docs-contract field/item assertion wording or text-normalization behavior
  changes.
- Update `tools/docs_registry_checks.py` in the same pull request when the
  maintainer-doc registry alignment rule between README, the maintainer hub,
  and the maintainer guide changes.
- Update `tools/lifecycle_checks.py` in the same pull request when
  release-lifecycle, maintainer-issue, linkage, close-out, or summary-semantics
  contract execution changes.
- Update `tools/docs_pipeline.py` in the same pull request when docs-check
  execution order, shared context inputs, phase labels, exit-code/reporting
  behavior, failure-summary formatting, JSON report shape / finding schema, or the
  success-message template changes.
- Update `tools/check_policies.py` in the same pull request when adding,
  removing, or renaming a repo-local policy validator, so `make policy-check`
  remains the local source of truth for policy-contract schema validation.
- Update `tools/render_docs_report.py` in the same pull request when the
  docs-check JSON schema is consumed differently for GitHub annotations or
  Markdown re-rendering.
- Update `tools/check_workflows.py` in the same pull request when local
  `actionlint` discovery rules or workflow-check operator guidance change.
- Update `tools/install_actionlint.py` in the same pull request when the
  pinned `actionlint` version, supported bootstrap targets, checksum set, or
  repo-local install path changes.
- Update `tools/sync_marker_comment.py` in the same pull request when managed
  marker-comment synchronization behavior changes for PR hygiene, community
  triage, or docs-check PR comment automation.
- Update `tools/github_api.py` in the same pull request when shared workflow
  helper GitHub API transport behavior changes, including pagination, request
  headers, JSON body handling, or ignored HTTP status rules.
- Update `tools/github_resources.py` in the same pull request when shared issue
  comments, issue labels, workflow artifacts, or pull-request files resource
  wiring changes.
- Update `tools/github_services.py` in the same pull request when the shared
  workflow-helper service layer changes how managed comment sync, label sync,
  workflow artifact lookup, or pull-request file listing is orchestrated.
- Update `tools/workflow_path_policy.py` in the same pull request when shared
  workflow-helper path classification rules for docs, runtime/ops,
  maintenance, governance, changelog, or tests change.
- Update `tools/pr_policy.py` and `.github/pull_request_template.md` together
  when PR-template checkbox labels, linked-issue field wording, or PR-hygiene
  reminder copy changes.
- Update `tools/repository_settings_policy.py`,
  `docs/branch-protection-policy.md`, `docs/repository-settings-checklist.md`,
  `docs/ruleset-policy.md`, and the referenced workflow files together when
  required checks, repository-settings cross-links, or PR-facing workflow
  names/triggers change.
- Update `tools/issue_intake_policy.py` and
  `.github/ISSUE_TEMPLATE/bug_report.yml` together when bug-report section
  labels, form name/title, required field wording, placeholder semantics, or
  community-triage reminder copy changes.
- Update `tools/intake_policy_base.py` in the same pull request when the
  shared intake-policy doc-path, key/label, contact-link, or
  snippet-collection helpers change.
- Update `tools/support_policy.py`, `SUPPORT.md`,
  `.github/ISSUE_TEMPLATE/support_request.yml`, and
  `.github/ISSUE_TEMPLATE/config.yml` together when support pre-read docs,
  support-request form name/title, field wording, support reminder copy, or
  support routing/contact-link wording changes.
- Update `tools/issue_form_policy.py` in the same pull request when GitHub
  issue form names, title prefixes, field labels, or requiredness change across
  bug, support, feature, proposal, release-preparation, or post-release forms.
  Label-policy and release-lifecycle issue-form path groups should reference
  that registry instead of re-declaring form paths, labels, or identity
  snippets.
  Bug/support policy modules may re-export registry metadata for compatibility,
  but should not own separate path, name, or title literals.
- Update `tools/saved_reply_policy.py` and `docs/saved-replies.md` together
  when canonical `needs-info`, `needs-repro`, `support-redirect`,
  `security-redirect`, `duplicate`, `out-of-scope`, or `docs-follow-up`
  maintainer reply wording changes.
- Update `tools/reply_policy_base.py` in the same pull request when the shared
  saved-reply or triage-reply slug lookup, snippet collectors, or baseline
  validation helpers change.
- Update `tests/policy_assertions.py` in the same pull request when shared
  policy-test snippet matching, label-description assertions, artifact
  assertion helpers, issue-form metadata/field/label parsing, issue-template
  contact-link parsing, stale-workflow exemption parsing, or release-notes
  config parsing changes.
- Update `tools/triage_policy.py`, `docs/issue-triage.md`, and
  `docs/label-taxonomy.md` together when canonical redirect/closure reply
  semantics or triage-policy wording changes.
- Update `tools/label_behavior_policy.py`, `docs/issue-triage.md`,
  `docs/label-taxonomy.md`, `.github/labels.json`, `.github/release.yml`, and
  the PR/stale triage helpers together when `documentation`, `duplicate`,
  `invalid`, `blocked`, `release-note`, or `wontfix` semantics change.
- Update `tools/routing_label_policy.py`, `docs/issue-triage.md`,
  `docs/label-taxonomy.md`, `.github/labels.json`, relevant issue forms,
  `.github/ISSUE_TEMPLATE/config.yml`, `docs/discussions-policy.md`,
  `docs/dependency-policy.md`, `.github/dependabot.yml`, and
  `.github/release.yml` together when `bug`, `support`, `proposal`,
  `dependencies`, or `security` routing changes.
- Update `tools/contributor_release_label_policy.py`,
  `docs/issue-triage.md`, `docs/label-taxonomy.md`, `.github/labels.json`,
  relevant feature or maintainer issue forms, `.github/release.yml`,
  `.github/workflows/stale.yml`, and maintainer lifecycle workflows together
  when `enhancement`, `maintenance`, `breaking`, `good first issue`, or
  `help wanted` semantics change.
- Update `tools/status_label_policy.py`, `docs/issue-triage.md`,
  `docs/label-taxonomy.md`, `.github/labels.json`,
  `.github/workflows/community-triage.yml`, `.github/workflows/stale.yml`,
  `.github/release.yml`, and the relevant maintainer lifecycle issue forms or
  workflows together when `needs-info`, `needs-repro`, `stale`, `ops-review`,
  `release-prep`, or `release-follow-up` semantics change.
- Update `tools/label_registry.py`, `.github/labels.json`, and
  `docs/label-taxonomy.md` together when any label name, description, or
  top-level taxonomy section assignment changes.
- Update `tools/label_policy_base.py` in the same pull request when the shared
  label-policy spec fields, snippet collectors, release-note collectors, or
  baseline validation rules change.
- Update `tools/docs_check_pr_comment.py` in the same pull request when the
  trusted docs-check PR comment workflow changes how it resolves workflow-run
  context, verifies artifact presence, or decides comment upsert/delete mode.
- Update `tools/sync_issue_labels.py` in the same pull request when managed
  GitHub label synchronization behavior changes for community triage or
  pull-request routing automation.
- Update `tools/pr_hygiene.py`, `tools/community_triage.py`, and
  `tools/community_pr_labels.py` in the same pull request when PR-hygiene,
  issue-intake, or pull-request path-label policy evaluation changes.
- Update `tools/lifecycle_contracts.py` in the same pull request when
  quarterly-review, release-preparation, or post-release issue fields,
  checklist items, or default summary values change.
- Update `SECURITY.md`, `SUPPORT.md`, and `docs/issue-triage.md` when issue-routing, disclosure, or support boundaries change.
- Update `docs/label-taxonomy.md` and `.github/labels.json` together when the repository label set changes.
- Update `GOVERNANCE.md`, `docs/roadmap-policy.md`, and `docs/maintainer-rotation.md` when decision-making, roadmap intake, or ownership rules change.
- Update `docs/discussions-policy.md` and any relevant issue templates when proposal or community-routing paths change.
- Update GitHub issue forms when bug, feature, proposal, support,
  release-preparation, or post-release follow-up intake requirements change.
- Update `docs/adr/README.md` or add a new ADR when a change introduces a long-lived architecture or workflow constraint.
- Update `docs/review-policy.md` and `docs/branch-protection-policy.md` when review or merge expectations change.
- Update `docs/ruleset-policy.md` when rulesets, merge queue, or required-check
  enforcement strategy changes.
- Update `docs/maintainer-access-policy.md` when maintainer onboarding,
  offboarding, or access-review rules change.
- Update `docs/quarterly-maintainer-review.md` and matching workflow logic when
  the recurring repository-operations review checklist, summary format, or
  cadence changes.
- Update `docs/release-cadence-policy.md` or
  `docs/release-lifecycle-runbook.md` when release timing, versioning posture,
  or release-artifact linkage rules change.
- Update `docs/operations-history.md` when a release cycle completes or when a
  maintainer-process change needs a durable historical record.
- Update `docs/dependency-policy.md` and `.github/dependabot.yml` together when dependency maintenance rules change.
- Update `docs/issue-triage.md`, `docs/label-taxonomy.md`, and any matching
  workflow logic when issue or pull-request automation changes.
- Update `tools/saved_reply_policy.py` and `docs/saved-replies.md` when
  maintainers standardize or rewrite common reply text.
- Prefer small, reviewable commits over large mixed refactors.
- Prefer pull requests over direct pushes when changing workflows, governance,
  compatibility, or release behavior.
- If docs or changelog updates are intentionally not needed, say so explicitly
  in the PR template instead of leaving the hygiene status ambiguous.
- If a substantial PR is intentionally not linked to an issue or proposal, say
  so explicitly in the PR template as well.

## Project Standards

- Python 3.12+ only.
- New code should be type-annotated.
- Total coverage must stay at or above the repository floor enforced by `coverage`.
- User-visible failures should produce actionable error messages.
- Network integrations should be deterministic enough for unit tests to mock.

## Documentation Ownership

Treat documentation updates as part of the feature or maintenance change, not a
follow-up task.

- Config or CLI UX changes: update `README.md` and `config.example.toml`.
- Common setup-path changes: update `docs/config-recipes.md`.
- Workflow or support-policy changes: update `docs/compatibility-matrix.md`
  and `docs/maintainer-guide.md`.
- Community-intake or disclosure changes: update `SECURITY.md`, `SUPPORT.md`,
  and `docs/issue-triage.md`.
- Label taxonomy changes: update `docs/label-taxonomy.md`,
  `.github/labels.json`, and any workflow or release-notes rule that depends on
  those labels.
- Governance or ownership changes: update `GOVERNANCE.md`,
  `docs/roadmap-policy.md`, `docs/maintainer-rotation.md`, and
  `docs/maintainer-access-policy.md`.
- Proposal-path or discussion-routing changes: update
  `docs/discussions-policy.md` and relevant issue templates.
- Issue-form intake changes: update the matching files under
  `.github/ISSUE_TEMPLATE/`.
- Long-lived architecture or workflow decisions: add or update an ADR under
  `docs/adr/`.
- Review or merge-policy changes: update `docs/review-policy.md` and
  `docs/branch-protection-policy.md`.
- Ruleset or merge-queue changes: update `docs/ruleset-policy.md` and
  `docs/repository-settings-checklist.md`.
- Manual GitHub setting changes: update
  `docs/repository-settings-checklist.md`.
- Maintainer onboarding, offboarding, or repository-role changes: update
  `docs/maintainer-access-policy.md` and any affected ownership docs.
- Scheduled repository-operations review changes: update
  `docs/quarterly-maintainer-review.md`, `.github/workflows/quarterly-maintainer-review.yml`,
  and any affected maintainer docs.
- Release-cadence or release-runbook changes: update
  `docs/release-cadence-policy.md`, `docs/release-lifecycle-runbook.md`,
  `RELEASING.md`, and any affected issue forms or maintainer docs.
- Maintainer-navigation changes: update `docs/maintainer-operations-hub.md`
  and any README or maintainer-guide links that point to it.
- Durable maintainer-operations history changes: update
  `docs/operations-history.md` in the same pull request.
- Post-release verification workflow changes: update
  `docs/post-release-checklist.md`, `.github/workflows/post-release-follow-up.yml`,
  and any affected release docs.
- Dependency-maintenance changes: update `docs/dependency-policy.md`,
  `.github/dependabot.yml`, and any workflow or label config that depends on
  them.
- Issue or pull-request automation changes: update `docs/issue-triage.md`,
  `docs/label-taxonomy.md`, and the relevant workflow inventory docs.
- Release-process changes: update `RELEASING.md`.
