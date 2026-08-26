#!/usr/bin/env bash
set -euo pipefail
# Release script: bump version, commit, tag, push -> CI publishes to PyPI (trusted publishing).
# Usage: ./scripts/release.sh 0.3.0
VERSION="${1:?usage: ./scripts/release.sh <version> (e.g. 0.3.0)}"
cd "$(dirname "$0")/.."

python3 - "$VERSION" <<'PY'
import pathlib
import re
import sys

version = sys.argv[1]
for path in ("pyproject.toml", "src/prefixcash/__init__.py"):
    p = pathlib.Path(path)
    t = p.read_text(encoding="utf-8")
    old = t
    if path.endswith(".toml"):
        t = re.sub(r'(?m)^version = "[^"]*"', f'version = "{version}"', t, count=1)
    else:
        t = re.sub(r'__version__ = "[^"]*"', f'__version__ = "{version}"', t, count=1)
    if t == old:
        raise SystemExit(f"version marker not found in {path}")
    p.write_text(t, encoding="utf-8")
    print(f"bumped {path} -> {version}")
PY

git add pyproject.toml src/prefixcash/__init__.py
git commit -m "release: v${VERSION}"
git tag "v${VERSION}"
git push origin main --tags
echo "Tag v${VERSION} pushed. CI builds and publishes to PyPI (trusted publishing)."
