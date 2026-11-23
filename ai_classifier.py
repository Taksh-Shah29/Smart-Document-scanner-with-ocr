"""
Scanify Pro — offline document classifier.

This lightweight classifier uses weighted OCR text signals and document-layout
hints. It is intentionally offline and requires no API key or model download.
The confidence is a heuristic score, not a calibrated probability.
"""
import re
from datetime import datetime

CATEGORY_RULES = {
    "Invoice": {
        "strong": ["invoice", "tax invoice", "invoice no", "invoice number", "bill to", "ship to", "subtotal", "grand total", "gstin", "hsn"],
        "weak": ["quantity", "unit price", "amount", "cgst", "sgst", "igst", "purchase order"],
    },
    "Receipt": {
        "strong": ["receipt", "payment received", "transaction successful", "thank you for your purchase", "cash memo", "pos transaction"],
        "weak": ["paid", "change", "cash", "card", "upi", "total", "date"],
    },
    "Bank Statement": {
        "strong": ["account statement", "bank statement", "opening balance", "closing balance", "available balance", "account number"],
        "weak": ["debit", "credit", "transaction date", "withdrawal", "deposit", "ifsc", "branch"],
    },
    "Identity Document": {
        "strong": ["date of birth", "government of india", "unique identification", "passport", "driving licence", "driving license", "identity card", "aadhaar"],
        "weak": ["male", "female", "nationality", "signature", "address", "id no", "valid until"],
    },
    "Academic Document": {
        "strong": ["mark sheet", "marksheet", "statement of marks", "transcript", "certificate", "university", "semester", "examination"],
        "weak": ["student", "enrollment", "enrolment", "course", "grade", "cgpa", "roll no", "roll number"],
    },
    "Letter": {
        "strong": ["dear sir", "dear madam", "to whomsoever it may concern", "subject:", "yours faithfully", "yours sincerely"],
        "weak": ["regards", "respected sir", "respected madam", "reference no", "thank you"],
    },
    "Form": {
        "strong": ["application form", "registration form", "please fill", "form no", "personal details"],
        "weak": ["first name", "last name", "date of birth", "checkbox", "yes/no", "signature"],
    },
}

def _normalise(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

def classify_document(text):
    """Return best category, heuristic confidence, and a short explanation."""
    content = _normalise(text)
    if not content:
        return {"label": "Unknown", "confidence": 0, "reason": "No readable OCR text was provided."}

    scores = {}
    matched = {}
    for category, rules in CATEGORY_RULES.items():
        strong_hits = [term for term in rules["strong"] if term in content]
        weak_hits = [term for term in rules["weak"] if term in content]
        score = len(strong_hits) * 3 + len(weak_hits)
        scores[category] = score
        matched[category] = strong_hits + weak_hits

    best = max(scores, key=scores.get)
    ranked = sorted(scores.values(), reverse=True)
    top = scores[best]
    second = ranked[1] if len(ranked) > 1 else 0

    if top == 0:
        return {"label": "General Document", "confidence": 25, "reason": "No category-specific terms found."}

    # Conservative heuristic: score strength and separation from second-best category.
    confidence = min(94, 38 + top * 7 + max(0, top - second) * 4)
    if top == second:
        confidence = min(confidence, 55)
    terms = ", ".join(matched[best][:4])
    return {
        "label": best,
        "confidence": int(confidence),
        "reason": f"Matched document terms: {terms}.",
    }

def make_suggested_filename(category, now=None):
    """Create a filesystem-safe, timestamped suggested filename."""
    safe = re.sub(r"[^A-Za-z0-9]+", "_", category or "Document").strip("_")
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{safe}_{stamp}"
