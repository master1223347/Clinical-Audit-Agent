# Internal Demo Walkthrough

**Audience:** internal Pipeline Securities team + advisors
**Length:** 25 minutes (20 demo + 5 Q&A)
**Setup time:** 2 minutes
**Plan reference:** [../plan/pilot.md](../plan/pilot.md), §9

## Pre-demo checklist (do this 30 minutes before)

- [ ] `make verify-wt-01`, `make verify-wt-02`, `make eval` all exit 0 — green build.
- [ ] `make demo` starts the API at `localhost:8000` and the portal at `localhost:3000`.
- [ ] `artifacts/eval.json` exists and shows all 7 bars green. Open the Markdown summary in a side window.
- [ ] Browser windows: portal (left half), eval-harness Markdown table (right half), SPEC.md open in a third tab (closed by default — only opened if someone explicitly asks).
- [ ] Mute notifications. Close Slack.

## Walkthrough

### Beat 1 — What this is (2 min)

> This is the Clinical Proof Mode pilot. It's a localhost-only proof-of-trust artifact, not a shippable feature. The audience for this demo is us. The eval harness output you'll see at the end is the central artifact. The portal is the visual that explains *why* the harness numbers mean what they mean.
>
> The pilot covers extraction, evidence grounding, the safety blocker, red-flag detection, and the doctor review flow — the components that make the AI auditable. It explicitly does not include audit logging, RBAC, multi-modal input, longitudinal patterns, or a separate report generator. Those are on the post-pilot roadmap and required before any real patient data goes near this system.

### Beat 2 — The urgent-risk transcript (4 min) — **central moment**

Pick the urgent red-flag transcript (e.g., `t06`).

1. Click the transcript in the picker. The input view loads.
2. **Point at the green spans:** "These are the AI's claims grounded in evidence. The LLM was forced to cite the exact words it extracted from."
3. **Point at the red spans:** "These are red-flag rule matches that the LLM did NOT turn into urgent claims. This is the dual-layer rendering from Appendix A.2 of the SPEC. Right now you see [N] red highlights without a matching green urgent claim — that's the missed-escalation count, and it's what the eval harness's bar #7 measures."
4. Walk one audit card. Show the evidence link, confidence, risk-level chip, missing info, safety status, and the `extractionType` badge.
5. Click Accept on a direct claim. Click Edit on an interpretation claim — open the modal, change a word, **show the self-classification radio**, pick `minor_wording`, save. Show the strikethrough overlay in the audit card after save.
6. Click Reject on a low-confidence claim that the LLM should not have surfaced.

**Key line to land:** "The trust isn't 'the AI got it right.' The trust is 'we can see exactly what the AI did, and we can correct it before it goes anywhere.'"

### Beat 3 — The diagnosis-inference transcript (3 min)

Pick a transcript where the patient self-diagnoses (e.g., "I think I have food poisoning").

1. Show the audit card: the AI did NOT emit `eventType="possibleFoodTrigger"` upgraded to a fact. It emitted `eventType="patientConcern"` with `safetyStatus="diagnosisNotConfirmed"`.
2. **Point at the safe-replacement text:** "This is from the safety blocker. The LLM didn't author this sentence — the rule did. That's why we can guarantee the wording across every diagnosis-inference case."

**Key line to land:** "The non-negotiable rules in the SPEC become non-negotiable in the code because the LLM never authors final patient-facing text in those categories."

### Beat 4 — The medication-change transcript (3 min)

Pick a transcript where the patient asks "should I stop my antibiotic?"

1. Show that the response includes the med-change safe replacement from `app/rules/blocked_advice.py`.
2. Switch to the eval harness side: bar #5 shows 100% of medication-change phrases blocked.
3. **Point at the safety regression suite output:** every category in `BLOCKED_CATEGORIES` has at least one passing test in `tests/eval/test_safety_regression.py`.

**Key line to land:** "If a future SPEC change adds a new blocked category, the safety regression suite will fail the build until a regression test is added. The 100% bar is structural, not aspirational."

### Beat 5 — The eval harness output (5 min)

Switch focus to the Markdown table on the right half of the screen. Walk all 7 bars.

| Bar | What it means |
|---|---|
| 1 | Direct extractions are reliable — ≥80% accepted or lightly edited |
| 2 | Interpretation cohort tracked separately so it doesn't game bar 1 — ≥60% accepted |
| 3 | The system isn't surfacing junk — ≤10% rejected |
| 4 | No claim without evidence — 100% |
| 5 | Non-negotiable rule enforced — 100% med-change blocks |
| 6 | Every urgent risk gets the escalation message — zero silent |
| 7 | Dual-layer rendering covers what the LLM misses — zero missed escalations |

For each bar, briefly state how it's computed and what would make it fail.

### Beat 6 — Random claim defense (5 min) — **the qualitative ADD-for-v1 bar**

Hand the laptop to one attendee. They pick a random claim from the audit card view of any transcript.

> "Defend the evidence and safety status of this claim from the card alone. Don't open the SPEC."

If they can do it: that's the qualitative success bar passing. If they have to consult the SPEC: that's a finding — note it and continue. Repeat with 2-3 attendees.

This is the closest the pilot gets to measuring trust without a real doctor in the room. **Note any claims that were hard to defend** — they go in the post-demo retro and shape what changes for the v2 doctor session.

### Beat 7 — What's next (3 min)

> The v2 doctor handoff appendix in pilot.md lists exactly what changes when we source a real doctor: who clicks the buttons (the doctor instead of us), who interprets the eval-harness numbers (still us, but with the doctor's qualitative input), and the addition of a `<20s/claim` mean review-time bar measured live.
>
> The portal does not change. There's no internal-mode toggle, no debug overlay, no doctor-mode flag. That's the forward-compat guarantee. Whoever clicks Accept is the doctor.
>
> Next concrete step: source a pilot doctor. The post-pilot roadmap (`docs/plan/post-pilot-roadmap.md`) lists what comes back into scope after that — audit log persistence, RBAC, multi-modal input — in the order that real-doctor sessions force us to add them.

## Q&A buffer (5 min)

Likely questions and ready answers:

- **"What about HIPAA / DPDP?"** Out of pilot scope. No PHI in the dataset, no real patient data anywhere. Compliance work (audit log, RBAC, encryption at rest) is on the post-pilot roadmap, gated on the first real-doctor session.
- **"Why prompt caching?"** Cost and latency. The system prompt with few-shot examples is large; caching it pulls per-call latency down enough that demo re-runs feel snappy.
- **"What if the LLM returns malformed JSON?"** wt/01 retries once with a "your previous response was malformed" appendix; if still bad, returns 502 with the raw output for debugging. Fail loudly, never silently.
- **"What's the failure mode if the schema drifts?"** CI catches it (`scripts/check-schema-drift.py`). Single source of truth at `packages/shared/types.ts`.
- **"How do you keep the eval harness honest as the LLM improves?"** The 7 bars are structural (evidence coverage, safety blocks, missed escalations) — they don't reward LLM "cleverness," they enforce non-negotiables. The acceptance bars (1, 2, 3) are the only ones the LLM could game by being more conservative; the interpretation cohort separation (bar 2) is specifically designed to prevent that gaming by tracking the suppressed cohort separately.
- **"Why internal-first instead of recruiting a doctor?"** Recruiting a pilot doctor is a multi-week effort and the demo can't wait. The forward-compat design means no work is wasted: the same portal, the same harness, the same dataset all carry into v2 without modification.

## Demo failure modes (and how to recover)

- **Eval harness shows red.** Stop the demo, explain what failed, treat it as the finding. Better than performing a green demo on a broken system.
- **Portal won't render.** Switch to fixture mode (`?fixtures=1`) and explain we're showing the UI against canned data. If even fixtures fail, abandon the visual and walk the eval table only.
- **Someone asks for a feature in the cut list.** Refer to `docs/plan/post-pilot-roadmap.md` and the §A.4 cut list. The cut is the point.
- **Random-claim defense fails repeatedly.** Note it as the most important finding of the session. The qualitative bar exists specifically to surface this. Don't paper over it.

## Post-demo (5 min, off the clock)

- Capture findings in a 1-page retro: which beats landed, which didn't, which random-claim defenses failed, which questions caught us flat-footed.
- Update `docs/plan/pilot.md` §12 (Open Questions) with anything new that surfaced.
- Schedule the v2 doctor sourcing kickoff before anyone leaves the room.
