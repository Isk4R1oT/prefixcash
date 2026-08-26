# Releasing prefixcash

## One-time setup: Trusted Publishing on PyPI (browser, needs your login)

1. Go to https://pypi.org/project/prefixcash/ (the project already exists).
2. Project settings → **Publishing** → **Add a new publisher**:
   - PyPI project name: `prefixcash`
   - Owner: `Isk4R1oT`
   - Repository: `prefixcash`
   - Workflow name: `publish.yml`
3. Save. No token is stored anywhere after this.

## Every release (after the setup)

```bash
./scripts/release.sh 0.3.0
```

What it does:
1. bumps `version` in `pyproject.toml` and `__version__` in `src/prefixcash/__init__.py`;
2. commits, tags `v0.3.0`, pushes `main` + the tag;
3. `.github/workflows/publish.yml` runs on the tag: verifies the tag matches
   `__version__`, builds the sdist + wheel, and publishes to PyPI via
   trusted publishing (no tokens).

Check the result: https://pypi.org/project/prefixcash/

## Fallback (no trusted publishing yet): token publish

```bash
export UV_PUBLISH_TOKEN=pypi-...      # revoke it right after use
uv build
uv publish
```

## Version format

PEP 440: `0.3.0`, `0.3.0rc1`, `1.0.0`. Tags are `v<version>`.
