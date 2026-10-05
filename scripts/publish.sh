#!/usr/bin/env bash
# Creates github.com/snbaskarraj/throughline-supply-chain-ontology, pushes, and turns on GitHub Pages.
# Needs the GitHub CLI, logged in once with:  gh auth login
set -euo pipefail
REPO="${1:-throughline-supply-chain-ontology}"
cd "$(dirname "$0")/.."
git init -q -b main 2>/dev/null || true
git add -A
git commit -qm "Throughline: supply chain ontology and governed conversational analytics" || true
gh repo create "$REPO" --public --source=. --remote=origin --push \
  --description "Supply chain ontology + governed semantic views + conversational analytics (web, REST, MCP)"
OWNER=$(gh api user -q .login)
gh api -X POST "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null 2>&1 || true
gh workflow run pages.yml -R "$OWNER/$REPO" >/dev/null 2>&1 || true
echo "Repo:      https://github.com/$OWNER/$REPO"
echo "Prototype: https://$OWNER.github.io/$REPO/   (live in ~1 minute, once the pages workflow finishes)"
