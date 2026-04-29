"""Duplicate-claim deduplication — pilot.md §2 (post-review M2a).

For each (eventType, evidence_span_overlap > 50%) cluster, keep the
highest-confidence claim and drop the others. Runs BEFORE safety screen
and persistence; dropped claims are not written to the DB.
"""

import logging

from app.models.claim import ClinicalClaim

_log = logging.getLogger(__name__)


def _span_overlap_ratio(start1: int, end1: int, start2: int, end2: int) -> float:
    """Return the overlap as a fraction of the shorter span's length."""
    overlap = max(0, min(end1, end2) - max(start1, start2))
    len1 = max(0, end1 - start1)
    len2 = max(0, end2 - start2)
    shorter = min(len1, len2)
    if shorter == 0:
        return 0.0
    return overlap / shorter


def dedup_claims(claims: list[ClinicalClaim]) -> list[ClinicalClaim]:
    """Collapse (eventType, evidence_span_overlap > 50%) clusters.

    Within each cluster, keep the claim with the highest confidence.
    All other cluster members are dropped (not persisted, not counted).
    Order of survivors is preserved relative to the input list.
    """
    if not claims:
        return []

    merged: list[int] = []  # indices of claims absorbed into a cluster
    survivors: list[ClinicalClaim] = []

    for i, claim in enumerate(claims):
        if i in merged:
            continue
        cluster = [i]
        for j in range(i + 1, len(claims)):
            if j in merged:
                continue
            other = claims[j]
            if other.eventType != claim.eventType:
                continue
            c_start = claim.evidence.startChar or 0
            c_end = claim.evidence.endChar or 0
            o_start = other.evidence.startChar or 0
            o_end = other.evidence.endChar or 0
            ratio = _span_overlap_ratio(c_start, c_end, o_start, o_end)
            if ratio > 0.5:
                cluster.append(j)
                merged.append(j)

        best = max(cluster, key=lambda idx: claims[idx].confidence)
        survivors.append(claims[best])

        dropped = len(cluster) - 1
        if dropped > 0:
            _log.debug(
                "dedup: dropped %d claim(s) from cluster (eventType=%s)",
                dropped,
                claim.eventType,
            )

    return survivors
