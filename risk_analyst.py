"""
risk_analyst.py
===============
Agent 3 – Risk Analyst
Role  : Reads the raw text and extracted figures from shared memory,
        identifies risks, red flags, and negative signals.

Tools
-----
1. scan_risk_signals()       – keyword + pattern scan of the text for
                               risk categories (macro, legal, margin,
                               debt, competition, guidance-cut).
2. score_and_rank_risks()    – prioritises risks by severity and
                               attaches the verbatim source sentence.
"""

import re
from typing import Any, Dict, List, Tuple
from shared_memory import SharedMemory


# ══════════════════════════════════════════════════════════════
# Tool 1 – Scan text for risk signals
# ══════════════════════════════════════════════════════════════

# (category, severity 1-3, keyword_patterns)
_RISK_PATTERNS: List[Tuple[str, int, List[str]]] = [
    ("Macro / Market Risk", 2, [
        r"inflation", r"interest rate", r"recession", r"macro",
        r"currency", r"foreign exchange", r"FX headwind",
    ]),
    ("Revenue / Demand Risk", 3, [
        r"revenue decline", r"demand weakness", r"lower than expected",
        r"miss", r"shortfall", r"headwind", r"slowdown", r"churn",
    ]),
    ("Margin Compression", 3, [
        r"margin pressure", r"cost increase", r"rising cost",
        r"supply chain", r"input cost", r"operating expense",
    ]),
    ("Debt / Liquidity Risk", 2, [
        r"debt", r"leverage", r"credit facility", r"covenant",
        r"cash burn", r"refinanc", r"maturity",
    ]),
    ("Legal / Regulatory Risk", 2, [
        r"litigation", r"lawsuit", r"regulatory", r"investigation",
        r"fine", r"penalty", r"compliance", r"antitrust",
    ]),
    ("Guidance Cut / Warning", 3, [
        r"lower guidance", r"reduced outlook", r"cut.*forecast",
        r"below.*expectation", r"cautious", r"uncertainty",
        r"challenging environment", r"difficult",
    ]),
    ("Competition Risk", 1, [
        r"competition", r"competitive pressure", r"market share loss",
        r"pricing pressure", r"new entrant",
    ]),
    ("Operational Risk", 1, [
        r"operational challenge", r"execution risk", r"product delay",
        r"recall", r"outage", r"disruption",
    ]),
]


def scan_risk_signals(text: str) -> List[Dict[str, Any]]:
    """
    Tool 1 – Scan for risk signals across predefined categories.
    Returns a list of {category, severity, matched_text, source}.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    findings: List[Dict[str, Any]] = []

    for category, severity, patterns in _RISK_PATTERNS:
        for sent in sentences:
            for pat in patterns:
                if re.search(pat, sent, re.IGNORECASE):
                    # Avoid duplicating the same sentence for the same category
                    already = any(
                        f["category"] == category and f["source"] == sent.strip()
                        for f in findings
                    )
                    if not already:
                        findings.append({
                            "category": category,
                            "severity": severity,
                            "matched_pattern": pat,
                            "source": sent.strip()[:250],
                        })
                    break  # one hit per sentence per category

    return findings


# ══════════════════════════════════════════════════════════════
# Tool 2 – Score and rank risks, format report
# ══════════════════════════════════════════════════════════════

_SEVERITY_LABEL = {1: "LOW ⚪", 2: "MEDIUM 🟡", 3: "HIGH 🔴"}


def score_and_rank_risks(
    signals: List[Dict[str, Any]],
    figures: Dict[str, Any],
) -> str:
    """
    Tool 2 – Deduplicate, rank, and format a sourced risk section.
    Also cross-references extracted figures (e.g. if margin is low).
    """
    if not signals:
        return "## Risk Analysis\n\nNo material risk signals detected in the report.\n"

    # Sort by severity descending, then category name
    signals_sorted = sorted(signals, key=lambda x: (-x["severity"], x["category"]))

    # Deduplicate by category (keep highest severity per category)
    seen_cats: Dict[str, Dict] = {}
    for sig in signals_sorted:
        cat = sig["category"]
        if cat not in seen_cats:
            seen_cats[cat] = sig

    lines = ["## Risk Analysis", ""]

    # Financial red-flag cross-check
    red_flags = []
    gm = figures.get("gross_margin", {}).get("value")
    if gm is not None and gm < 30:
        red_flags.append(f"⚠ Gross margin ({gm:.1f}%) below 30% threshold – margin under pressure.")
    om = figures.get("operating_margin", {}).get("value")
    if om is not None and om < 10:
        red_flags.append(f"⚠ Operating margin ({om:.1f}%) below 10% – limited operating leverage.")
    yoy = figures.get("yoy_growth", {}).get("value")
    if yoy is not None and yoy < 0:
        red_flags.append(f"⚠ Revenue declined {abs(yoy):.1f}% YoY – contraction signal.")

    if red_flags:
        lines.append("**Financial Red Flags (from extracted figures):**")
        for rf in red_flags:
            lines.append(f"  - {rf}")
        lines.append("")

    # Risk table header
    lines.append("**Identified Risk Signals:**")
    lines.append("")

    for cat, sig in seen_cats.items():
        sev_label = _SEVERITY_LABEL.get(sig["severity"], "UNKNOWN")
        lines.append(f"### {cat}  [{sev_label}]")
        lines.append(f"> *Source:* \"{sig['source'][:200]}\"")
        lines.append("")

    # Summary rating
    high_count = sum(1 for s in seen_cats.values() if s["severity"] == 3)
    med_count  = sum(1 for s in seen_cats.values() if s["severity"] == 2)
    if high_count >= 2:
        overall = "🔴 HIGH RISK – Multiple high-severity signals detected."
    elif high_count == 1 or med_count >= 2:
        overall = "🟡 MODERATE RISK – Watch key risk areas."
    else:
        overall = "🟢 LOW RISK – No major red flags identified."

    lines.append(f"**Overall Risk Assessment:** {overall}")
    lines.append("")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Agent class
# ══════════════════════════════════════════════════════════════

class RiskAnalyst:
    NAME = "Risk Analyst"

    def __init__(self, memory: SharedMemory) -> None:
        self.memory = memory

    def run(self) -> str:
        mem = self.memory
        mem.record(self.NAME, "START", "Scanning raw text for risks")

        if not mem.raw_text:
            raise ValueError("SharedMemory.raw_text is empty.")

        # ── Tool 1 ──────────────────────────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "scan_risk_signals")
        signals = scan_risk_signals(mem.raw_text)
        mem.record(self.NAME, "TOOL_RESULT", f"{len(signals)} risk signals found")

        # ── Tool 2 ──────────────────────────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "score_and_rank_risks")
        report = score_and_rank_risks(signals, mem.current_figures)
        mem.record(self.NAME, "TOOL_RESULT", f"Risk report: {len(report)} chars")

        mem.risk_analysis = report
        mem.record(self.NAME, "WRITE_MEMORY", "risk_analysis")
        mem.record(self.NAME, "END", "Risk analysis complete")

        return report
