PYTHON ?= python3
VENV_PYTHON := .venv/bin/python
PYTHON_BIN := $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),$(PYTHON))

.PHONY: run test lint format typecheck coverage build release-check check

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

build:
	$(PYTHON_BIN) -m build

release-check:
	$(PYTHON_BIN) -m twine check dist/*

check: test lint typecheck
