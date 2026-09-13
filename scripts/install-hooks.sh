#!/usr/bin/env bash
#
# install-hooks.sh
#
# Points git at the versioned .githooks/ directory so the pre-push ruff gate
# is active. Run once after cloning the repo:
#
#   ./scripts/install-hooks.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh 2>/dev/null || true

echo "install-hooks: core.hooksPath set to .githooks"
echo "install-hooks: ruff gate will now run on 'git push'."
