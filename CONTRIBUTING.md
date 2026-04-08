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
make test
make lint
make typecheck
make coverage
make build
```

To generate a sample digest locally:

```bash
make run
```

To keep local commits clean, install the pre-commit hooks:

```bash
pre-commit install
```

## Pull Request Guidelines

- Keep changes focused and explain the user-facing impact.
- Add or update tests for behavior changes.
- Update `README.md` and `CHANGELOG.md` when the change affects usage or release notes.
- Prefer small, reviewable commits over large mixed refactors.

## Project Standards

- Python 3.12+ only.
- New code should be type-annotated.
- User-visible failures should produce actionable error messages.
- Network integrations should be deterministic enough for unit tests to mock.
