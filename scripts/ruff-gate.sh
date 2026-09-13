#!/usr/bin/env bash
#
# ruff-gate.sh
#
# Runs ruff lint and format over the project, auto-applying safe fixes, then
# verifies the tree is clean. Exits non-zero if any lint error or formatting
# difference remains after auto-fixing (i.e. a problem that needs a human).
#
# Used by the git pre-push hook and the sam-deploy wrapper so that no code is
# pushed or deployed without passing ruff.
#
# Requires either `ruff` on PATH or `uv`/`uvx` (preferred, per project
# tooling). No global install is needed when uv is present.

set -euo pipefail

# Resolve repo root regardless of where the script is invoked from.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Pick a ruff runner: prefer an installed `ruff`, then fall back to `uvx`.
if command -v ruff >/dev/null 2>&1; then
  RUFF=(ruff)
elif command -v uvx >/dev/null 2>&1; then
  RUFF=(uvx ruff)
elif command -v uv >/dev/null 2>&1; then
  RUFF=(uv tool run ruff)
else
  echo "ruff-gate: neither 'ruff' nor 'uv/uvx' found on PATH." >&2
  echo "ruff-gate: install uv (https://docs.astral.sh/uv/) or ruff and retry." >&2
  exit 1
fi

echo "ruff-gate: applying safe lint fixes..."
PRE_FIX_HASH="$(git stash create 2>/dev/null || true)"
"${RUFF[@]}" check --fix .

echo "ruff-gate: applying formatting..."
"${RUFF[@]}" format .

# Re-verify: after auto-fixing, everything must be clean. Any remaining lint
# error (e.g. an unsafe fix that ruff won't apply automatically) or format
# drift blocks the push/deploy.
echo "ruff-gate: verifying lint is clean..."
"${RUFF[@]}" check .

echo "ruff-gate: verifying formatting is clean..."
"${RUFF[@]}" format --check .

# If ruff's auto-fixes changed the working tree relative to the snapshot taken
# before we ran it, surface those files so they can be committed. We compare
# against the pre-fix snapshot so unrelated pre-existing edits do not trip the
# gate -- only changes ruff itself introduced do.
POST_FIX_HASH="$(git stash create 2>/dev/null || true)"
if [ "$PRE_FIX_HASH" != "$POST_FIX_HASH" ]; then
  echo "" >&2
  echo "ruff-gate: ruff auto-fixed files. Review and commit the changes below," >&2
  echo "           then retry your push/deploy:" >&2
  echo "" >&2
  git -P diff --stat >&2
  exit 1
fi

echo "ruff-gate: all ruff checks passed."
