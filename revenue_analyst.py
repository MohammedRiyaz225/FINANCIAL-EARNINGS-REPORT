"""
revenue_analyst.py
==================
Agent 2 – Revenue Analyst
Role  : Reads the extracted KPIs from shared memory and produces a
        grounded, sourced commentary on revenue trajectory and growth.

Tools
-----
1. compute_revenue_metrics()   – derives QoQ / YoY growth rates and
                                 compares vs. consensus estimates if
                                 available in shared memory.
2. format_revenue_commentary() – templated narrative generation with
                                 inline citations to source sentences.
"""

from typing import Any, Dict, Optional
from shared_memory import SharedMemory


# ══════════════════════════════════════════════════════════════
# Tool 1 – Compute revenue-related derived metrics
# ══════════════════════════════════════════════════════════════

def compute_revenue_metrics(
    current: Dict[str, Any],
    previous: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tool 1 – Derive growth rates and margin comparisons.

    Parameters
    ----------
    current  : KPIs from ExtractionAgent (this quarter)
    previous : KPIs from the previous quarter (optional)

    Returns
    -------
    metrics dict with growth rates, margin delta, and assessment flags.
    """
    metrics: Dict[str, Any] = {}

    rev = current.get("revenue", {})
    if rev:
        metrics["revenue_value"] = rev.get("value")
        metrics["revenue_unit"]  = rev.get("unit", "M USD")
        metrics["revenue_source"] = rev.get("source", "N/A")

    # YoY growth – use extracted figure if present
    yoy = current.get("yoy_growth", {})
    if yoy:
        metrics["yoy_growth_pct"] = yoy.get("value")
        metrics["yoy_source"] = yoy.get("source", "N/A")

    # QoQ growth from Comparison data (if previous quarter available)
    if previous:
        prev_rev = previous.get("revenue", {})
        if prev_rev and rev:
            cur_v = rev.get("value", 0)
            prv_v = prev_rev.get("value", 0)
            if prv_v and prv_v != 0:
                qoq = round(((cur_v - prv_v) / prv_v) * 100, 2)
                metrics["qoq_growth_pct"] = qoq
                metrics["qoq_direction"] = "↑ growth" if qoq >= 0 else "↓ decline"

    # Gross & operating margins
    gm = current.get("gross_margin", {})
    if gm:
        metrics["gross_margin_pct"] = gm.get("value")
        metrics["gross_margin_source"] = gm.get("source", "N/A")

    om = current.get("operating_margin", {})
    if om:
        metrics["operating_margin_pct"] = om.get("value")
        metrics["operating_margin_source"] = om.get("source", "N/A")

    # Assessment flag
    yoy_val = metrics.get("yoy_growth_pct", 0) or 0
    if yoy_val >= 15:
        metrics["revenue_assessment"] = "STRONG"
    elif yoy_val >= 5:
        metrics["revenue_assessment"] = "MODERATE"
    elif yoy_val >= 0:
        metrics["revenue_assessment"] = "FLAT/SOFT"
    else:
        metrics["revenue_assessment"] = "DECLINING"

    return metrics


# ══════════════════════════════════════════════════════════════
# Tool 2 – Format sourced revenue commentary
# ══════════════════════════════════════════════════════════════

def format_revenue_commentary(metrics: Dict[str, Any], figures: Dict[str, Any]) -> str:
    """
    Tool 2 – Produce a structured, sourced revenue section.
    Every number is tied back to its source sentence.
    """
    lines = ["## Revenue & Growth Analysis", ""]

    # Headline revenue
    rev_val  = metrics.get("revenue_value")
    rev_unit = metrics.get("revenue_unit", "M USD")
    if rev_val is not None:
        rev_display = f"${rev_val:,.1f} {rev_unit}"
        lines.append(f"**Headline Revenue:** {rev_display}")
        src = metrics.get("revenue_source", "")
        if src:
            lines.append(f"> *Source:* \"{src[:150]}\"")
        lines.append("")

    # YoY growth
    yoy = metrics.get("yoy_growth_pct")
    if yoy is not None:
        direction = "grew" if yoy >= 0 else "declined"
        lines.append(f"**Year-over-Year Growth:** Revenue {direction} by **{abs(yoy):.1f}%** YoY.")
        yoy_src = metrics.get("yoy_source", "")
        if yoy_src:
            lines.append(f"> *Source:* \"{yoy_src[:150]}\"")
        lines.append("")

    # QoQ growth (if available)
    qoq = metrics.get("qoq_growth_pct")
    if qoq is not None:
        lines.append(f"**Quarter-over-Quarter Growth:** {metrics.get('qoq_direction', '')} of **{abs(qoq):.1f}%** QoQ.")
        lines.append("")

    # Margins
    gm = metrics.get("gross_margin_pct")
    om = metrics.get("operating_margin_pct")
    if gm is not None or om is not None:
        lines.append("**Profitability Margins:**")
        if gm is not None:
            lines.append(f"  - Gross Margin: **{gm:.1f}%**")
            gm_src = metrics.get("gross_margin_source", "")
            if gm_src:
                lines.append(f"    > *Source:* \"{gm_src[:150]}\"")
        if om is not None:
            lines.append(f"  - Operating Margin: **{om:.1f}%**")
            om_src = metrics.get("operating_margin_source", "")
            if om_src:
                lines.append(f"    > *Source:* \"{om_src[:150]}\"")
        lines.append("")

    # EPS
    eps = figures.get("eps", {})
    if eps:
        lines.append(f"**Earnings Per Share (EPS):** ${eps.get('value', 'N/A')}")
        lines.append(f"> *Source:* \"{eps.get('source', '')[:150]}\"")
        lines.append("")

    # Overall assessment
    assessment = metrics.get("revenue_assessment", "N/A")
    assessment_color_map = {
        "STRONG": "🟢 STRONG",
        "MODERATE": "🟡 MODERATE",
        "FLAT/SOFT": "🟠 FLAT/SOFT",
        "DECLINING": "🔴 DECLINING",
    }
    lines.append(f"**Revenue Assessment:** {assessment_color_map.get(assessment, assessment)}")
    lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Agent class
# ══════════════════════════════════════════════════════════════

class RevenueAnalyst:
    NAME = "Revenue Analyst"

    def __init__(self, memory: SharedMemory) -> None:
        self.memory = memory

    def run(self) -> str:
        mem = self.memory
        mem.record(self.NAME, "START", "Reading KPIs from shared memory")

        figures  = mem.current_figures
        previous = mem.previous_figures or None

        if not figures:
            raise ValueError("No figures in SharedMemory – run ExtractionAgent first.")

        # ── Tool 1 ──────────────────────────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "compute_revenue_metrics")
        metrics = compute_revenue_metrics(figures, previous)
        mem.record(self.NAME, "TOOL_RESULT", metrics)

        # ── Tool 2 ──────────────────────────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "format_revenue_commentary")
        commentary = format_revenue_commentary(metrics, figures)
        mem.record(self.NAME, "TOOL_RESULT", f"Commentary length: {len(commentary)} chars")

        # Write to shared blackboard
        mem.revenue_analysis = commentary
        mem.record(self.NAME, "WRITE_MEMORY", "revenue_analysis")
        mem.record(self.NAME, "END", "Revenue analysis complete")

        return commentary
