# Post-Pilot Roadmap

What was cut from the pilot per SPEC §A.4, when it comes back, and the gating signal. This is **not** a committed schedule — it's a sequence with explicit triggers so we don't re-litigate scope every time the pilot demo gets praise.

## Cut from pilot

| # | Capability | SPEC § | Replaced in pilot by | Restoration trigger |
|---|---|---|---|---|
| 1 | Audit log persistence | §18.7 | Nothing (pilot doesn't persist who-saw-what) | **First real-doctor session.** Required before any non-synthetic input touches the system. |
| 2 | RBAC (role-based access control) | §18 | Nothing — single-user localhost | **Second doctor onboarded** OR clinic-team stakeholder named. |
| 3 | Multi-modal input — voice STT | §7.1, §8.2 | Text-only input | **First doctor session where the doctor or patient asks for voice notes.** Voice STT first; image OCR after. |
| 4 | Multi-modal input — image OCR | §7.1, §8.2 | Text-only input | After voice STT ships and a doctor asks to upload a lab report. |
| 5 | Longitudinal pattern review | §19 Phase 5 | Nothing | **3+ months of accepted claims accumulated** AND a doctor asks "show me the pattern across visits." |
| 6 | Separate report generator (exportable PDF) | §8.10 | Filtered accepted-claims list rendered in portal | **Stakeholder asks for an exportable artifact** (PDF, email, EHR push). |
| 7 | Quality dashboard for non-doctors | §10.6 | Eval harness output | **Clinic-team stakeholder named as a real audience.** Until then, the eval harness JSON is enough. |
| 8 | "<20s/claim mean review time" success bar | §16.6 | Dropped from internal-first v1 | **Real doctor sourced.** See pilot.md Appendix A. |

## Sequence (rough order, not committed)

Each step requires a fresh plan-eng-review and a new audience decision. Don't compress these — every one of them is a chance for the system to break a non-negotiable safety rule, and the rules are the whole product.

1. **v2 — Doctor sourcing + first real session.** Run pilot.md's Appendix A handoff. Add the `<20s/claim` bar. Capture qualitative feedback. **Trigger:** named pilot doctor.
2. **v3 — Audit log + RBAC.** SPEC §18. Required before non-synthetic input. **Trigger:** completion of v2 *and* commitment to onboard a real patient.
3. **v4 — Voice STT input.** SPEC §7.1, §8.2. **Trigger:** doctor or patient asks for voice notes.
4. **v5 — Exportable report generator.** SPEC §8.10. **Trigger:** stakeholder asks for PDF/EHR push.
5. **v6 — Image OCR input.** SPEC §7.1, §8.2. **Trigger:** doctor asks to upload lab reports.
6. **v7 — Quality dashboard.** SPEC §10.6. **Trigger:** clinic-team stakeholder named.
7. **v8 — Longitudinal pattern review.** SPEC §19 Phase 5. **Trigger:** 3+ months of claims + doctor request.

## What is NOT in this roadmap (and won't be)

- **Diagnosis features.** SPEC §5 prohibits.
- **Direct medication advice.** SPEC §5, §8.7.
- **Replacing clinical judgment.** SPEC §5.
- **Auto-generated patient messages without rule-based templating.** The LLM never authors final patient-facing text in any future version. The safety blocker authors all replacement language; the §13.4 escalation message is looked up, not generated.

These are non-goals **forever**, not "later." A future PR that lifts any of these requires a SPEC update first, signed off by the team that owns clinical safety.

## How to add to this roadmap

1. Identify the trigger that justifies adding the capability.
2. Confirm it does not violate the non-goals above.
3. PR an addition to this file with the trigger and the SPEC § that grounds it.
4. Plan-eng-review the addition before any code is written.
