#!/usr/bin/env bash
#
# sam-deploy.sh
#
# Wrapper around `sam deploy` that runs the ruff gate first. SAM has no native
# pre-deploy hook, so use this wrapper instead of calling `sam deploy` directly:
#
#   ./scripts/sam-deploy.sh --guided
#   ./scripts/sam-deploy.sh --profile my-profile
#
# All arguments are forwarded verbatim to `sam deploy`.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Gate: lint + format must pass before we deploy.
"$REPO_ROOT/scripts/ruff-gate.sh"

echo "sam-deploy: ruff gate passed, running 'sam deploy $*'..."
exec sam deploy "$@"
