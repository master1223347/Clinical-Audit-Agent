#!/usr/bin/env bash
# Create the three pilot worktrees per docs/plan/pilot.md §3.
# Pattern: superpowers:using-git-worktrees.
#
# Worktrees are placed under .worktrees/ inside the repo (gitignored).
# Each worktree is on a fresh branch off `clinical-proofing`.
#
# Usage: bash scripts/create-worktrees.sh
# Idempotent: re-running skips existing worktrees.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
WT_DIR="$ROOT/.worktrees"
BASE_BRANCH="clinical-proofing"

mkdir -p "$WT_DIR"

# Add .worktrees/ to .gitignore if missing
if ! grep -qxF '.worktrees/' "$ROOT/.gitignore" 2>/dev/null; then
  echo '' >> "$ROOT/.gitignore"
  echo '# Pilot worktrees (created by scripts/create-worktrees.sh)' >> "$ROOT/.gitignore"
  echo '.worktrees/' >> "$ROOT/.gitignore"
  echo "added .worktrees/ to .gitignore"
fi

create_wt() {
  local slug="$1"
  local branch="$2"
  local path="$WT_DIR/$slug"

  if [ -d "$path" ]; then
    echo "wt: $path already exists, skipping"
    return 0
  fi

  if git -C "$ROOT" rev-parse --verify "$branch" >/dev/null 2>&1; then
    echo "wt: branch $branch exists; checking out into worktree"
    git -C "$ROOT" worktree add "$path" "$branch"
  else
    echo "wt: creating $path on new branch $branch from $BASE_BRANCH"
    git -C "$ROOT" worktree add -b "$branch" "$path" "$BASE_BRANCH"
  fi
}

create_wt "wt-01-extraction-core" "clinical-proof-pilot/extraction-core"
create_wt "wt-02-doctor-ui"        "clinical-proof-pilot/doctor-ui"
create_wt "wt-03-eval-harness"     "clinical-proof-pilot/eval-harness"

echo
echo "Worktrees:"
git -C "$ROOT" worktree list
echo
echo "Dispatch briefs: docs/plan/worktrees/{wt-01,wt-02,wt-03}.md"
echo "Gate: wt/02 and wt/03 must wait for wt/01 to tag pilot/schema-v1."
