"""
comparison_agent.py
===================
Agent 5 – Comparison Agent  (Group-of-3 add-on)
Role  : Compares current-quarter KPIs against previous-quarter KPIs
        and reports the direction (↑ / ↓ / →) and magnitude of change
        for each metric.

Tools
-----
1. compute_metric_deltas()   – calculates absolute and % changes for
                               every shared KPI.
2. format_comparison_table() – renders an ASCII/markdown delta table
                               with directional indicators and sourced
                               reference sentences.
"""

from typing import Any, Dict, List, Tuple
from shared_memory import SharedMemory


# ══════════════════════════════════════════════════════════════
# Tool 1 – Compute metric deltas between quarters
# ══════════════════════════════════════════════════════════════

_DISPLAY_NAMES = {
    "revenue":          "Revenue",
    "net_income":       "Net Income",
    "gross_profit":     "Gross Profit",
    "operating_income": "Operating Income",
    "eps":              "EPS",
    "gross_margin":     "Gross Margin",
    "operating_margin": "Operating Margin",
    "net_margin":       "Net Margin",
    "yoy_growth":       "YoY Growth",
    "free_cash_flow":   "Free Cash Flow",
    "guidance_revenue": "Guidance Revenue",
    "guidance_eps":     "Guidance EPS",
}


def compute_metric_deltas(
    current: Dict[str, Any],
    previous: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Tool 1 – For every KPI present in both quarters, compute the delta.

    Returns a list of dicts:
      {metric, display_name, current_value, previous_value,
       abs_delta, pct_delta, direction, unit, current_source}
    """
    deltas: List[Dict[str, Any]] = []
    all_keys = set(current.keys()) | set(previous.keys())

    for key in sorted(all_keys):
        cur_obj = current.get(key, {})
        prv_obj = previous.get(key, {})

        cur_val = cur_obj.get("value") if cur_obj else None
        prv_val = prv_obj.get("value") if prv_obj else None

        if cur_val is None and prv_val is None:
            continue

        unit = (cur_obj or prv_obj).get("unit", "")
        display = _DISPLAY_NAMES.get(key, key.replace("_", " ").title())

        if cur_val is not None and prv_val is not None:
            abs_delta = round(cur_val - prv_val, 2)
            pct_delta = round(((cur_val - prv_val) / prv_val) * 100, 1) if prv_val != 0 else None
            if abs_delta > 0:
                direction = "↑"
            elif abs_delta < 0:
                direction = "↓"
            else:
                direction = "→"
        else:
            abs_delta = None
            pct_delta = None
            direction = "—"

        deltas.append({
            "metric":          key,
            "display_name":    display,
            "current_value":   cur_val,
            "previous_value":  prv_val,
            "abs_delta":       abs_delta,
            "pct_delta":       pct_delta,
            "direction":       direction,
            "unit":            unit,
            "current_source":  cur_obj.get("source", "") if cur_obj else "",
        })

    return deltas


# ══════════════════════════════════════════════════════════════
# Tool 2 – Format delta table as Markdown
# ══════════════════════════════════════════════════════════════

def format_comparison_table(deltas: List[Dict[str, Any]]) -> str:
    """
    Tool 2 – Render a sourced markdown comparison table.
    """
    if not deltas:
        return "## Quarter-over-Quarter Comparison\n\nNo previous-quarter data available.\n"

    lines = ["## Quarter-over-Quarter Comparison", ""]
    lines.append(
        "| Metric | Prior Q | Current Q | Δ Absolute | Δ % | Dir |"
    )
    lines.append(
        "|--------|---------|-----------|-----------|-----|-----|"
    )

    for d in deltas:
        def fmt(v, unit=""):
            if v is None:
                return "N/A"
            if unit == "%":
                return f"{v:.1f}%"
            if unit == "M USD":
                return f"${v:,.1f}M"
            return f"{v}"

        unit = d["unit"]
        cur  = fmt(d["current_value"],  unit)
        prv  = fmt(d["previous_value"], unit)
        abd  = fmt(d["abs_delta"],      unit)
        pct  = f"{d['pct_delta']:.1f}%" if d["pct_delta"] is not None else "N/A"
        dir_ = d["direction"]
        name = d["display_name"]
        lines.append(f"| {name} | {prv} | {cur} | {abd} | {pct} | {dir_} |")

    lines.append("")

    # Key movers section (largest % changes)
    movers = sorted(
        [d for d in deltas if d["pct_delta"] is not None],
        key=lambda x: abs(x["pct_delta"] or 0),
        reverse=True,
    )[:3]

    if movers:
        lines.append("**Top Movers (QoQ):**")
        for d in movers:
            src = d["current_source"][:150] if d["current_source"] else "N/A"
            lines.append(
                f"  - **{d['display_name']}**: {d['direction']} {abs(d['pct_delta'] or 0):.1f}%"
                f" — _{src}_"
            )
        lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Agent class
# ══════════════════════════════════════════════════════════════

class ComparisonAgent:
    NAME = "Comparison Agent"

    def __init__(self, memory: SharedMemory) -> None:
        self.memory = memory

    def run(self) -> str:
        mem = self.memory
        mem.record(self.NAME, "START", "Comparing current vs. previous quarter")

        current  = mem.current_figures
        previous = mem.previous_figures

        if not current:
            raise ValueError("No current figures in SharedMemory.")

        # ── Tool 1 ──────────────────────────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "compute_metric_deltas")
        if not previous:
            mem.record(self.NAME, "WARN",
                       "No previous_figures in SharedMemory – comparison limited.")
            deltas = []
        else:
            deltas = compute_metric_deltas(current, previous)
        mem.record(self.NAME, "TOOL_RESULT", f"{len(deltas)} metric deltas computed")

        # ── Tool 2 ──────────────────────────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "format_comparison_table")
        report = format_comparison_table(deltas)
        mem.record(self.NAME, "TOOL_RESULT", f"Comparison table: {len(report)} chars")

        mem.comparison_report = report
        mem.record(self.NAME, "WRITE_MEMORY", "comparison_report")
        mem.record(self.NAME, "END", "Comparison analysis complete")

        return report
