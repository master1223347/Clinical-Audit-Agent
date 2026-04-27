# Clinical Proof Mode — Pilot Plan (v1)

**Status:** Locked (v1.2 — post-eng-review round 2)
**Branch:** `clinical-proofing`
**Audience:** Internal Pipeline Securities team + advisors (Option C — see brainstorming notes in commit history)
**Source spec:** [../clinical-proof-mode/SPEC.md](../clinical-proof-mode/SPEC.md). Appendix A locks pilot decisions and §A.4 enumerates explicit cuts.
**Last updated:** 2026-04-26

> **v1.1 changelog (post-eng-review round 1):** schema gate now lands on `clinical-proofing` base branch (C1); model-aware prompt-cache token thresholds (C2); precompute pipeline keyed on `(input_id, prompt_version_hash, model_id)` to absorb Anthropic outage risk and prompt-staleness (C3); wt/03 split into fixture (parallel) and live (sequential) phases (H1); root `Makefile` committed in Phase 1 (H2); cache-hit + evidence-integrity + sticky-escalation tests added (H3, M3); workspace via tsconfig path alias (H4); doctor actions never retract response-level escalations (H5 + corollary); `extractionType` badge tooltip (M1a); duplicate-claim dedup policy (M2a); zero-claim-transcript reporting (M2b); R6 (Anthropic outage) + R7 (reviewer training) added (M4). Confidence-filter UI deferred to v2 backlog (M1b).

> **v1.2 changelog (post-eng-review round 2):** zero-claim responses now persist to a sibling `analyze_responses` table, structurally separating response-level fields from claim-level fields and making the sticky-escalation rule a structural guarantee rather than a discipline (C4). Fixture-mode harness reads `expected_doctor_action` from each fixture claim — no random sampling, no simulation (H6). `count_tokens()` pinned to Anthropic SDK's `client.messages.count_tokens()` (H7). Phase 1 step 1.7 reframed for single-developer self-merge pattern (M5). `make precompute-fresh` documented as destructive across both tables (M6). wt-02 PR-check grep replaced with checklist item (M7).

---

## 1. PRD

The Clinical Proof Mode pilot is a localhost-only proof-of-trust artifact that demonstrates an internal reviewer can take an AI-extracted clinical claim, see the evidence span the LLM grounded it in, see whether a rule-based safety layer would have caught any unflagged red flag, and accept / edit / reject the claim — with the eval harness producing pass/fail numbers against the seven success bars in §7. The pilot covers SPEC §8.1 (extraction), §8.2 (evidence), §8.3 + Appendix A.1 (confidence + direct/interpretation grading), §8.4 (missing info), §8.5 (follow-up generation), §8.6 + Appendix A.2 (red-flag rules + dual-layer rendering), §8.7 (safety blocker), §8.8 (audit cards), §8.9 + Appendix A.3 (doctor edit semantics with self-classification), §11.1 + §11.2 (analyze + review-claim endpoints), §13.4 (urgent-risk escalation), §17 (edge cases). It explicitly defers §8.10 (separate report generator), §10.6 (quality dashboard), §18 (audit log + RBAC), §19 Phase 5 (longitudinal patterns), and all multi-modal input — those live in [./post-pilot-roadmap.md](./post-pilot-roadmap.md).

## 2. Scope

### In scope

- Four endpoints: `POST /analyze`, `POST /review-claim`, `POST /precompute`, `GET /analyze/cached/{transcript_id}`. Two SQLite tables (`analyze_responses`, `claims`).
- One Anthropic Claude call per `/analyze`, with prompt caching (claude-api skill).
- Rule-based safety blocker and red-flag detection. Per SPEC §8.6: rules first, LLM only to extract facts the rules consume.
- Doctor portal: transcript picker → input view with green/red dual-layer highlights → audit card list → claim edit modal with self-classification radio → accepted-claims summary.
- Eval harness: 10 synthetic transcripts with expected-claim labels, runs all seven success bars in fixture mode (parallel) and live mode (post-integration).

### Out of scope (cut list, see SPEC §A.4)

- Audit log persistence and RBAC (§18).
- Multi-modal input — voice STT, image OCR (§7.1, §8.2).
- Longitudinal pattern review (§19 Phase 5).
- Separate report generator (§8.10) — replaced by the filtered accepted-claims list in the portal.
- Quality dashboard for non-doctors (§10.6) — replaced by the eval harness output.
- "<20s/claim mean review time" success bar (§16.6) — moved to v2 Doctor Handoff (Appendix A of this plan).
- Confidence-filter UI in the audit card list — deferred to v2 (see Appendix A v2 backlog). v1 surfaces all claims with badges.

### Non-negotiable rules (lifted from SPEC + post-review additions, enforced by tests)

- **No claim without evidence.** Drop or mark `riskLevel="needs-review"`.
- **Every medication-change phrase is blocked** with the safe replacement from `app/rules/blocked_advice.py:SAFE_REPLACEMENTS`. Regression-tested in wt/03.
- **Diagnosis inference downgrades to `eventType="patientConcern"`** with `safetyStatus="diagnosisNotConfirmed"`.
- **Urgent-risk path renders the §13.4 escalation message verbatim** (looked up from `app/rules/risk_messages.py`, never authored by the LLM).
- **Original AI claim preserved verbatim** when the doctor edits.
- **No PHI in `docs/eval/pilot-set.json`.** Synthetic transcripts only. CI fails the build if `scripts/scan-phi.py` flags anything.
- **Sticky escalations — structural separation (revised v1.2).** Rule-based escalations (`escalation_message`, `red_flag_only_spans_json`) live on a sibling **`analyze_responses`** table, keyed on `(input_id, prompt_version_hash, model_id)`. They are populated by `/analyze` and `/precompute`, and **immutable thereafter**. `/review-claim` operates on the `claims` table only and cannot reach `analyze_responses` rows by design — the sticky-escalation rule is now a structural guarantee, not a discipline. Bar #6 reads `analyze_responses.escalation_message`. Bar #7 reads `analyze_responses.red_flag_only_spans_json` plus rule matches against raw text. A zero-claim transcript produces a populated `analyze_responses` row and zero `claims` rows; the cached endpoint still serves the escalation payload.
- **Duplicate-claim dedup policy (post-review).** Post-extraction, for each `(eventType, evidence_span_overlap > 50%)` cluster, the higher-confidence claim is kept and the others are dropped. Dropped claims are not persisted, not surfaced, and not counted in any bar. Dedup runs **before** safety screen and persistence.

## 3. Worktree Topology

| Worktree | Path | Branch | Owns |
|---|---|---|---|
| wt/01 | `.worktrees/wt-01-extraction-core/` | `clinical-proof-pilot/extraction-core` | Backend (`app/`) — extraction, safety, follow-up, dedup, precompute, endpoints, SQLite (two tables). **On day 1, lands schema artifacts directly on `clinical-proofing`** so wt/02 and wt/03 can branch from a base that already has the schema. |
| wt/02 | `.worktrees/wt-02-doctor-ui/` | `clinical-proof-pilot/doctor-ui` | `services/web/` Next.js doctor portal. Consumes the schema. |
| wt/03 | `.worktrees/wt-03-eval-harness/` | `clinical-proof-pilot/eval-harness` | `tests/eval/` + `docs/eval/`. Owns the 10-transcript dataset and the eval-bar checks. Phase 2 against fixtures, Phase 3 against live API. |

`packages/shared/types.ts` is the canonical claim-object schema, owned by wt/01, consumed by wt/02 and wt/03.

**Workspace setup (resolves H4):** `packages/shared/` is consumed via TypeScript path aliases — no separate npm package, no workspace tooling. wt/01's day-1 PR commits `services/web/tsconfig.base.json` containing:

```jsonc
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@shared/*": ["../../packages/shared/*"] }
  }
}
```

wt/02 extends this from `services/web/tsconfig.json`. The Python side imports the schema as Pydantic models in `app/models/claim.py`; field names mirror the TS source-of-truth and `scripts/check-schema-drift.py` enforces parity.

Worktrees are created by `scripts/create-worktrees.sh`, which validates the Phase 1 gate before creating wt/02 and wt/03.

## 4. Phase 0 — Pre-flight (already done)

- [x] Spec vendored at `docs/clinical-proof-mode/SPEC.md` with Appendix A locking Q1/Q2/Q3.
- [x] Audience locked: internal-first (Option C).
- [x] Stack locked: Python 3.11 + FastAPI + SQLite, Anthropic Claude with prompt caching, Next.js + TS + shadcn/ui localhost.
- [x] Existing `app/` scaffold inventoried — the pilot fills only pilot-relevant stubs; non-pilot stubs are left untouched.
- [x] Persona for dataset realism (only): Indian GP, chronic gastro patients, AI-skeptical, time-pressed.

## 5. Phase 1 — Schema Gate (wt/01 only, sequential, day 1)

**The schema must land on `clinical-proofing`, not just on the wt/01 feature branch**, so wt/02 and wt/03 can see it when they branch from `clinical-proofing`. This was the round-1 CRITICAL fix.

| Step | Owner | Output | Depends on |
|---|---|---|---|
| 1.1 | wt/01 | `packages/shared/types.ts` — TypeScript types for `ClinicalClaim`, `Evidence`, `RiskAssessment`, `SafetyBlock`, `FollowUpQuestion`, `DoctorAction`, `DoctorReviewStatus`, `ExtractionType` (`"direct" \| "interpretation"`), `DoctorEditOrigin` (`"minor_wording" \| "correction" \| "external_knowledge_override"`), `EventType`, `RiskLevel`, `SafetyStatus`, **`AnalyzeResponse`** (with response-level `escalationMessage` and `redFlagOnlySpans` fields, separate from the claim list). **Single source of truth.** | — |
| 1.2 | wt/01 | `app/models/claim.py` and `app/models/enums.py` extended with `extractionType`, `doctorEditOrigin`, and `RiskLevel.NEEDS_REVIEW`. Pydantic field names match TS field names byte-for-byte. | 1.1 |
| 1.3 | wt/01 | `docs/eval/fixtures/sample-claims.json` — 3-5 hand-written sample claim objects covering: a `direct` extraction, an `interpretation` extraction, a `medicationAdviceBlocked` claim, an urgent-risk claim. **Each claim carries an `expected_doctor_action` field (post-review H6)** with one of: `"accept"`, `"edit_minor_wording"`, `"edit_correction"`, `"edit_external_knowledge_override"`, `"reject"`. The Phase 2 fixture-mode harness reads this field directly to compute bars 1-3 — no random sampling, no simulation function. | 1.1, 1.2 |
| 1.4 | wt/01 | `scripts/check-schema-drift.py` — fails CI if Pydantic field set diverges from TS field set. | 1.1, 1.2 |
| 1.5 | wt/01 | `services/web/tsconfig.base.json` — path alias `@shared/*` → `../../packages/shared/*`. | 1.1 |
| 1.6 | wt/01 | **Root `Makefile`** with targets: `verify-wt-01`, `verify-wt-02`, `eval`, `demo`, `precompute`, `precompute-fresh`. Stubbed in Phase 1; real implementation in Phase 2. Specify `pytest --cov=app --cov-branch --cov-fail-under=80` for the general gate; `pytest --cov=app/core/safety --cov=app/rules/blocked_advice --cov-branch --cov-fail-under=100` for the safety gate. | — |
| 1.7 | wt/01 | **Land steps 1.1-1.6 directly on `clinical-proofing`** via fast-forward push (or self-approved PR if branch protection is on). Tag the resulting commit `pilot/schema-v1` and push the tag. **Self-merge is the expected pattern for this single-developer pilot (post-review M5)** — these are structural commits, not feature changes that need external review. Implementation work continues on `clinical-proof-pilot/extraction-core` from that base. | 1.1-1.6 |

**Gate to Phase 2:** `pilot/schema-v1` tag exists on `clinical-proofing` AND the schema files + `Makefile` are present at that commit. `scripts/create-worktrees.sh` validates this before creating wt/02 and wt/03 worktrees.

## 6. Phase 2 — Parallel Build (days 2-4)

After the Phase 1 gate, dispatch wt/01-implementation, wt/02, and wt/03 in parallel via `superpowers:dispatching-parallel-agents`.

### 6.1 wt/01 — Extraction Core (continues after Phase 1)

| Step | What | Spec § | Test gate |
|---|---|---|---|
| 2.1 | `app/core/evidence.py` — `locate_evidence(claim_text, raw_text)` returns `(start, end)` or raises `EvidenceNotFound`. Reject any claim whose `evidenceText` is not an exact substring of `rawText`. | §8.2 | Unit |
| 2.2 | Verify `app/rules/blocked_advice.py` covers all categories in §8.7. | §8.7 | Unit: `BLOCKED_CATEGORIES` ⊆ `SAFE_REPLACEMENTS` |
| 2.3 | `app/core/safety.py` — `screen_output(input, candidate_text, has_red_flags)` returns `SafetyBlock` or `None`. **100% line + branch coverage.** | §8.7, §17.3, §17.4 | Regression test per category in `BLOCKED_CATEGORIES` |
| 2.4 | `app/rules/red_flag_rules.py` — `match_red_flags(raw_text)` returns `list[(rule_key, start, end)]`. Cover all 8 vomiting + 5 medication red-flag rules from §8.6. | §8.6 | Unit per rule |
| 2.5 | `app/core/extraction.py` — single Anthropic Claude call (claude-api skill, prompt caching). System prompt **cached**: instructions + 3 few-shot examples (one direct, one interpretation, one patientConcern downgrade). Variable input: transcript only. LLM self-classifies `extractionType`; content-word-overlap heuristic forces `interpretation` when overlap < 0.5. Malformed JSON: retry once with appendix; raise on second failure (502). | §8.1, §A.1 | Unit + golden-file (5 transcripts) |
| 2.5a | **Cache-token threshold assertion (post-review C2 + H7).** Maintain `MIN_CACHE_TOKENS_BY_MODEL = {"claude-sonnet-4-6": 1024, "claude-opus-4-7": 1024, "claude-haiku-4-5": 2048}`. **Token counting via Anthropic SDK's `client.messages.count_tokens()`** (the only accurate counter for Claude — `tiktoken` is wrong). Run the assertion at module-import time so it raises **before the FastAPI app binds to a port**. Pad the cached block with style examples if short. | perf, C2, H7 | Unit: mock `count_tokens()` to return below-threshold; assert startup raises |
| 2.5b | **Cache-hit integration test (post-review H3).** Mock the Anthropic client; assert `cache_control` set on the system block; assert `usage.cache_read_input_tokens > 0` on the second call against an identical input. | perf, H3 | Integration |
| 2.5c | **`PROMPT_VERSION_HASH`** = sha256 of the cached system-prompt block. Computed at module load, exposed as `app.core.extraction.PROMPT_VERSION_HASH`. Used as part of the `analyze_responses` cache key. | C3 | Unit: hash changes when prompt changes |
| 2.6 | `app/core/follow_up.py` — generate prioritized follow-up questions from `missingInfo[]`. | §8.5 | Unit |
| 2.7 | **`app/core/dedup.py`** — `dedup_claims(claims)` collapses `(eventType, evidence_span_overlap > 50%)` clusters to highest-confidence claim. Runs before safety screen. | §2 (post-review M2a) | Unit: 3 candidates → 1 survivor |
| 2.7a | **Evidence-span integrity property test (post-review M3).** For 50 random shaped inputs, assert every persisted claim satisfies `claim.evidence_text == claim.raw_text[claim.evidence_start:claim.evidence_end]`. Use `hypothesis` or table-driven. | §8.2, M3 | Property test |
| 2.8 | `app/storage/repository.py` + SQLite **two-table schema** per §6.1.7. No Alembic migrations. DB path from `CLAIMS_DB_PATH` env var, defaults to `.data/claims.db`. | §9.2, C4 | Unit: roundtrip preserves all fields on both tables |
| 2.9 | Wire `POST /analyze`. Pipeline: input → extraction → evidence check → **dedup** → safety screen → red-flag rules → assemble `AnalyzeResponse` (claims + `escalationMessage` + `redFlagOnlySpans`) → **persist: write one row to `analyze_responses` (always, even when zero claims) and N rows to `claims` (one per surfaced claim)** → return. | §11.1, C4 | Integration |
| 2.10 | Wire `POST /review-claim`. Doctor actions update only the `claims` row. **`analyze_responses` is never written to by `/review-claim`** — the structural separation (post-review C4) enforces the sticky-escalation rule by design, not by discipline. | §11.2, §2 sticky-escalation | Integration |
| 2.10a | **Sticky-escalation test (post-review H5).** Create urgent-risk input → `/analyze` → reject the urgent claim via `/review-claim`. Assert response-level `escalationMessage` and `redFlagOnlySpans` (read from `analyze_responses` via the cached endpoint) are **unchanged** across both states. Repeat for an edit-downgrade ("fainted" → "lightheaded"). | §2 sticky-escalation, H5 | Integration |
| 2.11 | **Precompute pipeline (post-review C3, revised v1.2 for C4).** New module `app/core/precompute.py`. Endpoints: `POST /precompute` (body: `[{transcript_id, raw_text, context?}]` — runs full pipeline, writes one row to `analyze_responses` per transcript regardless of claim count, plus N claim rows). `GET /analyze/cached/{transcript_id}` (looks up `analyze_responses` by composite key, JOINs `claims` for the claim list, returns 200 with `{claims: [...], escalationMessage, redFlagOnlySpans}` on hit — including `claims: []` for zero-claim cases — or 404 only when the response was never computed). `make precompute-fresh` truncates **both** tables before re-running. | C3, C4 | Integration: precompute roundtrip; zero-claim transcript still serves escalation payload; prompt-hash change → 404 |
| 2.12 | Verification loop green. | — | `make verify-wt-01` exits 0 |

#### 6.1.7 SQLite schema (revised v1.2 — two tables, structural sticky-escalation)

```sql
-- Response-level data (one row per /analyze call, IMMUTABLE after creation):
CREATE TABLE analyze_responses (
  input_id              TEXT NOT NULL,
  prompt_version_hash   TEXT NOT NULL,
  model_id              TEXT NOT NULL,
  patient_id            TEXT NOT NULL,
  raw_text              TEXT NOT NULL,
  escalation_message    TEXT,                       -- §13.4 verbatim, NULL if not urgent
  red_flag_only_spans_json TEXT,                    -- §A.2 red-layer payload
  created_at            TEXT NOT NULL,
  PRIMARY KEY (input_id, prompt_version_hash, model_id)
);

-- Claim-level data (zero or more rows per response, MUTABLE via /review-claim):
CREATE TABLE claims (
  claim_id              TEXT PRIMARY KEY,
  input_id              TEXT NOT NULL,
  prompt_version_hash   TEXT NOT NULL,
  model_id              TEXT NOT NULL,
  claim_text            TEXT NOT NULL,
  original_claim_text   TEXT,
  event_type            TEXT NOT NULL,
  evidence_text         TEXT NOT NULL,
  evidence_start        INTEGER NOT NULL,
  evidence_end          INTEGER NOT NULL,
  confidence            REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  extraction_type       TEXT NOT NULL CHECK (extraction_type IN ('direct','interpretation')),
  risk_level            TEXT NOT NULL CHECK (risk_level IN ('low','medium','high','urgent','needs-review')),
  safety_status         TEXT NOT NULL,
  doctor_review_status  TEXT NOT NULL DEFAULT 'pending',
  doctor_edit_origin    TEXT CHECK (doctor_edit_origin IN ('minor_wording','correction','external_knowledge_override')),
  created_at            TEXT NOT NULL,
  FOREIGN KEY (input_id, prompt_version_hash, model_id)
    REFERENCES analyze_responses(input_id, prompt_version_hash, model_id)
);

CREATE INDEX claims_response_lookup
  ON claims(input_id, prompt_version_hash, model_id);
```

The two-table separation enforces the sticky-escalation rule **structurally**: `/review-claim` operates on `claims` only and cannot reach `analyze_responses`. A zero-claim transcript writes one `analyze_responses` row and zero `claims` rows; `GET /analyze/cached/{id}` returns 200 with `claims: []` and the escalation payload intact. A 404 means the response was never computed (vs. computed-and-empty) — critical distinction for the demo's central urgent-risk moment.

### 6.2 wt/02 — Doctor UI

| Step | What | Spec § | Test gate |
|---|---|---|---|
| 2.13 | Next.js + shadcn/ui scaffolding under `services/web/`. Localhost only. `tsconfig.json` extends `tsconfig.base.json` (committed by wt/01 in Phase 1). | §10.3 | `bun run typecheck` clean |
| 2.14 | TranscriptPickerPage — lists the 10 synthetic transcripts. | §10.3 | Vitest |
| 2.15 | DualLayerInputView — `rawText` with green spans (claim evidence) and red spans (red-flag-rule matches without a corresponding urgent claim). Both layers use char offsets. | §A.2 | Snapshot test |
| 2.16 | AuditCard — claim text, evidence, confidence, risk-level chip, missingInfo, safetyStatus, **`extractionType` badge** (yellow for `interpretation`), `displayWarning`, Accept / Edit / Reject. | §8.8 | Vitest |
| 2.16a | **`extractionType` badge tooltip (post-review M1a).** Hover/focus renders: "Direct: claim text closely paraphrases the cited evidence span. Interpretation: the AI inferred this beyond what's directly quoted — review carefully." Plain English; no jargon. | §A.1 forward-compat, M1a | Vitest: tooltip renders on hover and focus |
| 2.17 | ClaimEditModal — original claim, evidence, editable corrected-claim, **self-classification radio** (`minor_wording` / `correction` / `external_knowledge_override`), reason, Save (disabled until radio selected) / Cancel. | §10.4, §A.3 | Vitest |
| 2.18 | AcceptedClaimsSummary — only `accepted` and `edited` claims. Replaces report generator. | §A.4 (in-pilot replacement) | Vitest |
| 2.19 | Verification loop green. | — | `make verify-wt-02` exits 0 |

### 6.3 wt/03 — Eval Harness (split into two phases)

#### Phase 2 — fixture mode (parallel with wt/01 implementation)

| Step | What | Spec § | Test gate |
|---|---|---|---|
| 2.20 | `docs/eval/pilot-set.json` — 10 synthetic transcripts hitting every required edge case. Persona for clinical realism only: Indian GP, chronic gastro, AI-skeptical, time-pressed. **No PHI; synthetic only.** Spec: [../eval/pilot-set-spec.md](../eval/pilot-set-spec.md). | §17, §13.4, §A.4 | `scripts/scan-phi.py` exits 0 |
| 2.21 | `docs/eval/pilot-set-labels.json` — for each transcript: `expected_event_types[]`, `expected_red_flag_rules[]`, `expected_safety_categories[]`, `expected_urgent_claim` (bool), `edge_cases[]`. | — | Format check |
| 2.22 | `tests/eval/run_eval.py` with `--mode={fixture,live}`. **Phase 2 implements `--mode=fixture` only.** **Each fixture claim in `docs/eval/fixtures/sample-claims.json` carries an `expected_doctor_action` field (post-review H6)**; the harness reads it directly to compute bars 1-3 — **no random sampling, no simulation function**. Bar-computation logic runs end-to-end against the fixture. Output header: `mode=fixture`. | §15 (subset), H6 | Self-test: bars 1-3 deterministic against the fixture's labeled actions |
| 2.23 | `tests/eval/test_safety_regression.py` — for each category in `BLOCKED_CATEGORIES`, assert at least one transcript in `pilot-set.json` is labeled to trigger it. **No API call needed** — checks dataset coverage. **100% category coverage.** | §8.7 | Test fails if any category lacks a transcript |
| 2.24 | `tests/eval/test_missed_escalations.py` — fixture-mode: for each `expected_red_flag_rules` entry, assert the corresponding fixture's `redFlagOnlySpans` covers the rule's matched span. | §A.2 | Passes only if zero unmatched red-flag rules |
| 2.25 | `tests/eval/test_dataset_variety.py` — every §17 edge case covered, §13.4 urgent transcript present, Indian-context (curd-rice-style) transcript present. | §17 | Variety assertion |
| 2.26 | `scripts/scan-phi.py` + `tests/eval/test_no_phi.py`. | — | exit 0 |
| 2.27 | **Zero-claim-transcript reporting (post-review M2b).** Harness reports transcripts where `/analyze` returned zero claims as a separate counter (`zero_claim_transcripts: N`). They are NOT counted in bars 1-3 (no vacuous-truth 100%). They appear as their own line in the Markdown table. **Bar #6 still applies** — a zero-claim urgent transcript with no `escalationMessage` is a critical failure. | M2b | Unit |

#### Phase 3 — live mode (sequential, after wt/01 implementation lands)

| Step | What | Spec § | Test gate |
|---|---|---|---|
| 3.5 | Wire `--mode=live`. Calls `POST /precompute` to populate `analyze_responses` + `claims` for all 10 transcripts, then reads from `GET /analyze/cached/{transcript_id}` for each. Output header: `mode=live`, `prompt_version_hash`, `model_id`. Re-running without prompt change = cache hit. | C3 | Integration |
| 3.6 | **Sticky-escalation assertions in live mode.** Bar #6 reads `analyze_responses.escalation_message` (via the cached endpoint's `escalationMessage`). Bar #7 reads `analyze_responses.red_flag_only_spans_json` and rule matches. Both bars pass even when the doctor rejects/edits the underlying urgent claim — because `/review-claim` has no path to `analyze_responses` rows. | §2 sticky-escalation, H5, C4 | Integration: reject urgent claim → bar #6 still passes |

## 7. Eval Bars (Pilot Success Criteria)

The pilot is **not done** until all of the following are green in a single `make eval` run:

| # | Bar | Source |
|---|---|---|
| 1 | ≥80% of `direct` claims accepted-or-lightly-edited (`minor_wording` counts as lightly edited) | §A.1 |
| 2 | ≥60% of `interpretation` claims accepted (separate cohort; does not count toward bar 1) | §A.1 |
| 3 | ≤10% of all surfaced claims rejected | §16 |
| 4 | 100% of displayed claims have a visible evidence span | §8.2 |
| 5 | 100% of medication-change advice blocked with safe replacement | §8.7 |
| 6 | Zero urgent-risk transcripts produce a silent (non-escalating) response | §13.4 |
| 7 | Every red-flag-rule match without a matching urgent claim is flagged as a missed escalation | §A.2 |

**Read-from-source clarifications (post-review):**

- **Zero-claim transcripts excluded from bars 1-3** (otherwise vacuous truth gives a free 100%). Reported separately as `zero_claim_transcripts: N`. **Bar #6 still applies to them** — a zero-claim urgent transcript without `escalationMessage` fails.
- **Bar #6 reads from `analyze_responses.escalation_message`, not from claim status.** Sticky by structural separation (C4).
- **Bar #7 reads from `analyze_responses.red_flag_only_spans_json` plus rule matches against raw text, not from claim downgrades.** Sticky by structural separation (C4).
- **`mode=live` reads from the `analyze_responses` table.** Re-running the harness without a prompt change is a cache hit (fast, deterministic). Use `make precompute-fresh` to invalidate.
- **Fixture-mode bars 1-3 read `expected_doctor_action` directly from each fixture claim (H6).** No random sampling; no simulation function. Determinism by construction.

**Internal-audience addendum (qualitative bar, checked at demo time):** any internal reviewer can pick a random claim from the audit card and defend its evidence + safety status from the card alone, **without consulting SPEC.md**. If a reviewer has to open the SPEC, that is a finding. (R7 mitigation: distribute a 1-page briefing card to attendees 30 min before demo.)

## 8. Phase 3 — Integration (day 4)

| Step | What | Owner |
|---|---|---|
| 3.1 | wt/02 swaps fixture rendering for live `/analyze/cached/{id}` calls. | wt/02 |
| 3.2 | wt/03 wires `--mode=live` (calls `/precompute` once, then reads `/analyze/cached`). | wt/03 |
| 3.3 | `make precompute` runs end-to-end: 10 transcripts → SQLite (`analyze_responses` + `claims`). `make eval --mode=live` reads from cache, all 7 bars green. | all |
| 3.4 | End-to-end smoke run: pick all 10 transcripts in the portal, accept/edit/reject each, sticky-escalation check still green (verified by re-reading `analyze_responses` and confirming no field mutated). | all |
| 3.5 | Three PRs opened, each with §-coverage table. Verification-loop green required to merge. | all |

## 9. Phase 4 — Internal Demo (day 5)

Full demo script in [../demo/walkthrough.md](../demo/walkthrough.md). 25 minutes total. Outline:

1. **(2 min)** What this is — localhost proof-of-trust pilot, audience is us, eval harness is the artifact.
2. **(4 min)** The urgent-risk transcript — show dual-layer rendering catching the missed escalation. **Central moment.**
3. **(3 min)** Diagnosis-inference transcript — show the safety blocker downgrading to `patientConcern`.
4. **(3 min)** Medication-change-request transcript — show the blocker, show the safe replacement.
5. **(5 min)** Open the eval harness output: all 7 bars, broken out by direct vs. interpretation cohort.
6. **(5 min)** Random-claim defense exercise (the qualitative ADD-for-v1 bar).
7. **(3 min)** What's next: read the v2 Doctor Handoff appendix, schedule doctor sourcing.

The demo runs against the precompute cache by default (R6 mitigation — Anthropic outage doesn't kill the demo). A "Re-run live" button is available behind the scenes for skeptics.

## 10. Per-Worktree Contract (binding)

Each worktree must deliver:

1. **PRD** — one paragraph in `docs/plan/worktrees/wt-NN.md` referencing the SPEC §-clauses it covers.
2. **TDD discipline** — tests written before implementation. RED → GREEN → REFACTOR. 80% line + branch coverage floor (`pytest --cov=app --cov-branch --cov-fail-under=80` or `vitest --coverage`). **100% line + branch on the safety blocker** in wt/01 and on the safety regression suite in wt/03.
3. **Schema gate** (wt/01 only) — `packages/shared/types.ts`, `docs/eval/fixtures/sample-claims.json` (with `expected_doctor_action` per claim), `services/web/tsconfig.base.json`, root `Makefile`, and `scripts/check-schema-drift.py` committed to **`clinical-proofing`** and tagged `pilot/schema-v1` before downstream worktrees dispatch.
4. **Dataset gate** (wt/03 only) — `docs/eval/pilot-set.json` and `docs/eval/pilot-set-labels.json` committed; PHI-scanner CI green.
5. **Verification loop** green before review request.
6. **PR summary** lists §-clauses covered and links each to the test that exercises it.

## 11. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | LLM extraction quality on Indian-GP transcripts is poor (code-switching, regional food terms, time-pressed phrasing). | Med | High — kills the headline acceptance number | Cache the extraction system prompt; include 3 few-shot examples covering Indian-context patterns; smoke-run against the dataset *early* (Phase 2 step 2.5), not Phase 3. |
| R2 | Schema drift between Pydantic models and TypeScript types. | Med | High — invisible until integration day | Single source of truth in `packages/shared/types.ts`; CI gate on `scripts/check-schema-drift.py`. |
| R3 | Safety blocker false negative — a med-change phrase slips past. | Low | Critical — violates non-negotiable rule | 100% line + branch coverage on safety blocker; one regression test per category in `BLOCKED_CATEGORIES`; rule-first design (LLM never authors final patient-facing text). |
| R4 | Dual-layer rendering misaligns: red-flag rule offsets and LLM evidence offsets use different anchoring. | Med | Med — visible inconsistency erodes the demo | Both layers use the same character-offset scheme into `rawText`; evidence-span integrity property test (step 2.7a); visual snapshot tests in wt/02. |
| R5 | The 10-transcript dataset isn't varied enough — every transcript looks the same. | Med | High — eval bars become meaningless | [../eval/pilot-set-spec.md](../eval/pilot-set-spec.md) enumerates required variety; wt/03 dataset commit reviewed against that spec; eval harness includes a variety-coverage assertion (step 2.25). |
| **R6** | **Anthropic API outage on demo day** OR per-call latency (2-10s) makes the portal feel slow even when working. | Low (outage) / High (latency) | Critical for outage; Med for latency | Pre-compute all 10 transcripts to SQLite via `make precompute` before the demo. Portal reads from cache (`GET /analyze/cached/{id}`); eval harness's `--mode=live` reads from the same cache. Live re-compute available behind a button for skeptics. Cache invalidates automatically on prompt change (keyed on `prompt_version_hash`). |
| **R7** | **Internal reviewers fail random-claim defense** not because the system is wrong but because they haven't been trained on the vocabulary (`extractionType`, `safetyStatus`, "needs-review"). | Med | Med — qualitative bar produces false negatives | 1-page briefing card distributed to attendees 30 min before demo. Card defines: direct vs. interpretation, the four `safetyStatus` values, the dual-layer rendering legend. Owner: demo runner. |

## 12. Open Questions (with proposed defaults)

| # | Question | Proposed default | Confirm before |
|---|---|---|---|
| OQ1 | Confidence threshold for surfacing claims to the portal — show all, or filter? | Surface all. `interpretation` claims badged yellow with hover explainer; `confidence < 0.4` additionally badged "low confidence — needs review" per §17.5. No filtering. **Filter UI deferred to v2** (see Appendix A v2 backlog). | wt/02 dispatch |
| OQ2 | Transcript language. | English with embedded Hindi/regional food terms ("curd rice", "ghee", "rasam", "loose motions"). Full-Hindi transcripts cut for v1. | wt/03 dataset commit |
| OQ3 | Localhost SQLite persistence — file path, lifetime? | `.data/claims.db`, gitignored, fresh per `make demo`. Eval harness uses `.data/eval-<timestamp>.db`. | wt/01 storage implementation |
| OQ4 | Anthropic prompt cache strategy, **per-model thresholds, and token-counter implementation**. | Cache the system prompt (extraction instructions + 3 few-shot examples). Variable input is the transcript only. **`MIN_CACHE_TOKENS_BY_MODEL`** = `{Sonnet 4.6: 1024, Opus 4.7: 1024, Haiku 4.5: 2048}`. **Token counting via Anthropic SDK's `client.messages.count_tokens()`** — `tiktoken` is wrong for Claude. The assertion runs at module-import time and **must raise before the FastAPI app binds to a port**. wt/01 includes a unit test that mocks `count_tokens()` to return below threshold and asserts startup raises. | wt/01 extraction implementation |
| OQ5 | Mocking strategy for wt/02 and wt/03 in Phase 2 — TS types only or also a fixture file? | Both. Types from `packages/shared/types.ts`, fixture at `docs/eval/fixtures/sample-claims.json` (delivered in Phase 1 step 1.3, with `expected_doctor_action` per claim). | Phase 1 schema gate |
| OQ6 | LLM returns malformed JSON (missing required field). | Retry once with a "your previous response was malformed" appendix (cache hit preserved — same system prompt). If still bad, return `502` with the raw output for debugging. **Fail loudly, never silently.** | wt/01 extraction implementation |
| **OQ7** | **Precompute cache invalidation strategy.** | Cache key is `(input_id, prompt_version_hash, model_id)`, the primary key of `analyze_responses`. `prompt_version_hash` = sha256 of the cached system-prompt block, computed at module-load. A prompt change in wt/01 automatically invalidates downstream cached outputs (lookup misses → fresh `/analyze` call). **`make precompute-fresh` is destructive (post-review M6)** — it truncates BOTH `analyze_responses` AND `claims`, nuking any demo state from manual reviewer clicks. Only run when you want a clean batch. | wt/01 precompute implementation |

---

## Appendix A — v2 Doctor Handoff

What changes when a real pilot doctor is sourced. **The portal does not change.** No internal-mode toggle, no debug overlays, no doctor-mode flag. Whoever clicks Accept/Edit/Reject is the doctor. This is the forward-compat guarantee.

| Today (internal-first v1) | v2 (named doctor) |
|---|---|
| Internal Pipeline Securities team clicks Accept/Edit/Reject. | Named doctor (e.g., "Dr X at clinic Y in Bangalore") clicks the same buttons. |
| Eval harness output is interpreted by the team. | Doctor reviews the same harness output; team interprets the *delta* between internal and doctor results. |
| Success bar excludes "<20s/claim". | Add `<20s/claim mean review time` measured during a timed live session with the doctor. |
| Demo is an internal walkthrough. | Demo becomes a 30-minute paper-prototype call: 10 min context, 15 min the doctor reviews 3-5 claims live, 5 min debrief. |
| Dataset is synthetic with Indian-GP persona. | Dataset stays synthetic (no real patient data ever, even after sourcing). Persona may be replaced or expanded based on the doctor's actual specialty. |

**No code changes** for v2 except: (a) timing instrumentation hook in the portal — track `claim_review_started_at` / `claim_review_finished_at` per claim and emit them on `/review-claim`; (b) eval harness adds bar #8 for `<20s/claim` once timing data exists.

### v2 backlog (deferred from v1, captured here so they don't get lost)

- **Confidence-filter UI in the audit card list (M1b deferred).** v1 surfaces all claims with badges. A real doctor may want a "hide claims with confidence < N" filter. Re-spec when a real doctor uses the portal in v2 — the filter behavior should be informed by what they actually skim past, not designed in advance for an audience we haven't met. YAGNI for v1.
- **Reviewer onboarding flow.** v1's R7 mitigation is a 1-page briefing card distributed manually. v2 should bake a 60-second tutorial into the portal's first-launch flow.
- **Cache-staleness UI hint.** v1 silently re-runs `/analyze` on cache miss. v2 should surface "this result was generated [N hours ago] against prompt version X" to the reviewer when they're looking at cached output.

---

*This plan is locked at v1.2 (post-eng-review round 2). Changes require updating Appendix A of the SPEC and re-running plan-eng-review.*
