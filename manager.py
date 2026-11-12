"""
manager.py
==========
Orchestration pipeline – Financial Earnings Report Analysis Desk (FERAD)
=========================================================================
Architecture: Fan-out / Fan-in with a Manager (EditorManager)

Flow
----
1. Load document  →  SharedMemory.raw_text
2. ExtractionAgent  →  SharedMemory.current_figures          [sequential: must run first]
3. ComparisonAgent  →  SharedMemory.comparison_report        [needs current_figures + previous_figures]
   RevenueAnalyst   →  SharedMemory.revenue_analysis         ┐
   RiskAnalyst      →  SharedMemory.risk_analysis            ├─ FAN-OUT (parallel in concept)
   OutlookAnalyst   →  SharedMemory.outlook_analysis         ┘
4. EditorManager    →  SharedMemory.final_note               [FAN-IN: waits for all three]

Note: True async parallelism is intentionally avoided here so the
      notebook trace remains readable.  The fan-out is conceptual;
      each analyst reads from the shared blackboard independently.

Framework: Microsoft Semantic Kernel (SK) -- the SharedMemory object
           acts as SK's KernelArguments / context, and each Agent class
           mirrors an SK ChatCompletionAgent with its own plugin tools.
"""

import os
import sys
import datetime
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from shared_memory import SharedMemory
from document_loader import auto_load, make_previous_quarter_figures
from extraction_agent import ExtractionAgent
from revenue_analyst import RevenueAnalyst
from risk_analyst import RiskAnalyst
from outlook_analyst import OutlookAnalyst
from comparison_agent import ComparisonAgent
from editor_manager import EditorManager


# ─────────────────────────────────────────────────────────────
# Rich console (graceful fallback if rich not installed)
# ─────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.text import Text
    console = Console(highlight=False, markup=False, emoji=False)
    RICH = True
except ImportError:
    RICH = False
    class _FallbackConsole:
        def print(self, *args, **kwargs): print(*args)
        def rule(self, *args, **kwargs): print("=" * 60)
    console = _FallbackConsole()


def _banner(msg: str) -> None:
    if RICH:
        try:
            console.rule(msg)
        except Exception:
            print(f"\n{'='*60}\n  {msg}\n{'='*60}")
    else:
        print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def _agent_log(agent: str, action: str, data: str = "") -> None:
    ts = datetime.datetime.utcnow().strftime("%H:%M:%S")
    msg = f"[{ts}] {agent} | {action} | {str(data)[:100]}"
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


# ─────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────

def run_pipeline(
    source: str,
    company_name: str = "Company",
    quarter_label: str = "Q3 FY2024",
    previous_quarter_source: Optional[str] = None,
    synthetic_prev_delta: float = -7.0,
    output_file: str = "analyst_note.md",
) -> str:
    """
    Run the full multi-agent pipeline.

    Parameters
    ----------
    source                 : raw text, .txt path, or .pdf path for current quarter
    company_name           : company name for the note header
    quarter_label          : e.g. "Q3 FY2024"
    previous_quarter_source: raw text / path for prior quarter (optional)
    synthetic_prev_delta   : if no prior source, scale current by this % to simulate prior
    output_file            : path where the final note is saved

    Returns
    -------
    The full analyst note as a string.
    """
    _banner("FINANCIAL EARNINGS REPORT ANALYSIS DESK (FERAD)")
    _banner(f"Company: {company_name}  |  Quarter: {quarter_label}")

    memory = SharedMemory()
    memory.record("Manager", "PIPELINE_START", f"{company_name} / {quarter_label}")

    # ── Step 0: Load document ─────────────────────────────────────────────
    _banner("Step 0 – Document Loading")
    _agent_log("Manager", "LOAD_DOC", source[:60] + "...")
    memory.raw_text = auto_load(source)
    memory.record("Manager", "DOC_LOADED", f"{len(memory.raw_text)} chars")
    _agent_log("Manager", "DOC_LOADED", f"{len(memory.raw_text)} chars")

    # Load previous quarter if provided
    if previous_quarter_source:
        prev_text = auto_load(previous_quarter_source)
        memory.record("Manager", "PREV_DOC_LOADED", f"{len(prev_text)} chars")
        # We'll extract figures from it later (re-use ExtractionAgent)

    # ── Step 1: Extraction Agent ─────────────────────────────────────────
    _banner("Step 1 – Extraction Agent  [SEQUENTIAL]")
    _agent_log("Extraction Agent", "START")
    ext_agent = ExtractionAgent(memory)
    figures = ext_agent.run()
    _agent_log("Extraction Agent", "DONE", f"{len(figures)} KPIs: {list(figures.keys())}")

    # Load / synthesise previous-quarter figures
    if previous_quarter_source:
        _agent_log("Manager", "EXTRACTING_PREV_QUARTER")
        prev_mem = SharedMemory()
        prev_mem.raw_text = auto_load(previous_quarter_source)
        prev_agent = ExtractionAgent(prev_mem)
        prev_figures = prev_agent.run()
        memory.previous_figures = prev_figures
        memory.record("Manager", "PREV_FIGURES_LOADED", list(prev_figures.keys()))
    else:
        _agent_log("Manager", "SYNTHESISING_PREV_QUARTER",
                   f"scaling current figures by {synthetic_prev_delta:+.0f}%")
        memory.previous_figures = make_previous_quarter_figures(figures, synthetic_prev_delta)
        memory.record("Manager", "PREV_FIGURES_SYNTHETIC", list(memory.previous_figures.keys()))

    # ── Step 2: FAN-OUT ───────────────────────────────────────────────────
    _banner("Step 2 – FAN-OUT  [Parallel Analyst Agents]")

    # Revenue Analyst
    _agent_log("Revenue Analyst", "START")
    rev_agent = RevenueAnalyst(memory)
    rev_agent.run()
    _agent_log("Revenue Analyst", "DONE")

    # Risk Analyst
    _agent_log("Risk Analyst", "START")
    risk_agent = RiskAnalyst(memory)
    risk_agent.run()
    _agent_log("Risk Analyst", "DONE")

    # Outlook Analyst
    _agent_log("Outlook Analyst", "START")
    out_agent = OutlookAnalyst(memory)
    out_agent.run()
    _agent_log("Outlook Analyst", "DONE")

    # Comparison Agent (Group-of-3 add-on)
    _agent_log("Comparison Agent", "START")
    comp_agent = ComparisonAgent(memory)
    comp_agent.run()
    _agent_log("Comparison Agent", "DONE")

    # ── Step 3: FAN-IN – Editor Manager ──────────────────────────────────
    _banner("Step 3 – FAN-IN  [Editor Manager]")
    _agent_log("Editor Manager", "START")
    editor = EditorManager(memory, company_name=company_name, quarter_label=quarter_label)
    final_note = editor.run()
    _agent_log("Editor Manager", "DONE", f"{len(final_note)} chars")

    # ── Step 4: Save outputs ──────────────────────────────────────────────
    _banner("Step 4 – Saving Outputs")
    Path(output_file).write_text(final_note, encoding="utf-8")
    _agent_log("Manager", "NOTE_SAVED", output_file)
    memory.record("Manager", "PIPELINE_END", output_file)

    _banner("PIPELINE COMPLETE")

    if RICH:
        try:
            console.print(Panel.fit(
                f"[bold green][OK] Analyst note saved to:[/bold green] [cyan]{output_file}[/cyan]\n"
                f"[dim]Trace events: {len(memory.agent_trace)}  |  Run log: run_log.jsonl[/dim]",
                title="[bold]FERAD – Done[/bold]"
            ))
        except Exception:
            print(f"\n[OK] Analyst note saved to: {output_file}")
            print(f"Trace events: {len(memory.agent_trace)}  |  Run log: run_log.jsonl\n")
    else:
        print(f"\n[OK] Analyst note saved to: {output_file}")
        print(f"Trace events: {len(memory.agent_trace)}  |  Run log: run_log.jsonl\n")

    return final_note


# ─────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Financial Earnings Report Analysis Desk (FERAD)"
    )
    parser.add_argument("source", help="Report text / .txt / .pdf path")
    parser.add_argument("--company", default="Company", help="Company name")
    parser.add_argument("--quarter", default="Q3 FY2024", help="Quarter label")
    parser.add_argument("--prev", default=None, help="Previous quarter source (optional)")
    parser.add_argument("--output", default="analyst_note.md", help="Output file path")
    args = parser.parse_args()

    note = run_pipeline(
        source=args.source,
        company_name=args.company,
        quarter_label=args.quarter,
        previous_quarter_source=args.prev,
        output_file=args.output,
    )
    print("\n" + "=" * 60)
    print("ANALYST NOTE PREVIEW (first 1500 chars)")
    print("=" * 60)
    print(note[:1500])
