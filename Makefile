# Clinical Proof Mode pilot — root Makefile.
#
# Coverage gates (pilot.md §1.6, wt-01.md step 6):
#   General   pytest --cov=app --cov-branch --cov-fail-under=80
#   Safety    pytest --cov=app/core/safety --cov=app/rules/blocked_advice \
#             --cov-branch --cov-fail-under=100

PYTHON ?= python3
PYTEST ?= python3 -m pytest

.PHONY: help verify-wt-01 verify-wt-02 eval demo precompute precompute-fresh

help:
	@echo "Clinical Proof Mode pilot targets:"
	@echo "  verify-wt-01      backend verification loop"
	@echo "  verify-wt-02      doctor-portal verification loop (Phase 2)"
	@echo "  eval              run the eval harness (Phase 2 fixture / Phase 3 live)"
	@echo "  demo              start the localhost demo against the precompute cache"
	@echo "  precompute        run /precompute against all 10 transcripts (idempotent)"
	@echo "  precompute-fresh  destructive: truncate analyze_responses + claims, then re-run"

verify-wt-01:
	$(PYTEST) tests/
	$(PYTHON) -m ruff check app/
	$(PYTHON) scripts/check-schema-drift.py
	$(PYTEST) --cov=app --cov-branch --cov-fail-under=80
	$(PYTEST) tests/safety/ --cov=app.core.safety --cov=app.rules.blocked_advice --cov-branch --cov-fail-under=100

verify-wt-02:
	cd services/web && bun run typecheck
	cd services/web && bun run lint
	cd services/web && bun run test --coverage

eval:
	@# Phase 2: fixture mode (decoupled from wt/01 implementation).
	@# Phase 3 live mode requires wt/01 /precompute endpoint on localhost:8000.
	@#
	@# Fixture-mode bars are INFORMATIONAL in Phase 2 — the fixture claims are
	@# intentionally designed to test bar computation correctness, not to pass
	@# all 7 bars. The hard exit-0 gate on bar values applies in Phase 3 live
	@# mode (see wt-03.md step 3.5). Bars 1-3 failing in fixture mode is expected
	@# and tested by test_main_fixture_mode_returns_nonzero_when_bars_fail.
	@echo "--- PHI scan ---"
	$(PYTHON) scripts/scan-phi.py docs/eval/pilot-set.json
	@echo "--- Eval tests ---"
	$(PYTEST) tests/eval/ --cov=tests/eval --cov-fail-under=80
	@echo "--- Fixture-mode bars (informational) ---"
	$(PYTHON) tests/eval/run_eval.py \
	  --mode fixture \
	  --dataset docs/eval/pilot-set.json \
	  --out artifacts/eval-fixture.json || true

demo:
	@echo "demo: not yet implemented in Phase 1"
	@echo ""
	@echo "Phase 3 will:"
	@echo "  1. ensure precompute cache is warm (make precompute)"
	@echo "  2. start uvicorn on :8000 against .data/claims.db"
	@echo "  3. start the Next.js portal on :3000 against the cached endpoint"
	@exit 1

precompute:
	@echo "precompute: not yet implemented in Phase 1"
	@echo ""
	@echo "Phase 3 will POST /precompute with all 10 transcripts. Idempotent — only"
	@echo "re-runs entries that miss the (input_id, prompt_version_hash, model_id) cache."
	@exit 1

precompute-fresh:
	@echo "precompute-fresh: not yet implemented in Phase 1"
	@echo ""
	@echo "Phase 3 will TRUNCATE both analyze_responses and claims, then run /precompute."
	@echo "Destructive — wipes any manual reviewer click state in the demo DB."
	@exit 1
