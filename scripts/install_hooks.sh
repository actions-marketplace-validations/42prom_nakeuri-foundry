#!/usr/bin/env bash
set -euo pipefail
chmod +x .githooks/pre-push 2>/dev/null || true
git config core.hooksPath .githooks
echo "Nakeuri Flutter Foundry Git hooks enabled."
