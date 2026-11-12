"""
editor_manager.py
=================
Agent 6 – Editor Manager  (Fan-in / Orchestrator)
Role  : Receives the three analyst sections from shared memory (fan-in),
        detects any disagreements between them, and produces a single,
        coherent one-page analyst note with clear Revenue / Risk / Outlook
        structure. Also incorporates the Comparison Agent report.

Tools
-----
1. detect_disagreements()   – compares sentiment signals across the three
                              analyst sections and flags contradictions.
2. assemble_analyst_note()  – stitches the sourced sections into the
                              final one-page note with a header, summary,
                              and any flagged disagreements.

This agent is also the Orchestrator that fans out tasks to the analyst
agents and fans them back in.  See manager.py for the full pipeline.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from shared_memory import SharedMemory


# ══════════════════════════════════════════════════════════════
# Tool 1 – Detect disagreements between analyst sections
# ══════════════════════════════════════════════════════════════

def _extract_sentiment(text: str) -> str:
    """Coarsely classify a block of text as POSITIVE / NEGATIVE / NEUTRAL."""
    text_lower = text.lower()
    pos_hits = sum(
        1 for w in ["strong", "growth", "positive", "bullish", "opportunity", "record"]
        if w in text_lower
    )
    neg_hits = sum(
        1 for w in ["risk", "decline", "caution", "red flag", "warning", "challenge",
                    "headwind", "declining", "cautious"]
        if w in text_lower
    )
    if pos_hits > neg_hits + 1:
        return "POSITIVE"
    elif neg_hits > pos_hits + 1:
        return "NEGATIVE"
    return "NEUTRAL"


def detect_disagreements(
    revenue_section: str,
    risk_section:    str,
    outlook_section: str,
) -> List[str]:
    """
    Tool 1 – Flag cases where analysts disagree:
      - Revenue is strong BUT Risk is HIGH
      - Outlook is BULLISH BUT Revenue is DECLINING
      - Risk is LOW BUT Outlook is CAUTIOUS
    Returns a list of human-readable disagreement strings.
    """
    rev_sent  = _extract_sentiment(revenue_section)
    risk_sent = _extract_sentiment(risk_section)
    out_sent  = _extract_sentiment(outlook_section)

    disagreements: List[str] = []

    if rev_sent == "POSITIVE" and risk_sent == "NEGATIVE":
        disagreements.append(
            "⚠ DISAGREEMENT: Revenue Analyst reports STRONG revenue, but Risk Analyst "
            "flags HIGH risk – investors should scrutinise cost structure and demand quality."
        )
    if out_sent == "POSITIVE" and risk_sent == "NEGATIVE":
        disagreements.append(
            "⚠ DISAGREEMENT: Outlook Analyst is BULLISH on guidance while Risk Analyst "
            "identifies material risks – forward guidance may be overly optimistic."
        )
    if rev_sent == "NEGATIVE" and out_sent == "POSITIVE":
        disagreements.append(
            "⚠ DISAGREEMENT: Revenue Analyst signals DECLINING revenue but Outlook Analyst "
            "is POSITIVE – verify that guidance is not extrapolating a one-off recovery."
        )
    if risk_sent == "POSITIVE" and out_sent == "NEGATIVE":
        disagreements.append(
            "⚠ DISAGREEMENT: Risk profile appears LOW, but Outlook Analyst is CAUTIOUS – "
            "management may be sandbagging guidance."
        )

    if not disagreements:
        disagreements.append(
            "✅ All three analysts are broadly aligned – no material disagreements detected."
        )

    return disagreements


# ══════════════════════════════════════════════════════════════
# Tool 2 – Assemble the final one-page analyst note
# ══════════════════════════════════════════════════════════════

def assemble_analyst_note(
    figures:         Dict[str, Any],
    revenue_section: str,
    risk_section:    str,
    outlook_section: str,
    comparison_section: str,
    disagreements:   List[str],
    company_name:    str = "Company",
    quarter_label:   str = "Q3 FY2024",
) -> str:
    """
    Tool 2 – Produce the final, coherent one-page analyst note.
    All claims are carried over from the sourced sections.
    """
    import datetime
    today = datetime.date.today().strftime("%d %B %Y")

    # ── Header ────────────────────────────────────────────────
    header = f"""# ANALYST NOTE: {company_name.upper()} – {quarter_label} Earnings
**Date:** {today}
**Classification:** For Educational Purposes | Multi-Agent Generated Report
**System:** Financial Earnings Report Analysis Desk (FERAD)

---
"""

    # ── Executive Summary ─────────────────────────────────────
    rev_val = figures.get("revenue", {}).get("value")
    rev_unit = figures.get("revenue", {}).get("unit", "M USD")
    yoy_val = figures.get("yoy_growth", {}).get("value")
    eps_val = figures.get("eps", {}).get("value")
    gm_val  = figures.get("gross_margin", {}).get("value")

    summary_lines = ["## Executive Summary", ""]
    if rev_val:
        summary_lines.append(
            f"**{company_name}** reported revenue of **${rev_val:,.1f} {rev_unit}** for {quarter_label}."
        )
    if yoy_val is not None:
        direction = "grew" if yoy_val >= 0 else "declined"
        summary_lines.append(f"Revenue {direction} **{abs(yoy_val):.1f}%** year-over-year.")
    if eps_val:
        summary_lines.append(f"Diluted EPS came in at **${eps_val:.2f}**.")
    if gm_val:
        summary_lines.append(f"Gross margin stood at **{gm_val:.1f}%**.")
    summary_lines.append("")

    # ── Disagreement Flags ────────────────────────────────────
    flag_section = "\n## Analyst Disagreement Flags\n\n"
    for d in disagreements:
        flag_section += f"- {d}\n"
    flag_section += "\n---\n"

    # ── Assemble full note ────────────────────────────────────
    sections = [
        header,
        "\n".join(summary_lines),
        "---\n",
        revenue_section,
        "---\n",
        risk_section,
        "---\n",
        outlook_section,
        "---\n",
        comparison_section,
        flag_section,
        "---\n",
        "## Disclaimer\n\n"
        "_This note is generated by an automated multi-agent AI system for "
        "educational purposes only. It does not constitute investment advice. "
        "All figures are sourced directly from the earnings report text._\n",
    ]

    return "\n".join(sections)


# ══════════════════════════════════════════════════════════════
# Agent class
# ══════════════════════════════════════════════════════════════

class EditorManager:
    NAME = "Editor Manager"

    def __init__(
        self,
        memory:       SharedMemory,
        company_name: str = "Company",
        quarter_label: str = "Q3 FY2024",
    ) -> None:
        self.memory        = memory
        self.company_name  = company_name
        self.quarter_label = quarter_label

    def run(self) -> str:
        mem = self.memory
        mem.record(self.NAME, "START", "Fan-in: collecting analyst sections")

        rev  = mem.revenue_analysis
        risk = mem.risk_analysis
        out  = mem.outlook_analysis
        comp = mem.comparison_report or "## Quarter-over-Quarter Comparison\n\nNo comparison data provided.\n"

        for field, val in [("revenue_analysis", rev), ("risk_analysis", risk), ("outlook_analysis", out)]:
            if not val:
                raise ValueError(f"SharedMemory.{field} is empty – run all analysts first.")

        # ── Tool 1 ──────────────────────────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "detect_disagreements")
        disagreements = detect_disagreements(rev, risk, out)
        mem.record(self.NAME, "TOOL_RESULT", f"{len(disagreements)} flag(s): {disagreements}")

        # ── Tool 2 ──────────────────────────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "assemble_analyst_note")
        final_note = assemble_analyst_note(
            figures=mem.current_figures,
            revenue_section=rev,
            risk_section=risk,
            outlook_section=out,
            comparison_section=comp,
            disagreements=disagreements,
            company_name=self.company_name,
            quarter_label=self.quarter_label,
        )
        mem.record(self.NAME, "TOOL_RESULT", f"Final note: {len(final_note)} chars")

        mem.final_note = final_note
        mem.record(self.NAME, "WRITE_MEMORY", "final_note")
        mem.record(self.NAME, "END", "Fan-in complete – final analyst note written")

        return final_note
