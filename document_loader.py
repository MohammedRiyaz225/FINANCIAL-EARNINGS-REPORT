"""
document_loader.py
==================
Utility module – NOT an agent.
Loads earnings report text from various sources:
  - Plain .txt files
  - PDF files (via pdfplumber)
  - Raw string input (for testing)

Also provides helpers for injecting synthetic previous-quarter data.
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional


def load_from_text(text: str) -> str:
    """Return text as-is (for testing or pre-extracted text)."""
    return text.strip()


def load_from_txt_file(path: str) -> str:
    """Load plain text from a .txt file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return p.read_text(encoding="utf-8").strip()


def load_from_pdf(path: str) -> str:
    """
    Load text from a PDF earnings report using pdfplumber.
    Falls back gracefully with a clear error message if pdfplumber is missing.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber is required to load PDFs. "
            "Run: pip install pdfplumber"
        )
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages_text = []
    with pdfplumber.open(str(p)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t)
    return "\n\n".join(pages_text).strip()


def auto_load(source: str) -> str:
    """
    Convenience loader: detect source type by extension or treat as text.
    source can be: a file path (.txt or .pdf) or a raw string.
    """
    if source.strip().endswith(".pdf"):
        return load_from_pdf(source)
    p = Path(source)
    if p.exists() and p.suffix.lower() == ".txt":
        return load_from_txt_file(source)
    # Assume raw text was passed directly
    return load_from_text(source)


# ─────────────────────────────────────────────────────────────
# Synthetic previous-quarter data (for demo / testing)
# ─────────────────────────────────────────────────────────────

def make_previous_quarter_figures(current_figures: Dict[str, Any], delta_pct: float = -5.0) -> Dict[str, Any]:
    """
    Create synthetic previous-quarter figures by scaling the current
    figures by (1 + delta_pct/100).  Used for demo / testing when
    no real prior-quarter document is available.
    """
    previous: Dict[str, Any] = {}
    for key, obj in current_figures.items():
        if isinstance(obj, dict) and "value" in obj:
            old_val = obj["value"] * (1 + delta_pct / 100)
            previous[key] = {
                "value": round(old_val, 2),
                "unit":  obj.get("unit", ""),
                "source": f"[Synthetic prior-quarter estimate, scaled {delta_pct:+.0f}%]",
            }
    return previous
