"""
shared_memory.py
================
Append-only blackboard / shared memory used by every agent.
All agents READ and WRITE this single object so the Manager can
fan-out tasks and fan-in results without coupling agents directly.
"""

import json
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# Run-log path  (append-only, persisted to disk)
# ──────────────────────────────────────────────
LOG_PATH = Path("run_log.jsonl")


def _log(entry: Dict[str, Any]) -> None:
    """Append one JSON-line to the run log (never truncates the file)."""
    entry["ts"] = datetime.datetime.utcnow().isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


# ──────────────────────────────────────────────
# Shared blackboard
# ──────────────────────────────────────────────
class SharedMemory:
    """
    Central shared-state object.  All agents receive a reference to the
    *same* instance so every read/write is visible system-wide.

    Fields
    ------
    raw_text          : full text extracted from the earnings report PDF
    current_figures   : dict of KPIs extracted by the Extraction Agent
    previous_figures  : dict of KPIs from the previous quarter (for Comparison)
    revenue_analysis  : note produced by the Revenue Analyst
    risk_analysis     : note produced by the Risk Analyst
    outlook_analysis  : note produced by the Outlook Analyst
    comparison_report : delta report produced by the Comparison Agent
    final_note        : one-page analyst note produced by the Editor Manager
    agent_trace       : ordered list of (agent, action, data) for the demo
    """

    def __init__(self) -> None:
        self.raw_text: str = ""
        self.current_figures: Dict[str, Any] = {}
        self.previous_figures: Dict[str, Any] = {}
        self.revenue_analysis: str = ""
        self.risk_analysis: str = ""
        self.outlook_analysis: str = ""
        self.comparison_report: str = ""
        self.final_note: str = ""
        self.agent_trace: List[Dict[str, Any]] = []

    # ── Helpers ──────────────────────────────
    def record(self, agent: str, action: str, data: Any = None) -> None:
        """Append an event to the trace and to the on-disk run log."""
        entry = {"agent": agent, "action": action, "data": data}
        self.agent_trace.append(entry)
        _log(entry)

    def snapshot(self) -> Dict[str, Any]:
        """Return the full blackboard state as a plain dict."""
        return {
            "raw_text_length": len(self.raw_text),
            "current_figures": self.current_figures,
            "previous_figures": self.previous_figures,
            "revenue_analysis": self.revenue_analysis[:200] if self.revenue_analysis else "",
            "risk_analysis": self.risk_analysis[:200] if self.risk_analysis else "",
            "outlook_analysis": self.outlook_analysis[:200] if self.outlook_analysis else "",
            "comparison_report": self.comparison_report[:200] if self.comparison_report else "",
            "final_note_length": len(self.final_note),
            "trace_events": len(self.agent_trace),
        }
