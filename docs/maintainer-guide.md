# Maintainer Guide

## Local Workflow

Use the standard local checks before merging:

```bash
make check
make build
make release-check
```

If you want the docs-only guardrail without the full test suite, run:

```bash
make docs-check
```

If you are changing issue forms, labels, saved replies, triage policy, PR
hygiene, support policy, or release-lifecycle contract data, run:

```bash
make policy-check
```

For a machine-readable policy report, run:

```bash
make policy-check-json
```

For a GitHub-step-summary-friendly policy Markdown report, run:

```bash
make policy-check-markdown
```

If you need the same guardrail as a machine-readable artifact for CI or local
inspection, run:

```bash
make docs-check-json
```

If you need the same guardrail as a GitHub-step-summary-friendly Markdown
report, run:

```bash
make docs-check-markdown
```

To lint GitHub Actions workflows locally:

```bash
make workflow-tools
make workflow-check
```

If you need the JSON report and Markdown summary written to stable file paths
for upload or local post-processing, run:

```bash
python tools/check_docs.py --json-report-file reports/docs-check-report.json --markdown-report-file reports/docs-check-summary.md
```

If you need the policy report written to a stable file path for upload or local
post-processing, run:

```bash
python tools/check_policies.py --json-report-file reports/policy-check-report.json
```

If you need policy-check annotations or Markdown rendered back from that JSON
artifact, run:

```bash
python tools/render_policy_report.py reports/policy-check-report.json --format github-annotations
python tools/render_policy_report.py reports/policy-check-report.json --format markdown
```

If you need GitHub Actions annotations or a Markdown summary rendered back from
that JSON artifact, run:

```bash
python tools/render_docs_report.py reports/docs-check-report.json --format github-annotations
python tools/render_docs_report.py reports/docs-check-report.json --format markdown
python tools/render_docs_report.py reports/docs-check-report.json --format pr-comment
```

The current docs-check JSON artifact is schema v4 and carries stable `check_id`
values plus structured findings with `message`, `severity`, and best-effort
`path` / `line` / `end_line` metadata.
The link, registry, and lifecycle checks now emit native findings before report
serialization, so annotation metadata is mostly sourced directly from the
failing check instead of reconstructed from flat strings.
Those same checks now also attach heading, issue-form-field, and workflow-block
line ranges when the parser can resolve a stable source origin.
The reusable Python verification workflow also uploads a PR-comment body
artifact, and the trusted `workflow_run` follow-up in
`.github/workflows/docs-check-pr-comment.yml` re-renders the same body from the
JSON report on the default branch before it updates or deletes the PR comment.

`tools/check_workflows.py` looks for `actionlint` in `ACTIONLINT_BIN`, then
`.tools/actionlint/actionlint`, then `PATH`.
`make workflow-tools` installs the pinned `actionlint` release into
`.tools/actionlint/actionlint` for macOS/Linux amd64/arm64 hosts and verifies
the archive checksum before it replaces the repo-local binary.
`make workflow-check` is the YAML/actionlint guardrail. Workflow behavior
contracts live in the Python workflow contract suite under
`tests/test_*_workflow.py`, `tests/test_workflow_contract_suite.py`, and
`tests/workflow_assertions.py`; those run through `make check` and assert
permissions, triggers, artifact paths, and repo-local helper wiring for
state-changing workflows.

If you change lifecycle summary or close-out templates, sync the managed
lifecycle blocks first:

```bash
python tools/sync_lifecycle_docs.py
```

If you contribute regularly, install pre-commit hooks:

```bash
pre-commit install
```

If you are looking for the right maintainer doc rather than a specific command,
start with `docs/maintainer-operations-hub.md`.

## Workflow Inventory

- `ci.yml`: required verification for pull requests and direct pushes.
- `reusable-python-checks.yml`: shared verification path used by CI and
  release automation, including the uploaded `docs-check-report` and
  `policy-check-report` JSON/Markdown artifact pairs plus the GitHub step
  summary and GitHub annotations rendered from those reports by
  `tools/render_docs_report.py` and `tools/render_policy_report.py`. The
  docs-check JSON report now carries structured findings so annotations can
  target file/line locations when docs-check can infer them.
- `release.yml`: tag-driven packaging and GitHub Release publishing, with a
  manual `dry_run` dispatch path that builds and validates `package-dist`
  without publishing.
- `docs-check-pr-comment.yml`: trusted `workflow_run` follow-up that downloads
  the `docs-check-report` artifact from a CI pull-request run, re-renders the
  PR comment body on the default branch, posts it on failing PRs, and deletes
  the reminder again when docs-check passes.
- `tools/sync_marker_comment.py`: shared marker-comment helper used by PR
  hygiene, community triage, and docs-check PR comment sync so those workflows
  share the same create/update/delete behavior for managed comments.
- `tools/github_api.py`: shared repository-scoped GitHub API transport used by
  workflow helpers so auth headers, JSON payload handling, pagination, and
  ignored-status behavior do not drift across multiple scripts.
- `tools/github_resources.py`: typed GitHub resource facades for issue
  comments, issue labels, repository labels, workflow artifacts, and
  pull-request files, so the helper scripts do not each carry their own
  resource-path wiring.
- `tools/github_services.py`: narrow workflow-helper service layer for managed
  comment sync, issue/repository label sync, workflow artifact lookup, and
  pull-request file listing, so the CLI/workflow entry scripts do not each
  keep those operations.
- `tools/workflow_path_policy.py`: shared workflow-helper path classification
  policy for docs, runtime/ops, maintenance, governance, changelog, and tests,
  so PR hygiene and pull-request label routing do not drift on file-category
  rules.
- `tools/pr_policy.py`: shared PR-template contract for checkbox labels, linked
  issue field names, and PR-hygiene reminder copy, so PR hygiene automation and
  the pull-request template do not drift on wording.
- `tools/issue_intake_policy.py`: shared bug-report issue-intake contract for
  form metadata, section labels, required field names, placeholder semantics,
  and community triage reminder copy, so the bug issue form and issue-intake
  automation do not drift on wording.
- `tools/support_policy.py`: shared support-intake contract for the pre-read
  docs list, support request form metadata and field labels, `SUPPORT.md`
  include guidance, community-triage support reminder copy, and the
  issue-template support contact link, so support routing docs, forms, contact
  links, and automation do not drift on wording.
- `tools/intake_policy_base.py`: shared base schema and uniqueness helpers for
  issue-intake and support-intake specs, plus shared contact-link schema, so
  those modules do not each repeat the same doc-path, key/label, contact-link,
  and snippet-collection logic.
- `tools/issue_form_policy.py`: shared issue-form metadata and field registry
  for bug, support, feature, proposal, release-preparation, and post-release
  forms, so form names, title prefixes, field labels, and requiredness stay
  structurally checked across the public intake and maintainer lifecycle forms.
  Label-policy validators and lifecycle generated blocks reuse this registry
  instead of carrying separate issue-form identity snippets, path groups, or
  labels. Bug and support policy modules re-export the same registry metadata
  for compatibility instead of owning separate form identity constants.
  Routing, contributor/release, status-label, and release-lifecycle policies
  read issue-form path groups and label expectations from this registry.
- `tools/saved_reply_policy.py`: shared saved-reply contract for
  `needs-info`, `needs-repro`, `support-redirect`, `security-redirect`,
  `duplicate`, `out-of-scope`, and `docs-follow-up`, so canonical maintainer
  reply text in `docs/saved-replies.md` does not drift across high-frequency
  routing paths.
- `tools/triage_policy.py`: shared policy contract that binds canonical
  redirect/closure replies back to `docs/issue-triage.md` and
  `docs/label-taxonomy.md`, so reply wording and maintainer-policy wording do
  not drift apart.
- `tools/reply_policy_base.py`: shared base schema and snippet collectors for
  saved replies and triage reply-policy bindings, so those modules do not each
  repeat the same slug lookup and baseline snippet-validation loop.
- `tests/policy_assertions.py`: shared policy-test assertion helpers for
  normalized snippet checks, label description checks, and grouped artifact
  checks, plus issue-form metadata/fields/labels, issue-template contact-link,
  stale-workflow exemption, and release-notes config parsing, so policy
  contract tests do not each repeat file loading, whitespace normalization, and
  GitHub metadata parsing boilerplate.
- `tools/label_behavior_policy.py`: shared label-behavior contract for
  `documentation`, `duplicate`, `invalid`, `blocked`, `release-note`, and
  `wontfix`, so label descriptions, triage-policy wording, stale behavior,
  pull-request routing, and release-notes category wiring do not drift apart.
- `tools/routing_label_policy.py`: shared routing-label contract for `bug`,
  `support`, `proposal`, `dependencies`, and `security`, so label
  descriptions, issue forms, contact links, discussions fallback paths, and
  dependency-routing automation do not drift apart.
- `tools/contributor_release_label_policy.py`: shared contributor/release
  label contract for `enhancement`, `maintenance`, `breaking`,
  `good first issue`, and `help wanted`, so feature intake, maintainer
  lifecycle issues, release categories, and contributor-discovery label rules
  do not drift apart.
- `tools/status_label_policy.py`: shared status-label contract for
  `needs-info`, `needs-repro`, `stale`, `ops-review`, `release-prep`, and
  `release-follow-up`, so intake follow-up labels, inactivity handling, and
  maintainer lifecycle tracking labels do not drift apart.
- `tools/label_registry.py`: shared label registry for every GitHub label
  name, description, and taxonomy section boundary, so the four label-policy
  modules no longer each repeat the same label metadata.
- `tools/label_policy_base.py`: shared base schema and validation helpers for
  routing, behavior, contributor/release, and status label policies, so those
  modules no longer each repeat the same spec shape, snippet collectors,
  release-note category/exclusion collectors, and baseline validation loop.
- `tools/check_policies.py`: shared policy-check entry point for label
  registry, issue-form, issue-intake, support, saved-reply, triage, PR hygiene,
  repository-settings, label-policy, docs-contract, and release-lifecycle
  schema validators, so local and CI policy checks report failures with the
  contract name that failed. It can also emit a JSON report with schema version,
  overall status, per-contract status, and flattened errors for CI upload and
  local post-processing.
- `tools/repository_settings_policy.py`: shared repository-admin contract for
  the required-check list, the PR-facing workflow names/triggers that back those
  checks, and the cross-links among branch protection, ruleset, and repository
  settings docs.
- `tools/render_policy_report.py`: shared renderer for policy-check JSON
  reports, producing GitHub Actions annotations and Markdown summaries from the
  same report schema used by local `make policy-check-json`.
- `tools/docs_check_pr_comment.py`: shared trusted-workflow helper that resolves
  `workflow_run` PR/artifact context and decides docs-check PR comment
  upsert/delete outputs, so `docs-check-pr-comment.yml` no longer keeps that
  GitHub API and comment-decision logic inline.
- `tools/sync_issue_labels.py`: shared GitHub label-sync helper used by
  community triage so issue-intake and pull-request routing no longer keep
  add/remove label behavior in workflow YAML.
- `tools/sync_repository_labels.py`: shared repository-label sync helper used
  by `label-sync.yml` to read `.github/labels.json` and create or update
  labels through repo-local Python instead of inline workflow script.
- `tools/pr_hygiene.py`, `tools/community_triage.py`, and
  `tools/community_pr_labels.py`: shared policy evaluators that keep
  PR-hygiene, issue-intake, and pull-request path-label routing decisions in
  repo-local Python instead of embedding that logic directly in workflow YAML.
- `dependency-review.yml`: pull-request guardrail for dependency manifest and
  workflow dependency changes.
- `workflow-lint.yml`: lints GitHub Actions workflow definitions with
  `actionlint`; it now bootstraps the same pinned repo-local binary through
  `make workflow-tools` and then runs `make workflow-check`, so CI and local
  workflow linting use the same installer, binary path, and discovery rules.
- `make docs-check`: repository-local check for Markdown links, heading
  anchors, repository-doc references inside GitHub issue forms and workflows,
  consistency between the README docs map, the maintainer hub, and this guide,
  plus release-lifecycle contract checks across `RELEASING.md`, the runbook,
  and release issue forms, plus summary and close-out template checks for
  quarterly review and post-release maintainer issues, plus lifecycle
  cross-link field checks between quarterly review, release prep, and
  post-release artifacts, plus issue close-out rule checks across the same
  lifecycle, plus default-summary semantic checks for workflow-generated issue
  bodies, now using `tools/lifecycle_contracts.py` as the repo-local contract
  schema for lifecycle rules plus `tools/docs_contracts.py` for maintainer-doc
  registry and docs-check boundary rules, with structured parsing of workflow
  body sections and issue-form fields instead of file-level text matching.
  The generic Markdown / GitHub metadata scanning and parser implementation now
  lives in `tools/docs_parser.py`, and generic repository-link resolution plus
  anchor validation now live in `tools/docs_links.py`, while source reading and
  workflow-section caching now live in `tools/docs_sources.py`, and generic
  contract-assertion / text-normalization helpers now live in
  `tools/docs_assertions.py`. The maintainer-doc registry contract executor now
  lives in `tools/docs_registry_checks.py`, and the release/ops lifecycle
  contract executors now live in `tools/lifecycle_checks.py`. The declarative
  docs-check pipeline, phase report labels, command/reporting config, failure
  summaries, JSON/Markdown report rendering, and success-message template now
  live in `tools/docs_pipeline.py`. Managed lifecycle blocks in the
  quarterly-review/post-release docs, issue forms, and release/ops workflows
  are synced from that schema by `tools/sync_lifecycle_docs.py`.
- `pr-hygiene.yml`: reminds pull requests to make docs and changelog intent
  explicit.
- `label-sync.yml`: syncs the documented label set into the repository by
  calling `tools/sync_repository_labels.py` against `.github/labels.json`.
- `stale.yml`: applies inactivity rules to issues and pull requests.
- `quarterly-maintainer-review.yml`: opens the recurring maintainer issue for
  access review and repository-settings audit work.
- `post-release-follow-up.yml`: opens the follow-up issue after a GitHub
  release is published.
- `community-triage.yml`: applies conservative issue and pull-request triage
  automation.
- GitHub issue forms under `.github/ISSUE_TEMPLATE/*.yml`: structured intake
  for bugs, features, proposals, support requests, release preparation, and
  post-release follow-up.
- `daily-digest.yml`: scheduled production digest run plus Pages deployment.
- `backfill-archive-history.yml`: manual historical archive rebuild.
- `feedback-secret-sync.yml`: short-lived export path for feedback-state pull.
- `action-state-sync.yml`: short-lived export or import path for remembered
  action-notification state.

## Governance Documents

- `GOVERNANCE.md`: decision model and role definitions.
- `docs/roadmap-policy.md`: how ideas move into or out of the roadmap.
- `docs/maintainer-rotation.md`: how ownership should be handed off as the
  maintainer set grows.
- `docs/discussions-policy.md`: intended Discussions categories plus current
  fallback routes before Discussions is enabled.
- `docs/adr/README.md`: when and how to record long-lived decisions.
- `docs/review-policy.md`: default pull-request approval and self-merge rules.
- `docs/branch-protection-policy.md`: intended `main` branch protection rules.
- `docs/repository-settings-checklist.md`: manual GitHub admin settings that
  are not enforced by repository files alone.
- `docs/ruleset-policy.md`: intended ruleset and merge-queue posture.
- `docs/saved-replies.md`: canonical text for personal maintainer saved replies.
- `docs/maintainer-access-policy.md`: maintainer onboarding, offboarding, and
  access-review policy.
- `docs/maintainer-operations-hub.md`: maintainer-facing entry point for the
  operations docs set.
- `docs/quarterly-maintainer-review.md`: the checklist for recurring
  repository-operations review issues.
- `docs/release-cadence-policy.md`: release timing and version-scope policy.
- `docs/release-lifecycle-runbook.md`: release artifact order and linkage rules.
- `docs/operations-history.md`: the long-lived index for release-cycle and
  maintainer-operations history.
- `docs/post-release-checklist.md`: the checklist for post-release verification
  and next-cycle setup.

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

## CI Maintenance Policy

- Keep workflow permissions as narrow as practical.
- Prefer one documented local verification path:
  `make check`, `make policy-check`, `make workflow-check`, `make build`, and
  `make release-check`.
- Keep `make docs-check` green when maintainer docs, policy pages, or README
  links move, and when issue forms or workflows reference repository docs, so
  the docs index surfaces do not drift. The same guardrail also keeps the
  README docs map, maintainer entry-point docs, and release-lifecycle
  checklists aligned, and it prevents maintainer issue summary templates from
  drifting away from the public source-of-truth docs. It also keeps release
  lifecycle cross-link fields aligned so quarterly review, release prep, and
  post-release issues keep the same linkage expectations, and it keeps their
  close-out rules aligned so follow-up links or explicit `none` handoffs do
  not drift. The same guardrail now also keeps default summary values such as
  `none`, `confirmed`, and `complete` aligned with the documented template
  semantics by parsing issue-form fields and workflow body sections directly
  against `tools/lifecycle_contracts.py`; the maintainer-doc navigation,
  source-of-truth registry rules, and docs-check repository-boundary config
  live in `tools/docs_contracts.py`, while generic repository-link resolution
  and anchor validation live in `tools/docs_links.py`, and generic source
  reading plus workflow-section caching live in `tools/docs_sources.py`, and
  generic contract-assertion / text-normalization helpers live in
  `tools/docs_assertions.py`. Maintainer-doc registry checks live in
  `tools/docs_registry_checks.py`, and lifecycle contract checks live in
  `tools/lifecycle_checks.py`. The docs-check execution order, phase labels,
  command exit codes, stderr/stdout reporting shape, failure summaries, JSON
  report schema plus structured finding model, and success output now live in
  `tools/docs_pipeline.py`. `tools/render_docs_report.py` consumes that schema
  for GitHub annotations and Markdown re-rendering, and
  `tools/check_workflows.py` owns local `actionlint` discovery for
  `make workflow-check`. The same guardrail also verifies that managed
  lifecycle blocks were re-synced before commit.
- Add `timeout-minutes` to long-lived jobs so failures stop burning runner time.
- Use concurrency on PR-facing or release-facing workflows when stale runs do
  not provide signal.
- Treat cache keys and artifact names as public maintenance surfaces; document
  changes when they affect recovery, sync, or Pages behavior.
- When a workflow changes operator behavior, update `README.md`,
  `RELEASING.md`, and this guide in the same pull request.

## Compatibility Ownership

The source of truth for supported runtimes and platforms is
`docs/compatibility-matrix.md`.

- Do not broaden compatibility claims only in badges or README prose.
- If CI still validates only one runtime, document broader versions as
  "expected" rather than "supported".
- When support changes, update the matrix, relevant workflow files, and the
  release notes together.

## Secrets And Scheduled Runs

- `PAPER_DIGEST_CONFIG_TOML`: required for scheduled digest runs.
- `PAPER_DIGEST_FEEDBACK_JSON`: optional feedback seed for scheduled runs.
- `OPENAI_API_KEY`: only required when `[analysis] enabled = true`.
- `OPENALEX_API_KEY`: only required when OpenAlex feeds are configured and the
  config references that environment variable.
- `PAPER_DIGEST_SMTP_PASSWORD`: only required for SMTP delivery.

When changing any workflow that reads these secrets, verify both the docs and
the failure messages stay actionable.

## Issue Triage

The source of truth for intake and closure rules is
`docs/issue-triage.md`.

- Security reports must be redirected to `SECURITY.md`.
- Usage and setup questions should follow `SUPPORT.md`.
- Public issues should meet the minimum reproduction bar before maintainers
  spend time on deep investigation.
- When closing or redirecting an issue, link the exact policy or doc page being
  applied.
- Keep the live label set aligned with `docs/label-taxonomy.md` and
  `.github/labels.json`.
- Keep `community-triage.yml` aligned with the bug template and the minimum
  information bar in `docs/issue-triage.md`.
- Keep the issue forms aligned with support-routing, proposal-routing, and bug
  intake policy so forms do not drift from the published maintainer rules.

## Support Boundaries

- Treat support as best effort, not an SLA.
- Prioritize the latest release, `main`, and the documented local CLI and
  GitHub Actions paths.
- Avoid turning issues into private consulting threads; redirect broad usage
  questions back to `README.md`, config recipes, or `SUPPORT.md` when
  appropriate.

## Governance And Ownership

- Governance is maintainer-led unless the public docs say otherwise.
- Use `GOVERNANCE.md` as the source of truth for decision rules.
- Use `docs/roadmap-policy.md` as the source of truth for roadmap intake and
  prioritization language.
- Keep `.github/CODEOWNERS`, `GOVERNANCE.md`, and
  `docs/maintainer-rotation.md` aligned when ownership changes.
- Keep `.github/CODEOWNERS` structured by repository surface so future
  maintainer growth does not depend on one blanket rule.

## Maintainer Access

- Use `docs/maintainer-access-policy.md` as the source of truth for
  onboarding, offboarding, role minimization, and periodic access review.
- Treat admin access as exceptional rather than the default maintainer role.
- When repository-admin access changes, update ownership and routing docs in
  the same pull request where practical.
- During quarterly access review, compare the live collaborator list against
  `.github/CODEOWNERS`, `GOVERNANCE.md`, and
  `docs/repository-settings-checklist.md`.
- Use `docs/quarterly-maintainer-review.md` and the scheduled issue from
  `quarterly-maintainer-review.yml` to leave a dated record of the review.
- Use the review-summary template in `docs/quarterly-maintainer-review.md` so
  each cycle records the same access, settings, and follow-up fields.

## Review And Branch Protection

- Use `docs/review-policy.md` as the source of truth for default PR review
  expectations.
- Use `docs/branch-protection-policy.md` as the source of truth for intended
  `main` branch settings that GitHub must enforce manually.
- Use `docs/repository-settings-checklist.md` as the source of truth for merge
  strategy, Pages, Discussions, and other repository-admin settings.
- Use `docs/ruleset-policy.md` as the source of truth when branch rulesets or
  merge queue enter the workflow.
- If workflow names or required status-check contexts change, update the
  protection policy in the same pull request. Branch protection uses check
  contexts such as `verify / verify`, not only the human-readable workflow
  name.
- Prefer reusable workflows when CI and release pipelines share the same
  verification contract.
- Treat `pull_request_target` automation as sensitive: do not add checkout or
  untrusted-code execution to triage-only workflows.
- Keep `pr-hygiene.yml`, the PR template, and contributor docs aligned so the
  automation only reminds contributors about what the repository publicly asks
  them to do.

## Saved Replies

- Use `tools/saved_reply_policy.py` and `docs/saved-replies.md` together as the
  maintained source of truth for high-frequency issue and pull-request replies.
- Remember that saved replies live in personal GitHub settings, not in the
  repository configuration.
- When a maintainer updates the canonical reply text here, update their saved
  replies in GitHub as part of the same maintenance work.

## Release Notes And Labels

- `.github/release.yml` is the source of truth for generated GitHub release
  note categories.
- Use `release-note` when a change should stand out in both `CHANGELOG.md` and
  generated release notes.
- Keep label names used by `.github/release.yml`, `stale.yml`, and
  `docs/label-taxonomy.md` aligned.

## Dependency Policy

Use `docs/dependency-policy.md` as the source of truth.

- Runtime dependencies should stay minimal.
- Development tooling can grow when it clearly improves repository health.
- Keep Dependabot grouping and the `dependencies` label aligned with
  `.github/dependabot.yml`, `.github/labels.json`, and `.github/release.yml`.

## Release Ownership

Follow the checklist in `RELEASING.md`.

- Use `docs/release-cadence-policy.md` when deciding whether a patch, minor, or
  larger release is ready to ship.
- Use `docs/release-lifecycle-runbook.md` as the source of truth for how
  quarterly review, release prep, tag publication, and post-release follow-up
  connect.
- Open a `Release preparation` issue before pushing the tag and keep it linked
  from any release-preparation pull request or maintainer notes.
- Open or confirm the `Post-release follow-up` issue after publication and use
  it to track release verification, next-cycle setup, and retrospective notes.
- Update `docs/operations-history.md` when a release completes or when a
  maintainer-process change is significant enough to affect future operations.
- If a release includes repository-settings, access, or workflow-policy
  changes, link the latest quarterly maintainer review issue in the release
  preparation work.
- If the quarterly review is overdue at release time, either complete it first
  or note the deferral explicitly in release preparation.

The tag format is `vX.Y.Z`, for example `v0.2.0`.
