# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic
Versioning.

## [Unreleased]

- Documentation now includes a dedicated compatibility matrix, smaller
  configuration recipes, and a stronger maintainer guide for workflow and
  release ownership.
- Community docs now include a fuller security policy, explicit support
  expectations, maintainer issue-triage rules, and routed GitHub issue
  templates.
- The repository now documents and syncs a label taxonomy, applies stale issue
  automation, and categorizes generated GitHub release notes through a
  dedicated template.
- Governance, roadmap intake, and maintainer-ownership rules are now explicit
  through dedicated public docs instead of being implied by repository state.
- Proposal intake, future Discussions categories, ADR guidance, and dependency
  maintenance policy are now documented explicitly, with grouped Dependabot
  updates and dependency-review automation aligned to the repository label set.
- CI and release verification now share a reusable workflow, and the
  repository now documents review and branch-protection policy explicitly.
- GitHub issue and pull-request intake now has conservative triage automation,
  and workflow definitions now have a dedicated `actionlint` check.
- Pull requests now have explicit docs/changelog hygiene declarations plus a
  dedicated automation check that reminds contributors when those updates are
  likely missing.
- `CODEOWNERS` is now structured by repository surface, and issue intake now
  uses GitHub issue forms while keeping bug-triage automation compatible with
  the generated issue body format.
- Support intake now also shares one contract across `SUPPORT.md`, the support
  issue form metadata and fields, support contact links, and community-triage
  reminder copy.
- The canonical `support-redirect` saved reply and the support issue-form
  intro now also reuse that same support-routing contract.
- Canonical `needs-info`, `support-redirect`, and `security-redirect` saved
  replies now also live behind a repo-local reply-policy contract.
- The remaining canonical saved replies now also live behind that same
  reply-policy contract, so `docs/saved-replies.md` is fully governed instead
  of partially managed.
- Redirect and closure reply semantics are now also tied back to
  `docs/issue-triage.md` and `docs/label-taxonomy.md` through a shared
  triage-policy contract.
- `documentation`, `duplicate`, `invalid`, `blocked`, `release-note`, and
  `wontfix` now also share an explicit label-behavior contract, so label
  descriptions, stale expectations, pull-request routing, and generated
  release-notes wiring do not drift apart.
- `bug`, `support`, `proposal`, `dependencies`, and `security` now also share
  an explicit routing-label contract, so issue forms, contact links,
  discussions fallback paths, and dependency-routing automation do not drift
  apart from the label taxonomy.
- `enhancement`, `maintenance`, `breaking`, `good first issue`, and
  `help wanted` now also share an explicit contributor/release label
  contract, so feature intake, maintainer lifecycle labels, release
  categories, stale exemptions, and contributor-discovery semantics do not
  drift apart.
- `needs-info`, `needs-repro`, `stale`, `ops-review`, `release-prep`, and
  `release-follow-up` now also share an explicit status-label contract, so
  intake follow-up labels, inactivity handling, and maintainer lifecycle
  tracking labels do not drift apart.
- Label names, descriptions, and taxonomy section boundaries now also share a
  unified registry schema, so the four label-policy modules no longer repeat
  the same metadata in parallel.
- The four label-policy modules now also share a common base schema and
  validation helper, so their spec shape, snippet collectors, release-note
  category/exclusion collectors, and baseline validation loop no longer drift
  in parallel.
- The issue-intake/support policy pair and the saved-reply/triage policy pair
  now also share common base helpers, so their doc-path, key/label, slug
  lookup, contact-link spec, snippet collector, and baseline validation logic
  no longer drift in parallel.
- GitHub issue forms now also share a structured metadata and field registry
  for bug, support, feature, proposal, release-preparation, and post-release
  forms, so form names, title prefixes, field labels, and requiredness stay
  checked without relying on broad YAML snippet matching; label-policy
  validators and lifecycle generated blocks now reuse that registry for
  issue-form labels, label-policy path groups, release-lifecycle path groups,
  and identity checks, and bug/support policy modules now re-export the same
  registry metadata instead of owning separate form identity constants.
- Policy contract tests now share assertion helpers for normalized snippet
  matching, label descriptions, grouped artifact checks, and stale-workflow
  exemption plus issue-form metadata/field/label, issue-template contact-link,
  and release-notes config parsing, so policy tests no longer repeat
  file-loading, whitespace-normalization, and GitHub metadata parsing
  boilerplate.
- Local verification now includes `make policy-check` backed by
  `tools/check_policies.py`, so issue-form, intake, support, saved-reply,
  triage, PR hygiene, label, docs-contract, and release-lifecycle policy
  validators run through one contract-named gate before docs and coverage.
- `tools/check_policies.py` now also emits a schema-versioned JSON report via
  `make policy-check-json`, `--format json`, and `--json-report-file`, so
  policy-check output can be uploaded or rendered by future CI annotations and
  summaries without re-running contract logic.
- `tools/render_policy_report.py` now renders policy-check JSON reports into
  GitHub Actions annotations and Markdown, `make policy-check-markdown` exposes
  the local summary path, and the reusable Python verification workflow uploads
  the policy-check JSON/Markdown artifact while appending the same summary and
  annotations to CI. The docs checker now also skips generated `reports/`
  outputs so local report rendering does not change docs-check file counts.
- The reusable Python verification workflow now has shared report contract
  tests covering both docs-check and policy-check upload inputs, JSON
  generation, Markdown summary publication, GitHub Actions annotations, PR
  comment preview rendering, and uploaded report artifact contents.
- The trusted docs-check PR comment follow-up workflow now also has a
  repo-local workflow contract covering its `workflow_run` trigger, minimal
  permissions, docs-check artifact download, default-branch PR comment
  rendering, comment-action decision, and shared marker-comment sync helper
  calls.
- PR hygiene, community triage, and label sync now have workflow contract-suite
  coverage for state-changing GitHub automation, and `label-sync.yml` now calls
  `tools/sync_repository_labels.py` instead of embedding label mutation logic in
  workflow YAML.
- Maintainer docs now include a repository-settings checklist for manual GitHub
  admin configuration, and `PR Hygiene` now also reminds contributors to link
  substantial pull requests back to an issue or proposal.
- Maintainer operations docs now also define intended ruleset / merge-queue
  posture and a canonical source-of-truth for GitHub saved replies.
- Maintainer operations docs now also define maintainer onboarding,
  offboarding, least-privilege access, and quarterly access-review policy.
- The repository now opens a recurring quarterly maintainer review issue and
  documents the checklist used for repository-settings and access audits.
- Quarterly maintainer reviews now use a standard closing-summary template, and
  release prep explicitly links repository-operations changes back to the
  latest review record.
- Maintainers now have a dedicated release-preparation issue form, plus a
  `release-prep` label and stale-policy exemption for tagged-release tracking.
- Releases now also open a dedicated post-release follow-up issue and document
  a standard checklist for published-release verification and next-cycle setup.
- Release timing expectations and the linkage between quarterly review, release
  prep, tag publication, and post-release follow-up are now documented through
  a dedicated cadence policy and lifecycle runbook.
- Maintainer operations now also have a long-lived history index that records
  release-cycle artifacts and notable process changes in one place.
- Maintainer docs now also have a single operations hub page that routes common
  review, audit, release, and post-release tasks to their source-of-truth docs.
- Local verification now includes a docs consistency check for Markdown links
  and heading anchors, and `pre-commit` can run the same guardrail before
  commits.
- The docs consistency guard now also validates repository-doc references in
  GitHub issue forms and workflows, not only Markdown pages.
- The docs consistency guard now also checks that the README docs map, the
  maintainer hub source-of-truth table, and maintainer-guide coverage stay in
  sync.
- The docs consistency guard now also checks that `RELEASING.md`, the release
  lifecycle runbook, and release issue forms keep the same core release
  contract.
- The docs consistency guard now also checks that quarterly-review and
  post-release summary / close-out templates stay aligned with their published
  maintainer docs, and that release-prep scope-summary categories still match
  `RELEASING.md`.
- The docs consistency guard now also checks that quarterly review, release
  prep, and post-release artifacts keep the same cross-link field contract, and
  the release docs now make the post-release quarterly-review linkage rule
  explicit.
- The docs consistency guard now also checks that quarterly review, release
  prep, and post-release artifacts keep the same close-out contract, and the
  release docs now make the release-preparation handoff rule explicit.
- The docs consistency guard now also checks that quarterly-review and
  post-release summary templates keep the same default-value semantics as the
  workflow-generated issue bodies, and quarterly follow-up wording now allows
  issue or pull-request links consistently.
- The docs consistency guard now parses workflow body sections, issue-form
  fields, checklist blocks, and summary fields structurally, so lifecycle
  contract checks fail on the exact missing field or checklist item instead of
  relying on whole-file text snippets.
- The release-lifecycle contract values used by `make docs-check` now live in
  `tools/lifecycle_contracts.py`, so quarterly-review, release-prep, and
  post-release schema changes have a single repo-local source of truth.
- The remaining release-lifecycle text/snippet contract previously embedded in
  `tools/check_docs.py` now also lives in `tools/lifecycle_contracts.py`, so
  release doc/form wording checks use the same repo-local schema layer.
- Lifecycle text contracts now also use typed schema objects instead of raw
  tuple/dict shapes, so `tools/check_docs.py` reads issue-linkage, close-out,
  release-lifecycle, and maintainer-issue wording checks through one
  structured contract format.
- The last maintainer-issue wording contracts previously defined inside
  `tools/check_docs.py` now also live in `tools/lifecycle_contracts.py`, so
  `check_docs.py` no longer carries local lifecycle/maintainer text truth.
- The remaining lifecycle file/section locators used by `make docs-check`
  now also live in `tools/lifecycle_contracts.py`, so `tools/check_docs.py`
  reads release/ops artifact paths and heading mappings from the same
  repo-local schema instead of re-declaring them inline.
- The non-lifecycle maintainer-doc registry rules used by `make docs-check`
  now also live in `tools/docs_contracts.py`, so `tools/check_docs.py` reads
  README docs-map, maintainer-hub, and maintainer-guide section mappings from
  a dedicated repo-local schema instead of keeping those locators inline.
- The remaining repo-specific docs-check boundary values now also live in
  `tools/docs_contracts.py`, so `tools/check_docs.py` reads repository
  reference roots, root-level reference files, skip directories, and GitHub
  metadata globs from schema instead of defining those boundaries inline.
- The generic Markdown / GitHub metadata scanning and parsing helpers used by
  `make docs-check` now also live in `tools/docs_parser.py`, so
  `tools/check_docs.py` focuses on contract orchestration instead of carrying
  file iteration, link extraction, issue-form parsing, and workflow-body
  parsing implementations inline.
- The generic repository-link resolution, anchor validation, and Markdown /
  GitHub metadata reference-check helpers used by `make docs-check` now also
  live in `tools/docs_links.py`, so `tools/check_docs.py` focuses on contract
  orchestration instead of also carrying path-resolution and target-validation
  logic inline.
- The generic `TextSource` reading, Markdown section lookup, and workflow-
  section caching helpers used by `make docs-check` now also live in
  `tools/docs_sources.py`, so `tools/check_docs.py` focuses on contract
  orchestration instead of also carrying source-read and workflow-cache
  plumbing inline.
- The generic docs-contract field/item assertion wording plus text-
  normalization and snippet-matching helpers used by `make docs-check` now
  also live in `tools/docs_assertions.py`, so `tools/check_docs.py` focuses on
  contract orchestration instead of also carrying repo-agnostic assertion and
  normalization logic inline.
- The maintainer-doc registry check now lives in
  `tools/docs_registry_checks.py`, and the release/ops lifecycle contract
  executors now live in `tools/lifecycle_checks.py`, so `tools/check_docs.py`
  acts as a thin docs-check entry point instead of also carrying registry and
  lifecycle execution logic inline.
- The docs-check execution order, shared file-list context, pipeline
  validation, and success output now live in `tools/docs_pipeline.py`, so
  `tools/check_docs.py` no longer hand-writes the check sequence inside
  `main()`.
- The remaining docs-check entrypoint truth now also lives in
  `tools/docs_pipeline.py`, so repository root selection, exit codes,
  stderr/stdout reporting behavior, and direct entrypoint tests no longer need
  local truth inside `tools/check_docs.py`.
- The docs-check phase report labels, preflight failure summary, runtime
  failure summary, and per-error detail formatting now also live in
  `tools/docs_pipeline.py`, so `tools/check_docs.py` no longer owns
  human-facing phase-report wording.
- `tools/check_docs.py` now also supports a machine-readable JSON report, and
  the JSON schema version, phase statuses, and per-check error payloads live
  in `tools/docs_pipeline.py` alongside the existing text-report contract.
- The reusable Python verification workflow now uploads a `docs-check-report`
  artifact, and `tools/check_docs.py` can write the same JSON report directly
  to disk with `--json-report-file`.
- `tools/check_docs.py` now also renders a Markdown summary via
  `make docs-check-markdown` / `--markdown-report-file`, and the reusable
  Python verification workflow now publishes that same summary to the GitHub
  step summary alongside the uploaded artifact.
- `tools/render_docs_report.py` now re-renders docs-check JSON reports into
  GitHub Actions annotations and Markdown, and the reusable Python verification
  workflow uses it to surface docs-check failures directly in the Checks UI.
- The docs-check JSON report first moved to structured findings so the same
  annotation path could attach best-effort file/line metadata instead of only
  flat check-level messages.
- The docs-check JSON report is now schema v3 and carries `end_line` alongside
  `line`, so Markdown summaries and GitHub annotations can target line ranges
  when the parser resolves a stable heading, issue-form, or workflow block.
- The docs-check JSON report is now schema v4 and carries stable `check_id`
  values per pipeline stage, so annotations, Markdown detail headings, and
  future machine consumers can key off identifiers that do not depend on
  human-facing labels.
- The reusable Python verification workflow now also uploads a
  `docs-check-pr-comment.md` artifact rendered from the same schema, and the
  repo-local renderer can emit a stable PR comment body that groups findings by
  `check_id`.
- Pull requests now also get a trusted docs-check comment sync workflow that
  downloads the CI artifact, re-renders the comment on the default branch, and
  updates or deletes the PR comment without executing pull-request code in a
  write-permission context.
- Local workflow linting now also has a pinned `make workflow-tools` bootstrap
  path that installs `actionlint` into `.tools/actionlint/actionlint` with a
  verified archive checksum, so `make workflow-check` no longer depends only on
  ad hoc PATH state.
- The dedicated `Workflow Lint` CI job now also bootstraps and runs the same
  pinned repo-local `actionlint` path as local workflow linting, and it triggers
  when the helper scripts or `Makefile` change instead of only on workflow YAML
  edits.
- PR hygiene, community triage, and docs-check PR comment automation now share
  one repo-local marker-comment helper, so managed comment create/update/delete
  behavior no longer drifts across three separate workflows.
- PR hygiene and community issue-intake policy evaluation now also live in
  repo-local Python helpers, so those workflows keep only orchestration and
  GitHub-side label/comment actions in YAML.
- Community triage now also routes `needs-info` sync and pull-request
  path-based labels through repo-local Python helpers, so GitHub label mutation
  and label-routing policy no longer live in `github-script` workflow blocks.
- The trusted docs-check PR comment follow-up now resolves `workflow_run`
  context and comment upsert/delete decisions through one repo-local Python
  helper instead of keeping that API and policy logic inline in workflow YAML.
- Repo-local workflow helpers now also share one GitHub API transport layer, so
  auth headers, JSON payload handling, pagination, and ignored-status behavior
  no longer drift across comment, label, artifact, and PR-file scripts.
- Those workflow helpers now also share typed GitHub resource facades for issue
  comments, issue labels, workflow artifacts, and pull-request files, so
  resource-path wiring is no longer duplicated across scripts.
- Those helpers now also share a narrower GitHub service layer for managed
  comment sync, label sync, workflow artifact lookup, and pull-request file
  listing, so the script entrypoints no longer each keep those higher-level
  operations inline.
- PR hygiene and pull-request label routing now also share one workflow path
  policy module for docs, runtime/ops, maintenance, governance, changelog, and
  test path classification, so file-category semantics no longer drift across
  helper scripts.
- PR hygiene now also shares one PR-template policy contract for checkbox
  labels, linked-issue field naming, and reminder copy, so the automation and
  `.github/pull_request_template.md` no longer drift on wording.
- Community triage now also shares one bug issue-intake policy contract for
  section labels, required field names, placeholder semantics, and reminder
  copy, so `.github/ISSUE_TEMPLATE/bug_report.yml` and the intake automation no
  longer drift on wording.
- The link, registry, and lifecycle checks now emit native structured findings
  through a shared `tools/docs_findings.py` layer, so most docs-check
  annotations carry source-aware file metadata without relying on legacy string
  parsing first.
- The docs parser and source helpers now resolve markdown-section, issue-form,
  and workflow-template line origins, so lifecycle and registry annotations can
  land on the relevant heading or field instead of only the containing file.
- The repository now has a documented `make workflow-check` path powered by
  `tools/check_workflows.py`, which looks for `actionlint` in
  `ACTIONLINT_BIN`, `.tools/actionlint/actionlint`, then `PATH`.
- Quarterly-review and post-release lifecycle blocks in maintainer docs,
  issue forms, and release/ops workflows are now generated by
  `tools/sync_lifecycle_docs.py` from `tools/lifecycle_contracts.py`, and
  docs/pre-commit checks fail if those managed blocks are stale.
- Release-preparation and post-release issue forms now also generate their
  compatibility, changelog, validation, next-cycle, and retrospective blocks
  from `tools/lifecycle_contracts.py` instead of keeping those checklist
  payloads hand-maintained in YAML.
- CI and release workflows now share the same documented verification path,
  add explicit permissions and timeouts, and document their operational role
  more clearly.
- Ranking is now configurable via a dedicated `[ranking]` section plus optional
  per-feed `sort_by` overrides, and digests expose the active sorting mode in
  Markdown and JSON output.
- Papers now carry a canonical identity, relevance score, and match reasons so
  the digest can deduplicate across sources, keep richer merged records, and
  explain why each paper surfaced.
- The static archive site now emits canonical paper detail pages with merged
  source links, match reasons, history, and lightweight related-paper
  suggestions.
- Canonical paper detail pages now expose first-seen / last-seen history, and
  the archive site includes a dedicated rising-paper view for papers that keep
  resurfacing across multiple dates or feeds.
- Local feedback state now supports `star`, `follow_up`, `reading`, `done`,
  and `ignore` paper statuses keyed by canonical id, with ranking effects plus
  dedicated reading-list, review-queue, and staged weekly-review archive
  pages.
- A feedback management CLI now supports `set`, `clear`, and `list`, and the
  archive site now exposes copyable canonical-id / feedback command helpers
  plus a weekly review page for starred and follow-up papers.
- Feedback entries can now carry free-form notes, with CLI support for
  updating and clearing them, and those notes now surface across digest
  output, Focus notifications, and feedback-centric archive pages.
- The scheduled `Daily Digest` workflow now supports feedback-state sync via
  `PAPER_DIGEST_FEEDBACK_JSON` or `workflow_dispatch`'s
  `feedback_json_override`, so online Pages can reflect local reading-list
  decisions.
- Notifications now support a feedback-driven `Focus` block with configurable
  `[notify]` rules for newly starred papers, resurfaced follow-up papers, and
  starred papers that newly enter the momentum view.
- Deliveries can now opt in or out of Focus independently and choose whether
  Focus stays inline with the digest or gets emitted as a separate `Focus Brief`.
- Deliveries can now also filter Focus by feedback status and trigger reason,
  and each delivery can cap its own Focus item count independently.
- Feedback entries now support structured `next_action` and `due_date` fields,
  the feedback CLI can manage them directly, and digest notifications now
  include a dedicated weekly action section for overdue and soon-due papers.
- Action reminders can now be narrowed through `[notify]` with
  `action_overdue_only`, `action_due_within_days`, and `max_action_items`, and
  each delivery can either keep actions inline, emit a dedicated `Action Brief`,
  or run as an action-only reminder channel.
- Deliveries can now further narrow action reminders by feedback status,
  trigger reason, due window, overdue-only mode, and per-channel item caps.
- Feedback-state GitHub sync now uses a single CLI entrypoint:
  `feedback sync --direction push|pull`. Push writes the local feedback state
  into `PAPER_DIGEST_FEEDBACK_JSON`, and pull restores it locally through a
  dedicated short-lived export workflow.
- Feedback entries now also support `snoozed_until` and
  `review_interval_days`, with CLI support, recurring-review due dates,
  overdue escalation tiers, and archive views that hide snoozed items from the
  active review queue while surfacing snoozed and overdue work separately.
- Digest runs now auto-advance feedback state when a snooze window ends, flag
  recurring reviews that have actually come due, and persist those state
  changes after successful delivery so recurring work can resurface without a
  manual edit.
- `feedback sync --direction pull` now supports `--merge-strategy
  newer|local|remote`, so bidirectional feedback sync can resolve conflicts in
  `due_date`, `snoozed_until`, notes, and other structured review fields
  without bluntly overwriting the local file.
- Feedback sync now also supports `--dry-run` and `--show-diff`, so both push
  and pull workflows can preview field-level changes against the current
  GitHub secret before either side is written.
- Local state management now exposes `state action list/reset`, and canonical
  paper detail pages surface the latest remembered action notification reasons
  so you can inspect or re-arm suppressed `Action Brief` reminders without
  hand-editing the state file.
- The archive site now also exposes a dedicated
  `notification-history.html` page that visualizes remembered action
  notification reasons across papers, grouped by trigger code and linked back
  to canonical detail pages.
- `state action reset` now supports `--dry-run`, `--show-match`, and
  `--before YYYY-MM-DD`, so action-notification re-arms can be previewed and
  narrowed to stale entries before the state file is mutated.
- Remembered action-notification state now supports
  `state action sync --direction push|pull`, plus `--dry-run` and
  `--show-diff`, so local `state action reset` operations can preview and sync
  the exact suppression snapshot used by GitHub Actions runs.
- Action reminders now only emit newly changed action states such as snooze
  resumes, first due-soon transitions, overdue escalations, and recurring
  reviews that have actually come due; notified action reasons are persisted in
  state so `Action Brief` does not repeat the same reminder every day, while
  the weekly review page keeps the longer unfinished / overdue / recurring
  backlog visible.
- The manual `Daily Digest` workflow now accepts a temporary `config.toml`
  override input and isolates those validation runs from caches and Pages
  deployment.
- OpenAlex joins arXiv, Crossref, PubMed, and Semantic Scholar as a supported
  literature source.
- Semantic Scholar joins arXiv, Crossref, and PubMed as a supported literature
  source.
- PubMed joins arXiv and Crossref as a third supported literature source.
- Slack incoming webhook delivery joins email, Feishu, and WeCom as a
  first-class notification channel.
- Discord incoming webhook delivery joins email, Feishu, WeCom, and Slack as a
  first-class notification channel.
- Telegram bot delivery joins email, Feishu, WeCom, Slack, and Discord as a
  first-class notification channel.
- Static archive site now includes fixed feed subscription pages, keyword
  tracking pages, and a trends overview alongside the daily archive index.
- Archive subscription pages now publish RSS feeds for both fixed feed views
  and keyword tracking views.
- The scheduled GitHub Actions workflow now restores and saves `output/`
  history, so archive pages, trends, and RSS feeds can accumulate across runs.
- A manual archive backfill workflow can import historical successful
  `Daily Digest` artifacts into `output/`, rebuild the site and RSS, and seed
  the archive cache in one pass while skipping synthetic validation digests.
- The manual backfill workflow now supports configurable run limits and
  inclusive date windows for targeted archive recovery.
- The manual backfill workflow can also run in dry-run mode to preview imports
  and replacements without mutating `output/`, cache, or Pages.
- WeCom webhook delivery joins email and Feishu as a first-class notification
  channel.
- Rule-based Chinese briefing mode now extracts recurring topic terms, assigns
  lightweight paper tags, and organizes "今日重点" around topics instead of
  only feed order.

## [0.4.1] - 2026-04-09

- Configurable request timeout, retry attempts, and retry backoff for upstream
  source fetches.
- Shared network retry handling for transient timeout, `429`, and `5xx` source
  failures across arXiv and Crossref fetches.
- GitHub Actions workflows updated for Node 24 compatibility, including the
  Pages deployment and release paths.

## [0.4.0] - 2026-04-09

- Static archive-site generation from historical digest outputs, including
  daily hit counts, per-feed summaries, and lightweight client-side search.
- GitHub Pages deployment from the scheduled `Daily Digest` workflow.
- Bounded retry and backoff handling for transient arXiv `429` and `5xx`
  responses during scheduled fetches.

## [0.3.0] - 2026-04-08

- Optional OpenAI-backed structured paper analysis with configurable cost caps.
- Top-of-digest highlights plus richer per-paper conclusions, contributions,
  audience guidance, and limitations in Markdown, email, and Feishu output.
- A stronger digest templating path with feed-level key points and a Chinese
  `zh_daily_brief` layout for "今日重点"-style reports.
- Digest template selection is now independent from LLM analysis, so the
  Chinese daily brief can run in rule-based mode without any API key.

## [0.2.0] - 2026-04-08

- Optional SMTP email delivery for generated digests.
- Persistent state-based deduplication across runs.
- Crossref support as a second paper source.
- A scheduled GitHub Actions workflow for daily digest generation.
- A unified delivery layer with feed-level notification fan-out.
- Feishu webhook delivery support.
- Expanded unit coverage for arXiv parsing, Crossref parsing, digest rendering,
  output writing, delivery orchestration, and state management.

## [0.1.0] - 2026-04-08

### Added

- Initial arXiv-backed daily paper digest generator.
- TOML-based configuration with category and keyword filtering.
- Markdown and JSON output writers.
- Local unit tests, CI workflow, and core contributor documentation.
- Pre-commit configuration for local repository hygiene.
- Dependabot configuration for dependency and GitHub Actions updates.
- Release workflow, release checklist, and maintainer-facing documentation.
- Coverage, build, and distribution validation commands.
- CLI-focused unit tests and single-source version metadata.
