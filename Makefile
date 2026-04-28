PYTHON ?= python3
VENV_PYTHON := .venv/bin/python
PYTHON_BIN := $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),$(PYTHON))

.PHONY: run test lint format typecheck coverage policy-check policy-check-json policy-check-markdown docs-check docs-check-json docs-check-markdown docs-check-pr-comment workflow-tools workflow-check build release-check check

run:
	$(PYTHON_BIN) -m paper_digest --config config.toml

test:
	$(PYTHON_BIN) -m unittest discover -s tests -v

lint:
	$(PYTHON_BIN) -m ruff check .

format:
	$(PYTHON_BIN) -m ruff format .

typecheck:
	$(PYTHON_BIN) -m mypy paper_digest

coverage:
	$(PYTHON_BIN) -m coverage run -m unittest discover -s tests -v
	$(PYTHON_BIN) -m coverage report

policy-check:
	$(PYTHON_BIN) tools/check_policies.py

policy-check-json:
	$(PYTHON_BIN) tools/check_policies.py --format json

policy-check-markdown:
	$(PYTHON_BIN) tools/check_policies.py --json-report-file reports/policy-check-report.json
	$(PYTHON_BIN) tools/render_policy_report.py reports/policy-check-report.json --format markdown

docs-check:
	$(PYTHON_BIN) tools/sync_lifecycle_docs.py --check
	$(PYTHON_BIN) tools/check_docs.py

docs-check-json:
	$(PYTHON_BIN) tools/sync_lifecycle_docs.py --check
	$(PYTHON_BIN) tools/check_docs.py --format json

docs-check-markdown:
	$(PYTHON_BIN) tools/sync_lifecycle_docs.py --check
	$(PYTHON_BIN) tools/check_docs.py --format markdown

docs-check-pr-comment:
	$(PYTHON_BIN) tools/sync_lifecycle_docs.py --check
	$(PYTHON_BIN) tools/check_docs.py --json-report-file reports/docs-check-report.json
	$(PYTHON_BIN) tools/render_docs_report.py reports/docs-check-report.json --format pr-comment --output reports/docs-check-pr-comment.md

workflow-tools:
	$(PYTHON_BIN) tools/install_actionlint.py

workflow-check:
	$(PYTHON_BIN) tools/check_workflows.py

build:
	$(PYTHON_BIN) -m build --no-isolation

release-check:
	$(PYTHON_BIN) -m twine check dist/*

check: lint typecheck policy-check docs-check coverage
