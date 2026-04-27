"""§13 — patient-facing messages by risk level."""

from app.models.enums import RiskLevel

PATIENT_MESSAGES: dict[RiskLevel, str] = {
    RiskLevel.LOW: (
        "Logged. Continue tracking and answer follow up questions if symptoms change."
    ),
    RiskLevel.MEDIUM: (
        "Logged. Because this involves symptoms that may need follow up, "
        "Dr Tracker will include this in your doctor report. "
        "Contact your doctor if symptoms worsen."
    ),
    RiskLevel.HIGH: (
        "This may need prompt medical attention. "
        "Please contact a doctor or local emergency service if symptoms are severe or worsening."
    ),
    RiskLevel.URGENT: (
        "This may be urgent. "
        "Please seek emergency medical help now if you are experiencing severe symptoms."
    ),
}
