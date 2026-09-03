from __future__ import annotations

from typing import Any

from .component_registry import ComponentRegistry
from .risk_engine import classify_risk
from .specification import compile_specification

CAPABILITY_HINTS = {
    "auth-session": ["login", "log in", "sign in", "signup", "sign up", "auth", "oauth", "account"],
    "offline-outbox": ["offline", "outbox", "sync later", "no internet"],
    "push-notifications": ["push", "notification", "fcm", "apns", "reminder"],
    "payments-boundary": ["payment", "subscription", "billing", "stripe", "iap", "purchase"],
    "network-dio": ["api", "backend", "http", "server", "rest"],
    "observability": ["crash", "observability", "analytics", "logging", "monitoring"],
    "adaptive-shell": ["responsive", "adaptive", "navigation", "screen", "ui"],
    "google-auth": ["google login", "google sign in", "google oauth"],
    "apple-auth": ["apple login", "sign in with apple", "apple sign in"],
    "biometric-gate": ["biometric", "face id", "fingerprint"],
    "deep-links": ["deep link", "app link", "universal link"],
    "local-cache": ["cache", "local cache"],
    "feature-flags": ["feature flag", "kill switch", "remote config"],
    "accessibility-baseline": ["accessibility", "screen reader", "large text"],
    "websocket": ["websocket", "socket", "realtime", "real-time"],
    "file-upload": ["upload", "file upload"],
    "camera": ["camera", "scan qr", "barcode"],
    "location": ["location", "gps", "geofence"],
    "in-app-purchase": ["in app purchase", "iap", "storekit", "play billing"],
    "secure-logging": ["logging", "structured log", "audit log"],
    "update-gate": ["force update", "minimum version", "min supported version"],
}


def compile_requirements(brief: str) -> dict[str, Any]:
    text = " ".join(brief.lower().split())
    requested = []
    for component, hints in CAPABILITY_HINTS.items():
        if any(h in text for h in hints):
            requested.append(component)
    if not requested:
        requested = ["adaptive-shell"]

    registry = ComponentRegistry()
    plan = registry.resolve(requested)
    acceptance = []
    risks = []
    for component in plan["components"]:
        risks.append(component.get("risk", "medium"))
        for item in component.get("acceptance", []):
            acceptance.append({"component": component["id"], "criterion": item})

    questions = []
    if "android" not in text and "ios" not in text and "web" not in text and "desktop" not in text:
        questions.append("Which target platforms are in scope? Default can remain Android + iOS.")
    if any(c in plan["ordered_components"] for c in ["auth-session", "payments-boundary", "network-dio"]) and not any(x in text for x in ["backend", "api", "firebase", "supabase", "server"]):
        questions.append("What backend/API authority should this client integrate with?")

    risk = classify_risk(brief, component_risks=risks).to_dict()
    specification = compile_specification(brief, component_ids=plan["ordered_components"])
    return {
        "brief": brief,
        "inferred_components": plan["ordered_components"],
        "capabilities": plan["capabilities"],
        "acceptance_criteria": acceptance,
        "risk": risk,
        "blocking_questions": questions,
        "executable_specification": specification,
        "rule": "Inferred items are a starting hypothesis. User intent and PROJECT_RULES.md override them. Do not silently add capabilities not needed by the brief.",
    }
