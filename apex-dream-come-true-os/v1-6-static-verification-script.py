"""
APEX Dream Come True OS — v1.6 Static Verification Script

Truth boundary:
- Static verification only.
- Does not prove deployment readiness, legal compliance, privacy compliance,
  accessibility compliance, child safety, product quality, market validation,
  or viral adoption.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent

REQUIRED_FILES = [
    "README.md",
    "STATUS.md",
    "summary.md",
    "submission-checklist.md",
    "prototype-index.html",
    "static-verification.md",
    "v1-5-full-artifact-import-strategy.md",
    "v1-5-static-check-plan.md",
    "v1-5-private-beta-review-checklist.md",
]

REQUIRED_TERMS = {
    "STATUS.md": ["NOT DEPLOYED", "NOT VALIDATED", "External outreach sending: DISABLED"],
    "prototype-index.html": ["NO-SEND", "NOT VALIDATED", "No external sending"],
}

FORBIDDEN_PATTERNS = [
    r"API_KEY\s*=",
    r"SECRET\s*=",
    r"BEGIN PRIVATE KEY",
    r"password\s*=",
    r"mailto:",
    r"fetch\(\s*['\"]https?://",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).exists()]
    if missing:
        fail(f"Missing required files: {missing}")

    for rel_path, terms in REQUIRED_TERMS.items():
        text = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        for term in terms:
            if term not in text:
                fail(f"Missing required term {term!r} in {rel_path}")

    scanned_files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".html", ".py", ".json", ".txt", ".yml", ".yaml"}]
    for path in scanned_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                fail(f"Forbidden pattern {pattern!r} found in {path.relative_to(ROOT)}")

    print("PASS: v1.6 static verification passed.")
    print("Boundary: static verification is not legal/privacy/accessibility/market validation.")


if __name__ == "__main__":
    main()
