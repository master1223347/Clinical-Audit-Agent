# Clinical Proof Mode pilot — root Makefile.
#
# Coverage gates (pilot.md §1.6, wt-01.md step 6):
#   General   pytest --cov=app --cov-branch --cov-fail-under=80
#   Safety    pytest --cov=app/core/safety --cov=app/rules/blocked_advice \
#             --cov-branch --cov-fail-under=100

PYTHON ?= python3
PYTEST ?= python3 -m pytest

EVAL_HOST ?= http://localhost:8000

.PHONY: help verify-wt-01 verify-wt-02 eval eval-fixture eval-live demo precompute precompute-fresh

help:
	@echo "Clinical Proof Mode pilot targets:"
	@echo "  verify-wt-01      backend verification loop"
	@echo "  verify-wt-02      doctor-portal verification loop (Phase 2)"
	@echo "  eval              run the eval harness; auto-selects live vs fixture"
	@echo "                    based on whether $(EVAL_HOST)/health is reachable"
	@echo "  eval-fixture      Phase 2 fixture-mode bars (informational; exits 0)"
	@echo "  eval-live         Phase 3b live-mode bars; HARD GATE — exits 1 on bar miss"
	@echo "  demo              start the localhost demo against the precompute cache"
	@echo "  precompute        run /precompute against all 10 transcripts (idempotent)"
	@echo "  precompute-fresh  destructive: TRUNCATE analyze_responses + claims,"
	@echo "                    then re-run /precompute for all 10 transcripts"

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
	@if curl -sf $(EVAL_HOST)/health > /dev/null 2>&1; then \
		echo "--- Live mode ($(EVAL_HOST)/health reachable) ---"; \
		$(MAKE) eval-live; \
	else \
		echo "--- Fixture mode (no live server at $(EVAL_HOST)) ---"; \
		$(MAKE) eval-fixture; \
	fi

eval-fixture:
	@# Phase 2 fixture mode is decoupled from wt/01 implementation.
	@# Bars are INFORMATIONAL — the fixture claims test bar-computation
	@# correctness, not pass-fail. The hard exit-0 gate lives in eval-live
	@# (per wt-03.md §3.5). The trailing `|| true` keeps `make eval` exit 0
	@# in fixture mode so CI without a live backend still completes cleanly.
	@echo "--- PHI scan ---"
	$(PYTHON) scripts/scan-phi.py docs/eval/pilot-set.json
	@echo "--- Eval tests ---"
	$(PYTEST) tests/eval/ --cov=tests/eval --cov-fail-under=80
	@echo "--- Fixture-mode bars (informational) ---"
	$(PYTHON) tests/eval/run_eval.py \
	  --mode fixture \
	  --dataset docs/eval/pilot-set.json \
	  --out artifacts/eval-fixture.json || true

eval-live:
	@# Phase 3b live mode — HARD GATE. Exit code propagates: bar miss = 1.
	@# Requires a wt-01 backend running on $(EVAL_HOST).
	@echo "--- PHI scan ---"
	$(PYTHON) scripts/scan-phi.py docs/eval/pilot-set.json
	@echo "--- Eval tests (incl. live sticky regression) ---"
	$(PYTEST) tests/eval/ --cov=tests/eval --cov-fail-under=80
	@echo "--- Live-mode bars (hard gate) ---"
	$(PYTHON) tests/eval/run_eval.py \
	  --mode live \
	  --host $(EVAL_HOST) \
	  --dataset docs/eval/pilot-set.json \
	  --out artifacts/eval-live.json

demo:
	@echo "demo: not yet implemented in Phase 1"
	@echo ""
	@echo "Phase 3 will:"
	@echo "  1. ensure precompute cache is warm (make precompute)"
	@echo "  2. start uvicorn on :8000 against .data/claims.db"
	@echo "  3. start the Next.js portal on :3000 against the cached endpoint"
	@exit 1

precompute:
	@# Idempotent — POSTs all 10 transcripts to /precompute. Server skips
	@# entries already cached on (input_id, prompt_version_hash, model_id).
	@echo "--- POST /precompute (idempotent) ---"
	$(PYTHON) -c "import json, httpx, sys; \
	  d = json.load(open('docs/eval/pilot-set.json')); \
	  items = [{'transcript_id': t['id'], 'raw_text': t['rawText'], \
	            'patient_id': t['patientId'], \
	            'context': t.get('context', {})} for t in d['transcripts']]; \
	  r = httpx.post('$(EVAL_HOST)/precompute', json=items, timeout=120.0); \
	  r.raise_for_status(); \
	  print(r.json())"

precompute-fresh:
	@# DESTRUCTIVE: truncates analyze_responses + claims tables, then re-runs
	@# /precompute for all 10 transcripts. Wipes any reviewer-click state in
	@# the demo DB. Use before a fresh demo run or when the prompt hash changes.
	@echo "--- DESTRUCTIVE precompute-fresh ($(EVAL_HOST), $${CLAIMS_DB_PATH:-.data/claims.db}) ---"
	$(PYTHON) scripts/precompute_fresh.py --host $(EVAL_HOST)
