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
	@echo "verify-wt-02: not yet implemented in Phase 1"
	@echo ""
	@echo "Phase 2 (wt/02) will run, in order:"
	@echo "  cd services/web && bun run typecheck"
	@echo "  cd services/web && bun run lint"
	@echo "  cd services/web && bun run test --coverage"
	@exit 1

eval:
	@echo "eval: not yet implemented in Phase 1"
	@echo ""
	@echo "Phase 2 (fixture mode):"
	@echo "  $(PYTHON) tests/eval/run_eval.py --mode=fixture"
	@echo "Phase 3 (live mode, after wt/01 implementation lands):"
	@echo "  $(PYTHON) tests/eval/run_eval.py --mode=live"
	@exit 1

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
