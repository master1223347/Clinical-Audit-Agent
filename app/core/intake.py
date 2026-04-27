"""§7.1 — Intake & cleaning.

Convert any input modality (text/voice/image/conversation) into a normalized
`PatientInput` whose `rawText` is what downstream extraction will scan. The
original modality is preserved so evidence (§8.2) can point back to the
transcript or image region.
"""

from typing import Protocol

from app.models import PatientInput
from app.models.enums import InputType


class Transcriber(Protocol):
    def transcribe(self, audio_bytes: bytes) -> str: ...


class ImageReader(Protocol):
    def extract_text(self, image_bytes: bytes) -> str: ...


def normalize_input(
    raw_input: PatientInput,
    transcriber: Transcriber | None = None,
    image_reader: ImageReader | None = None,
) -> PatientInput:
    """Returns a PatientInput with `rawText` populated for any modality."""
    raise NotImplementedError


def detect_modality(payload: bytes | str) -> InputType:
    raise NotImplementedError
