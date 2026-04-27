#!/usr/bin/env bash
# Create the three pilot worktrees per docs/plan/pilot.md §3.
# Pattern: superpowers:using-git-worktrees.
#
# Worktrees are placed under .worktrees/ inside the repo (gitignored).
# Each worktree is on a fresh branch off `clinical-proofing`.
#
# Phase 1 schema gate:
#   wt/01 can be created at any time (it's the worktree that DOES Phase 1).
#   wt/02 and wt/03 require the schema to have landed on `clinical-proofing`
#   (the base branch they will branch from). This script validates the gate
#   before creating wt/02 and wt/03 — if the schema artifacts are missing,
#   it skips them and exits non-zero with instructions.
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

# Phase 1 gate: schema artifacts must be on `clinical-proofing` before wt/02 and wt/03 dispatch.
# Validates by querying git for each required path at the tip of the base branch.
validate_schema_gate() {
  if ! git -C "$ROOT" rev-parse --verify "$BASE_BRANCH" >/dev/null 2>&1; then
    echo "ERROR: base branch $BASE_BRANCH does not exist"
    return 1
  fi

  local missing=0
  local required_paths=(
    "packages/shared/types.ts"
    "docs/eval/fixtures/sample-claims.json"
    "scripts/check-schema-drift.py"
    "services/web/tsconfig.base.json"
    "Makefile"
  )

  for path in "${required_paths[@]}"; do
    if ! git -C "$ROOT" cat-file -e "$BASE_BRANCH:$path" 2>/dev/null; then
      echo "  MISSING on $BASE_BRANCH: $path"
      missing=1
    fi
  done

  if [ "$missing" = "1" ]; then
    return 1
  fi

  if ! git -C "$ROOT" rev-parse --verify "pilot/schema-v1" >/dev/null 2>&1; then
    echo "  WARNING: tag pilot/schema-v1 not found locally. Phase 1 PR may not be merged yet, or you need 'git fetch --tags'."
    # Don't block — the files are present, that's what matters for branching.
  fi

  return 0
}

# wt/01 owns Phase 1 — always create it.
create_wt "wt-01-extraction-core" "clinical-proof-pilot/extraction-core"

# wt/02 and wt/03 depend on the Phase 1 schema gate.
echo
echo "Validating Phase 1 schema gate on $BASE_BRANCH..."
if validate_schema_gate; then
  echo "  Phase 1 schema gate: OK"
  echo
  create_wt "wt-02-doctor-ui"    "clinical-proof-pilot/doctor-ui"
  create_wt "wt-03-eval-harness" "clinical-proof-pilot/eval-harness"
else
  echo
  echo "Phase 1 schema gate NOT complete — skipping wt/02 and wt/03."
  echo "  wt/01 must first land its day-1 PR on $BASE_BRANCH (see docs/plan/worktrees/wt-01.md)."
  echo "  After that PR merges and 'pilot/schema-v1' is tagged, re-run this script."
  echo
  echo "Worktrees so far:"
  git -C "$ROOT" worktree list
  exit 1
fi

echo
echo "Worktrees:"
git -C "$ROOT" worktree list
echo
echo "Dispatch briefs: docs/plan/worktrees/{wt-01,wt-02,wt-03}.md"
