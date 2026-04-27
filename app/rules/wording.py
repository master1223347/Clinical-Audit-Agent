"""§12 — Rules for Clinical Wording."""

ALLOWED_PHRASES: list[str] = [
    "patient reported",
    "patient described",
    "patient may have",
    "cause unknown",
    "doctor review recommended",
    "pattern observed, not diagnosis",
]

DISALLOWED_PHRASES: list[str] = [
    "patient has food poisoning",
    "patient should stop medication",
    "this is definitely caused by",
    "this is not serious",
    "no need to see a doctor",
    "increase the dose",
    "decrease the dose",
    "taper the medication",
]

UNCERTAIN_FALLBACKS: list[str] = [
    "Cause unknown.",
    "Needs doctor review.",
]
