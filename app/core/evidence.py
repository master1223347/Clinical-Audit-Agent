"""§8.2 — Evidence Span Grounding.

Every claim must include the exact span from patient input that supports it.
A claim without a verifiable evidence span is dropped or marked needs-review.
"""


class EvidenceNotFound(Exception):
    pass


def locate_evidence(evidence_text: str, raw_text: str) -> tuple[int, int]:
    """Return (start, end) offsets of evidence_text in raw_text.

    Raises EvidenceNotFound if evidence_text is empty or not an exact substring.
    Offsets satisfy: raw_text[start:end] == evidence_text.
    """
    if not evidence_text:
        raise EvidenceNotFound("evidence_text must not be empty")
    idx = raw_text.find(evidence_text)
    if idx == -1:
        raise EvidenceNotFound(
            f"evidence_text {evidence_text!r} not found in raw_text"
        )
    return idx, idx + len(evidence_text)
