# Release Checklist

Use this checklist when cutting a new release of AtlasBridge.

## Pre-Release

- [ ] All CI checks green on `main`
- [ ] `__init__.py` version updated
- [ ] `pyproject.toml` version updated (must match `__init__.py`)
- [ ] `CHANGELOG.md` updated with release date and notes
- [ ] No `[Unreleased]` items remaining that should be in this release
- [ ] Safety tests pass: `pytest tests/safety/ -v`
- [ ] Full test suite passes: `pytest tests/ -q`
- [ ] Coverage meets floor: `pytest --cov=atlasbridge`

## Invariant Verification

- [ ] No changes to `core/`, `os/`, `channels/`, `adapters/` unless explicitly planned
- [ ] `BaseAdapter` and `BaseChannel` ABCs unchanged (contract freeze)
- [ ] Policy DSL schema unchanged (contract freeze)
- [ ] CLI command set unchanged (contract freeze)
- [ ] Dashboard binds to loopback by default
- [ ] No new production dependencies added

## Release

- [ ] Commit version bump: `chore: bump version to X.Y.Z`
- [ ] Push to `main`
- [ ] Create annotated tag: `git tag -a vX.Y.Z -m "vX.Y.Z — Release Title"`
- [ ] Push tag: `git push origin vX.Y.Z`
- [ ] Verify PyPI publish workflow completes successfully
- [ ] Verify package on PyPI: `pip index versions atlasbridge`

## Post-Release

- [ ] Create GitHub release with release notes
- [ ] Update `CLAUDE.md` roadmap table
- [ ] Update `docs/roadmap-90-days.md`
- [ ] Update memory files if applicable
- [ ] Verify: `pip install atlasbridge==X.Y.Z && atlasbridge version`
