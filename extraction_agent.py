"""
extraction_agent.py
===================
Agent 1 – Extraction Agent
Role  : Pulls key financial figures (revenue, profit, margin, EPS,
        guidance) from the raw earnings-report text using two tools:
        1. parse_financial_figures()  – regex / heuristic KPI extractor
        2. retrieve_relevant_chunks() – RAG over the document chunks
        
Every figure stored in shared memory carries the source sentence it
came from so every downstream claim is traceable.
"""

import re
import json
from typing import Any, Dict, List, Tuple

from shared_memory import SharedMemory


# ══════════════════════════════════════════════════════════════
# Tool 1 – Structured extraction via regex heuristics
# ══════════════════════════════════════════════════════════════

# Pattern bank: (label, regex, unit_hint)
_PATTERNS: List[Tuple[str, str, str]] = [
    ("revenue",           r"(?:total\s+)?revenue[s]?\s+(?:of|was|were|:)?\s*\$?([\d,\.]+)\s*(billion|million|B|M)?", "USD"),
    ("net_income",        r"net\s+income\s+(?:of|was|were|:)?\s*\$?([\d,\.]+)\s*(billion|million|B|M)?", "USD"),
    ("gross_profit",      r"gross\s+profit\s+(?:of|was|were|:)?\s*\$?([\d,\.]+)\s*(billion|million|B|M)?", "USD"),
    ("operating_income",  r"operating\s+income\s+(?:of|was|were|:)?\s*\$?([\d,\.]+)\s*(billion|million|B|M)?", "USD"),
    ("eps",               r"(?:diluted\s+)?(?:EPS|earnings\s+per\s+share)\s+(?:of|was|were|:)?\s*\$?([\d,\.]+)", "USD"),
    ("gross_margin",      r"gross\s+(?:profit\s+)?margin\s+(?:of|was|were|:)?\s*([\d,\.]+)\s*%", "%"),
    ("operating_margin",  r"operating\s+margin\s+(?:of|was|were|:)?\s*([\d,\.]+)\s*%", "%"),
    ("net_margin",        r"net\s+(?:profit\s+)?margin\s+(?:of|was|were|:)?\s*([\d,\.]+)\s*%", "%"),
    ("yoy_growth",        r"(?:revenue\s+)?(?:grew|increased|growth)\s+(?:by\s+)?([\d,\.]+)\s*%\s*(?:year.over.year|YoY|y/y)?", "%"),
    ("guidance_revenue",  r"(?:guidance|outlook|expect[s]?|forecast[s]?)[^.]*?revenue[^.]*?\$([\d]+(?:\.[\d]+)?)\s*(billion|million|B|M)?", "USD"),
    ("guidance_eps",      r"(?:guidance|outlook|expect[s]?|forecast[s]?)[^.]*?(?:EPS|earnings\s+per\s+share)[^.]*?\$([\d]+(?:\.[\d]+)?)", "USD"),
    ("free_cash_flow",    r"free\s+cash\s+flow\s+(?:of|was|were|:)?\s*\$?([\d,\.]+)\s*(billion|million|B|M)?", "USD"),
]


def _normalise_amount(raw_value: str, unit: str) -> float:
    """Convert '12.3 billion' → 12_300 (millions for uniformity)."""
    v = float(raw_value.replace(",", ""))
    unit_lower = (unit or "").lower()
    if unit_lower in ("billion", "b"):
        v *= 1_000  # → millions
    return round(v, 2)


def parse_financial_figures(text: str) -> Dict[str, Any]:
    """
    Tool 1 – Regex-based structured extraction.
    Returns a dict of {metric: {value, unit, source_sentence}}.
    """
    figures: Dict[str, Any] = {}
    sentences = re.split(r'(?<=[.!?])\s+', text)

    for label, pattern, unit_hint in _PATTERNS:
        for sent in sentences:
            m = re.search(pattern, sent, re.IGNORECASE)
            if m:
                raw_val = m.group(1)
                unit_grp = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
                try:
                    if unit_hint == "%":
                        value = float(raw_val.replace(",", ""))
                        unit = "%"
                    elif label in ("eps", "guidance_eps"):
                        value = float(raw_val.replace(",", ""))
                        unit = "USD"
                    else:
                        value = _normalise_amount(raw_val, unit_grp or unit_hint)
                        unit = "M USD"
                    if label not in figures:          # first match wins
                        figures[label] = {
                            "value": value,
                            "unit": unit,
                            "source": sent.strip()[:200],
                        }
                except ValueError:
                    continue
    return figures


# ══════════════════════════════════════════════════════════════
# Tool 2 – RAG: chunk retrieval for supplemental figures
# ══════════════════════════════════════════════════════════════

def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> List[str]:
    """Split text into overlapping windows."""
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i: i + chunk_size]))
        i += chunk_size - overlap
    return chunks


_FINANCIAL_KEYWORDS = [
    "revenue", "profit", "margin", "eps", "earnings", "income",
    "guidance", "outlook", "growth", "cash flow", "operating",
    "quarter", "annual", "forecast", "risk", "debt", "expenses",
]


def retrieve_relevant_chunks(text: str, top_k: int = 8) -> List[Dict[str, Any]]:
    """
    Tool 2 – Lightweight keyword-scored RAG (no external vector DB needed).
    Returns the top_k most finance-relevant chunks with their scores.
    """
    chunks = _chunk_text(text)
    scored: List[Tuple[float, str]] = []

    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(chunk_lower.count(kw) for kw in _FINANCIAL_KEYWORDS)
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"score": s, "text": c[:500]}
        for s, c in scored[:top_k]
    ]


# ══════════════════════════════════════════════════════════════
# Agent class
# ══════════════════════════════════════════════════════════════

class ExtractionAgent:
    NAME = "Extraction Agent"

    def __init__(self, memory: SharedMemory) -> None:
        self.memory = memory

    def run(self) -> Dict[str, Any]:
        """
        Orchestrate the two tools over the raw text held in shared memory.
        Results are written back to shared memory for downstream agents.
        """
        mem = self.memory
        mem.record(self.NAME, "START", "Beginning structured extraction + RAG")

        if not mem.raw_text:
            raise ValueError("SharedMemory.raw_text is empty – load a report first.")

        # ── Tool 1: regex extraction ──────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "parse_financial_figures")
        figures = parse_financial_figures(mem.raw_text)
        mem.record(self.NAME, "TOOL_RESULT", f"{len(figures)} figures extracted")

        # ── Tool 2: RAG – pull supplemental chunks ────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "retrieve_relevant_chunks")
        chunks = retrieve_relevant_chunks(mem.raw_text, top_k=8)
        mem.record(self.NAME, "TOOL_RESULT", f"{len(chunks)} relevant chunks retrieved")

        # Supplement: scan top chunks for any figures missed by regexes
        for chunk_obj in chunks:
            extra = parse_financial_figures(chunk_obj["text"])
            for k, v in extra.items():
                if k not in figures:
                    figures[k] = v
                    figures[k]["source"] += " [via RAG]"

        # Write to shared blackboard
        mem.current_figures = figures
        mem.record(self.NAME, "WRITE_MEMORY", list(figures.keys()))
        mem.record(self.NAME, "END", f"Extraction complete – {len(figures)} KPIs")

        return figures
