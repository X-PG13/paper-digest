# Releasing

This project uses Git tags to trigger release builds.

## Before Tagging

1. Ensure `CHANGELOG.md` is updated.
2. Confirm the version in `paper_digest/__about__.py`.
3. Run the full verification suite:

```bash
make check
make coverage
make build
```

4. Verify the built distributions locally:

```bash
python -m twine check dist/*
```

## Create a Release

1. Commit the release changes.
2. Create and push a tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

3. The GitHub Actions release workflow will build the package, validate it, and
   attach the artifacts to a GitHub release.

## After Release

1. Bump the version for the next development cycle if needed.
2. Add a new unreleased section to `CHANGELOG.md`.
3. Verify that the GitHub release contains both the wheel and source archive.
