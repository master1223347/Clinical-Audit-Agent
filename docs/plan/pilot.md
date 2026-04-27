# Clinical Proof Mode — Pilot Plan (v1)

**Status:** Locked
**Branch:** `clinical-proofing`
**Audience:** Internal Pipeline Securities team + advisors (Option C — see brainstorming notes in commit history)
**Source spec:** [../clinical-proof-mode/SPEC.md](../clinical-proof-mode/SPEC.md). Appendix A locks pilot decisions and §A.4 enumerates explicit cuts.
**Last updated:** 2026-04-26

---

## 1. PRD

The Clinical Proof Mode pilot is a localhost-only proof-of-trust artifact that demonstrates an internal reviewer can take an AI-extracted clinical claim, see the evidence span the LLM grounded it in, see whether a rule-based safety layer would have caught any unflagged red flag, and accept / edit / reject the claim — with the eval harness producing pass/fail numbers against the seven success bars in §7. The pilot covers SPEC §8.1 (extraction), §8.2 (evidence), §8.3 + Appendix A.1 (confidence + direct/interpretation grading), §8.4 (missing info), §8.5 (follow-up generation), §8.6 + Appendix A.2 (red-flag rules + dual-layer rendering), §8.7 (safety blocker), §8.8 (audit cards), §8.9 + Appendix A.3 (doctor edit semantics with self-classification), §11.1 + §11.2 (analyze + review-claim endpoints), §13.4 (urgent-risk escalation), §17 (edge cases). It explicitly defers §8.10 (separate report generator), §10.6 (quality dashboard), §18 (audit log + RBAC), §19 Phase 5 (longitudinal patterns), and all multi-modal input — those live in [./post-pilot-roadmap.md](./post-pilot-roadmap.md).

## 2. Scope

### In scope

- Two endpoints (`POST /analyze`, `POST /review-claim`) and one SQLite table (`claims`).
- One Anthropic Claude call per `/analyze`, with prompt caching (claude-api skill).
- Rule-based safety blocker and red-flag detection. Per SPEC §8.6: rules first, LLM only to extract facts the rules consume.
- Doctor portal: transcript picker → input view with green/red dual-layer highlights → audit card list → claim edit modal with self-classification radio → accepted-claims summary.
- Eval harness: 10 synthetic transcripts with expected-claim labels, runs all seven success bars.

### Out of scope (cut list, see SPEC §A.4)

- Audit log persistence and RBAC (§18).
- Multi-modal input — voice STT, image OCR (§7.1, §8.2).
- Longitudinal pattern review (§19 Phase 5).
- Separate report generator (§8.10) — replaced by the filtered accepted-claims list in the portal.
- Quality dashboard for non-doctors (§10.6) — replaced by the eval harness output.
- "<20s/claim mean review time" success bar (§16.6) — moved to v2 Doctor Handoff (Appendix A of this plan).

### Non-negotiable rules (lifted from SPEC, enforced by tests)

- **No claim without evidence.** Drop or mark `riskLevel="needs-review"`.
- **Every medication-change phrase is blocked** with the safe replacement from `app/rules/blocked_advice.py:SAFE_REPLACEMENTS`. Regression-tested in wt/03.
- **Diagnosis inference downgrades to `eventType="patientConcern"`** with `safetyStatus="diagnosisNotConfirmed"`.
- **Urgent-risk path renders the §13.4 escalation message verbatim** (looked up from `app/rules/risk_messages.py`, never authored by the LLM).
- **Original AI claim preserved verbatim** when the doctor edits.
- **No PHI in `docs/eval/pilot-set.json`.** Synthetic transcripts only. CI fails the build if `scripts/scan-phi.py` flags anything.

## 3. Worktree Topology

| Worktree | Path | Branch | Owns |
|---|---|---|---|
| wt/01 | `.worktrees/wt-01-extraction-core/` | `clinical-proof-pilot/extraction-core` | Backend (`app/`) — extraction, safety, follow-up, endpoints, SQLite. Publishes the canonical claim-object schema. |
| wt/02 | `.worktrees/wt-02-doctor-ui/` | `clinical-proof-pilot/doctor-ui` | `services/web/` Next.js doctor portal. Consumes the schema. |
| wt/03 | `.worktrees/wt-03-eval-harness/` | `clinical-proof-pilot/eval-harness` | `tests/eval/` + `docs/eval/`. Owns the 10-transcript dataset and the eval-bar checks. |

`packages/shared/types.ts` is owned by wt/01 but read by wt/02 and wt/03.

Worktrees are created by `scripts/create-worktrees.sh` (see [./worktrees/](./worktrees/) for per-worktree dispatch briefs).

## 4. Phase 0 — Pre-flight (already done)

- [x] Spec vendored at `docs/clinical-proof-mode/SPEC.md` with Appendix A locking Q1/Q2/Q3.
- [x] Audience locked: internal-first (Option C).
- [x] Stack locked: Python 3.11 + FastAPI + SQLite, Anthropic Claude with prompt caching, Next.js + TS + shadcn/ui localhost.
- [x] Existing `app/` scaffold inventoried — the pilot fills only pilot-relevant stubs; non-pilot stubs are left untouched.
- [x] Persona for dataset realism (only): Indian GP, chronic gastro patients, AI-skeptical, time-pressed.

## 5. Phase 1 — Schema Gate (wt/01 only, sequential, day 1)

Everything else blocks on this. wt/01 must finish Phase 1 before wt/02 and wt/03 dispatch.

| Step | Owner | Output | Depends on |
|---|---|---|---|
| 1.1 | wt/01 | `packages/shared/types.ts` — TypeScript types for `ClinicalClaim`, `Evidence`, `RiskAssessment`, `SafetyBlock`, `FollowUpQuestion`, `DoctorAction`, `DoctorReviewStatus`, `ExtractionType` (`"direct" \| "interpretation"`), `DoctorEditOrigin` (`"minor_wording" \| "correction" \| "external_knowledge_override"`), `EventType`, `RiskLevel`, `SafetyStatus`. **Single source of truth.** | — |
| 1.2 | wt/01 | `app/models/claim.py` extended with `extractionType` (Appendix A.1) and `doctorEditOrigin` (Appendix A.3) fields. Pydantic field names match TS field names byte-for-byte. | 1.1 |
| 1.3 | wt/01 | `docs/eval/fixtures/sample-claims.json` — 3-5 hand-written sample claim objects covering: a `direct` extraction, an `interpretation` extraction, a `medicationAdviceBlocked` claim, an urgent-risk claim. Used by wt/02 to render and wt/03 to label against in Phase 2. | 1.1, 1.2 |
| 1.4 | wt/01 | `scripts/check-schema-drift.py` — fails CI if Pydantic field set diverges from TS field set. Lightweight: parse both, compare keys + enum values. | 1.1, 1.2 |
| 1.5 | wt/01 | Push branch with the four artifacts above. **Tag the commit `pilot/schema-v1`** and announce. | 1.1-1.4 |

**Gate to Phase 2:** wt/01 announces "schema published" by tagging `pilot/schema-v1`. Until then, wt/02 and wt/03 do not dispatch.

## 6. Phase 2 — Parallel Build (days 2-4)

After the Phase 1 tag lands, dispatch wt/01-implementation, wt/02, and wt/03 in parallel via `superpowers:dispatching-parallel-agents`.

### 6.1 wt/01 — Extraction Core (continues after Phase 1)

| Step | What | Spec § | Test gate |
|---|---|---|---|
| 2.1 | Implement `app/core/evidence.py` — `locate_evidence(claim_text, raw_text)` returns `(start, end)` or raises `EvidenceNotFound`. Reject any claim whose `evidenceText` is not an exact substring of `rawText`. | §8.2 | Unit: claim with bogus evidence raises; valid evidence returns correct offsets |
| 2.2 | Verify `app/rules/blocked_advice.py` — already scaffolded — covers all categories in SPEC §8.7. | §8.7 | Unit: every key in `BLOCKED_CATEGORIES` exists in `SAFE_REPLACEMENTS` |
| 2.3 | Implement `app/core/safety.py` — `screen_output(input, candidate_text, has_red_flags)` returns `SafetyBlock` or `None`. Rule-first med-change classifier; diagnosis-inference downgrade; emergency-reassurance-with-red-flag block. **100% coverage required.** | §8.7, §17.3, §17.4 | One regression test per category in `BLOCKED_CATEGORIES` |
| 2.4 | Implement `app/rules/red_flag_rules.py` — `match_red_flags(raw_text)` returns `list[(rule_key, start, end)]`. Cover all 8 vomiting + 5 medication red-flag rules from §8.6. | §8.6 | Unit: synthetic input for each rule produces the matching key |
| 2.5 | Implement `app/core/extraction.py` — single Anthropic Claude call (claude-api skill, prompt caching). System prompt is **cached**: extraction instructions + 3 few-shot examples (one direct, one interpretation, one patientConcern downgrade per §17.3). Variable input: the transcript. Output: structured JSON parsed into `ClinicalClaim[]` with the LLM self-classifying `extractionType`. **Validate** with a content-word-overlap heuristic against the evidence span; if mismatch, force `extractionType="interpretation"` regardless of LLM label. | §8.1, §A.1 | Unit + golden-file: 5 transcripts → expected event-type counts within tolerance |
| 2.6 | Implement `app/core/follow_up.py` — generate prioritized follow-up questions from `missingInfo[]`. | §8.5 | Unit: `missingInfo=["blood in vomit", "hydration"]` produces at least one high-priority question per item |
| 2.7 | Implement SQLite `claims` table + repository in `app/storage/repository.py`. Single table, no Alembic migrations. Schema in §6.1.7. | §9.2 | Unit: roundtrip insert/select preserves all fields including `originalClaimText` and `doctorEditOrigin` |
| 2.8 | Wire endpoints. `POST /analyze`: input → extraction → evidence check → safety screen → red-flag rules → claim list (red-flag-only spans tagged separately on the response) → persist → return. `POST /review-claim`: load claim → apply doctor action → preserve `originalClaimText` if edit → store `doctorEditOrigin` → persist → return. | §11.1, §11.2 | Integration: `pytest tests/api/`, full request roundtrip with SQLite |
| 2.9 | Verification loop green. | — | `make verify-wt-01` exits 0 |

#### 6.1.7 SQLite `claims` schema

```sql
CREATE TABLE claims (
  claim_id              TEXT PRIMARY KEY,
  patient_id            TEXT NOT NULL,
  input_id              TEXT NOT NULL,
  raw_text              TEXT NOT NULL,
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
  red_flag_only_spans_json TEXT,
  created_at            TEXT NOT NULL
);
```

`red_flag_only_spans_json` carries the red-layer payload for Appendix A.2 (rule matches that did NOT become claims). Stored on the claim row that opened the input session, or on a header row if no claims were emitted.

### 6.2 wt/02 — Doctor UI

| Step | What | Spec § | Test gate |
|---|---|---|---|
| 2.10 | Next.js + shadcn/ui scaffolding under `services/web/`. Localhost only. | §10.3 | `bun run typecheck` clean; dev server boots |
| 2.11 | TranscriptPickerPage — lists the 10 synthetic transcripts. | §10.3 | Vitest: renders 10 buttons; clicking calls `/analyze` with the chosen `inputId` |
| 2.12 | DualLayerInputView — renders `rawText` with green spans (claim evidence) and red spans (red-flag-rule matches without a corresponding urgent claim). Both layers use char offsets. | §A.2 | Snapshot test: known input renders both layers correctly with no overlap glitches |
| 2.13 | AuditCard — claim text, evidence (highlighted in the input view), confidence (% with bar), risk-level chip, missingInfo list, safetyStatus badge, **`extractionType` badge** (yellow for `interpretation`), `displayWarning` if present, Accept / Edit / Reject buttons. | §8.8 | Vitest: card renders all fields; Accept POSTs to `/review-claim` with `action="accepted"` |
| 2.14 | ClaimEditModal — original claim (read-only), evidence (read-only), editable corrected-claim textarea, **self-classification radio** (`minor_wording` / `correction` / `external_knowledge_override`), reason textarea, Save (disabled until radio selected) / Cancel. On save, POST to `/review-claim` with `action="edited"`, `correctedClaim`, `doctorEditOrigin`, `reason`. | §10.4, §A.3 | Vitest: Save disabled with no radio selection; strikethrough overlay renders on returned claim |
| 2.15 | AcceptedClaimsSummary — shown after the reviewer reviews all claims for a transcript. Lists only `accepted` and `edited` claims with their final text. Does NOT include `pending` or `rejected`. | §A.4 (in-pilot replacement for §8.10) | Vitest: only correct status values appear |
| 2.16 | Verification loop green. | — | `make verify-wt-02` exits 0 |

### 6.3 wt/03 — Eval Harness

| Step | What | Spec § | Test gate |
|---|---|---|---|
| 2.17 | Author `docs/eval/pilot-set.json` — 10 synthetic transcripts hitting all §17 edge cases + one urgent red flag (§13.4) + one curd-rice/Indian-context transcript matching the §6 example + four normal cases. **No PHI; synthetic only.** Persona for clinical realism only: Indian GP, chronic gastro, AI-skeptical, time-pressed. Full spec: [../eval/pilot-set-spec.md](../eval/pilot-set-spec.md). | §17, §13.4, §A.4 | `scripts/scan-phi.py` exits 0 |
| 2.18 | Author expected-claim labels at `docs/eval/pilot-set-labels.json` — for each transcript: `expected_event_types[]`, `expected_red_flag_rules[]`, `expected_safety_categories[]`, `expected_urgent_claim` (bool). | — | Format check: every transcript has at least one expected label |
| 2.19 | Implement eval harness `tests/eval/run_eval.py` — runs `/analyze` against all 10 transcripts, computes the 7 success bars, writes `artifacts/eval.json` + Markdown table. | §15 (subset) | Self-test: known fixture produces known JSON |
| 2.20 | Implement safety regression suite `tests/eval/test_safety_regression.py` — every category in `BLOCKED_CATEGORIES` has at least one transcript that should trigger it. **100% category coverage.** | §8.7 | Test fails if any category lacks a transcript |
| 2.21 | Implement missed-escalation check `tests/eval/test_missed_escalations.py` — for every red-flag-rule match in any transcript, assert the response contains an urgent claim that includes the matched span. | §A.2 | Passes only if zero unmatched red-flag rules |
| 2.22 | Verification loop green. | — | `make eval` exits 0 with all 7 bars green |

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

**Internal-audience addendum (qualitative bar, checked at demo time):** any internal reviewer can pick a random claim from the audit card and defend its evidence + safety status from the card alone, **without consulting SPEC.md**. If a reviewer has to open the SPEC, that is a finding.

For Phase 2 (before wt/02 integration), bars 1-3 are computed using a fixed-seed simulated-doctor-actions function (placeholder); bars 4-7 use only the LLM output and the rule output. The harness reports "simulated" vs "live" mode in its output header so we don't confuse the two during demos.

## 8. Phase 3 — Integration (day 4)

| Step | What | Owner |
|---|---|---|
| 3.1 | wt/02 swaps fixture rendering for live `/analyze` calls. | wt/02 |
| 3.2 | wt/03 swaps mock claims for live `/analyze` output; switches eval bars 1-3 to live mode (reads doctor actions from the SQLite DB written by `/review-claim`). | wt/03 |
| 3.3 | End-to-end smoke run: pick all 10 transcripts in the portal, accept/edit/reject each, eval harness reads from the SQLite DB, all 7 bars green. | all |
| 3.4 | Three PRs opened, each with §-coverage table in the description. Verification-loop green required to merge. | all |

## 9. Phase 4 — Internal Demo (day 5)

Full demo script in [../demo/walkthrough.md](../demo/walkthrough.md). 25 minutes total. Outline:

1. **(2 min)** What this is — localhost proof-of-trust pilot, audience is us, eval harness is the artifact.
2. **(4 min)** The urgent-risk transcript — show dual-layer rendering catching the missed escalation. **Central moment.**
3. **(3 min)** Diagnosis-inference transcript — show the safety blocker downgrading to `patientConcern`.
4. **(3 min)** Medication-change-request transcript — show the blocker, show the safe replacement.
5. **(5 min)** Open the eval harness output: all 7 bars, broken out by direct vs. interpretation cohort.
6. **(5 min)** Random-claim defense exercise (the qualitative ADD-for-v1 bar).
7. **(3 min)** What's next: read the v2 Doctor Handoff appendix, schedule doctor sourcing.

## 10. Per-Worktree Contract (binding)

Each worktree must deliver:

1. **PRD** — one paragraph in `docs/plan/worktrees/wt-NN.md` referencing the SPEC §-clauses it covers.
2. **TDD discipline** — tests written before implementation. RED → GREEN → REFACTOR. 80% line coverage floor (`pytest --cov` or `vitest --coverage`). **100% on the safety blocker** in wt/01 and on the safety regression suite in wt/03.
3. **Schema gate** (wt/01 only) — `packages/shared/types.ts` and `docs/eval/fixtures/sample-claims.json` committed and tagged `pilot/schema-v1` before downstream worktrees dispatch.
4. **Dataset gate** (wt/03 only) — `docs/eval/pilot-set.json` and `docs/eval/pilot-set-labels.json` committed; PHI-scanner CI green.
5. **Verification loop** green before review request.
6. **PR summary** lists §-clauses covered and links each to the test that exercises it.

## 11. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | LLM extraction quality on Indian-GP transcripts is poor (code-switching, regional food terms, time-pressed phrasing). | Med | High — kills the headline acceptance number | Cache the extraction system prompt; include 3 few-shot examples covering Indian-context patterns; run a smoke against the dataset *early* (Phase 2 step 2.5), not Phase 3. |
| R2 | Schema drift between Pydantic models and TypeScript types. | Med | High — invisible until integration day | Single source of truth in `packages/shared/types.ts`; CI gate on `scripts/check-schema-drift.py`. |
| R3 | Safety blocker false negative — a med-change phrase slips past. | Low | Critical — violates non-negotiable rule | 100% test coverage on safety blocker; one regression test per category in `BLOCKED_CATEGORIES`; rule-first design (LLM never authors final patient-facing text). |
| R4 | Dual-layer rendering misaligns: red-flag rule offsets and LLM evidence offsets use different anchoring. | Med | Med — visible inconsistency erodes the demo | Both layers use the same character-offset scheme into `rawText`; eval harness asserts span integrity (`evidence_text == raw_text[start:end]`); visual snapshot tests in wt/02. |
| R5 | The 10-transcript dataset isn't varied enough — every transcript looks the same and we don't actually exercise §17 edge cases. | Med | High — eval bars become meaningless | [../eval/pilot-set-spec.md](../eval/pilot-set-spec.md) enumerates required variety; wt/03 dataset commit reviewed against that spec; eval harness includes a variety-coverage assertion. |

## 12. Open Questions (with proposed defaults)

| # | Question | Proposed default | Confirm before |
|---|---|---|---|
| OQ1 | Confidence threshold for surfacing claims to the portal — show all, or filter? | Surface all. `interpretation` claims badged yellow; `confidence < 0.4` additionally badged "low confidence — needs review" per §17.5. No filtering; the reviewer sees everything the LLM said. | wt/02 dispatch |
| OQ2 | Transcript language. | English with embedded Hindi/regional food terms ("curd rice", "ghee", "rasam", "loose motions"). Full-Hindi transcripts cut for v1. | wt/03 dataset commit |
| OQ3 | Localhost SQLite persistence — file path, lifetime? | `.data/claims.db`, gitignored, fresh per `make demo`. Eval harness uses `.data/eval-<timestamp>.db`. | wt/01 storage implementation |
| OQ4 | Anthropic prompt cache strategy. | Cache the system prompt (extraction instructions + 3 few-shot examples). Variable input is the transcript only. 5-min TTL is fine for demo cadence. | wt/01 extraction implementation |
| OQ5 | Mocking strategy for wt/02 and wt/03 in Phase 2 — TS types only or also a fixture file? | Both. Types from `packages/shared/types.ts`, fixture at `docs/eval/fixtures/sample-claims.json` (delivered in Phase 1 step 1.3). | Phase 1 schema gate |
| OQ6 | LLM returns malformed JSON (missing required field). | Retry once with a "your previous response was malformed" appendix. If still bad, return `502` with the raw output for debugging. **Fail loudly, never silently.** | wt/01 extraction implementation |

---

## Appendix A — v2 Doctor Handoff

What changes when a real pilot doctor is sourced. **The portal does not change.** No internal-mode toggle, no debug overlays, no doctor-mode flag. Whoever clicks Accept/Edit/Reject is the doctor. This is the forward-compat guarantee.

| Today (internal-first v1) | v2 (named doctor) |
|---|---|
| Internal Pipeline Securities team clicks Accept/Edit/Reject. | Named doctor (e.g., "Dr X at clinic Y in Bangalore") clicks the same buttons. |
| Eval harness output (acceptance %, safety-block %, missed-escalation count) is interpreted by the team. | Doctor reviews the same harness output; team interprets the *delta* between internal and doctor results. |
| Success bar excludes "<20s/claim". | Add `<20s/claim mean review time` measured during a timed live session with the doctor. |
| Demo is an internal walkthrough. | Demo becomes a 30-minute paper-prototype call: 10 min context, 15 min the doctor reviews 3-5 claims live, 5 min debrief. |
| Dataset is synthetic with Indian-GP persona. | Dataset stays synthetic (no real patient data ever, even after sourcing) but persona may be replaced or expanded based on the doctor's actual specialty. |

**No code changes** for v2 except: (a) add the timing instrumentation hook in the portal (already a small change — track `claim_review_started_at` / `claim_review_finished_at` per claim and emit them on `/review-claim`), and (b) extend the eval harness with a bar #8 for `<20s/claim` once timing data exists.

---

*This plan is locked. Changes require updating Appendix A of the SPEC and re-running plan-eng-review.*
