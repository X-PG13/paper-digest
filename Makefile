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
	$(PYTHON_BIN) -m tools.check_policies

policy-check-json:
	$(PYTHON_BIN) -m tools.check_policies --format json

policy-check-markdown:
	$(PYTHON_BIN) -m tools.check_policies --json-report-file reports/policy-check-report.json
	$(PYTHON_BIN) -m tools.render_policy_report reports/policy-check-report.json --format markdown

docs-check:
	$(PYTHON_BIN) -m tools.sync_lifecycle_docs --check
	$(PYTHON_BIN) -m tools.check_docs

docs-check-json:
	$(PYTHON_BIN) -m tools.sync_lifecycle_docs --check
	$(PYTHON_BIN) -m tools.check_docs --format json

docs-check-markdown:
	$(PYTHON_BIN) -m tools.sync_lifecycle_docs --check
	$(PYTHON_BIN) -m tools.check_docs --format markdown

docs-check-pr-comment:
	$(PYTHON_BIN) -m tools.sync_lifecycle_docs --check
	$(PYTHON_BIN) -m tools.check_docs --json-report-file reports/docs-check-report.json
	$(PYTHON_BIN) -m tools.render_docs_report reports/docs-check-report.json --format pr-comment --output reports/docs-check-pr-comment.md

workflow-tools:
	$(PYTHON_BIN) -m tools.install_actionlint

workflow-check:
	$(PYTHON_BIN) -m tools.check_workflows

build:
	$(PYTHON_BIN) -m build --no-isolation

release-check:
	$(PYTHON_BIN) -m twine check dist/*

check: lint typecheck policy-check docs-check coverage
