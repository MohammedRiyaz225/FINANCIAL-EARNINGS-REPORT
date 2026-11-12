# Financial Earnings Report Analysis Desk (FERAD)
## Group 9 — Multi-Agent System Documentation

---

### Project Title
**FINANCIAL EARNINGS REPORT ANALYSIS DESK**

### Objective
To design, build, and demonstrate a production-ready multi-agent system that automates an enterprise workflow, by applying a defined coordination architecture, framework-based agent development (Microsoft Agent Framework / Semantic Kernel pattern), grounded retrieval and shared memory, and collaborative task execution across specialized agents.

### Group Members
| Registration Number | Roll Number | Student Name |
|---|---|---|
| *Registration Number 1* | *Roll Number 1* | *Student Name 1* |
| *Registration Number 2* | *Roll Number 2* | *Student Name 2* |
| *Registration Number 3* | *Roll Number 3* | *Student Name 3* |

---

## Agent Roster

| # | Agent | Module | Role |
|---|-------|--------|------|
| 1 | **Extraction Agent** | `extraction_agent.py` | Pulls key KPIs (revenue, profit, margin, EPS, guidance) from raw report text using regex extraction and RAG |
| 2 | **Revenue Analyst** | `revenue_analyst.py` | Computes derived growth metrics and produces sourced revenue/margin commentary |
| 3 | **Risk Analyst** | `risk_analyst.py` | Scans for risk signals across 8 categories, ranks by severity, cross-references figures |
| 4 | **Outlook Analyst** | `outlook_analyst.py` | Identifies forward-looking statements, assesses guidance specificity and management tone |
| 5 | **Comparison Agent** | `comparison_agent.py` | Computes QoQ metric deltas and renders a sourced comparison table *(Group-of-3 add-on)* |
| 6 | **Editor Manager** | `editor_manager.py` | Fan-in orchestrator: detects analyst disagreements, assembles the final one-page note |

**Supporting modules:** `shared_memory.py` (blackboard), `document_loader.py` (report ingestion), `manager.py` (pipeline CLI).

---

## Architecture

### Pattern: Fan-Out / Fan-In with a Manager

```
                    ┌──────────────────────────┐
                    │     DOCUMENT LOADER       │
                    │  (txt / pdf / raw string) │
                    └────────────┬─────────────┘
                                 │ raw_text
                                 ▼
                    ┌──────────────────────────┐
                    │    EXTRACTION AGENT       │  (Sequential – must run first)
                    │  Tool 1: parse_figures()  │
                    │  Tool 2: retrieve_chunks()│
                    └────────────┬─────────────┘
                                 │ current_figures → SharedMemory
                    ┌────────────┴──────────────────────────────────────┐
                    │               FAN-OUT (parallel)                   │
          ┌─────────▼──────────┐ ┌──────────▼──────────┐ ┌─────────────▼──────────┐ ┌──────────▼─────────┐
          │  REVENUE ANALYST   │ │   RISK ANALYST       │ │   OUTLOOK ANALYST       │ │ COMPARISON AGENT   │
          │ compute_metrics()  │ │ scan_risk_signals()  │ │ extract_guidance()      │ │ compute_deltas()   │
          │ format_commentary()│ │ score_and_rank()     │ │ assess_quality()        │ │ format_table()     │
          └─────────┬──────────┘ └──────────┬──────────┘ └─────────────┬───────────┘ └──────────┬─────────┘
                    │ revenue_analysis       │ risk_analysis             │ outlook_analysis        │ comparison_report
                    └────────────────────────┴───────────────────────────┴─────────────────────────┘
                                                          │
                                                          ▼  FAN-IN
                                         ┌───────────────────────────────┐
                                         │       EDITOR MANAGER          │
                                         │  detect_disagreements()       │
                                         │  assemble_analyst_note()      │
                                         └───────────────┬───────────────┘
                                                          │
                                                   final_note.md
```

### Why Fan-Out / Fan-In fits this problem

The three analysis dimensions (revenue, risk, outlook) are **independent**: each reads the same extracted KPIs but applies a different lens. Running them as parallel fan-out branches maximises throughput in a production deployment. The Editor Manager then acts as the coordinating brain, enforcing consistency, catching contradictions, and synthesising one coherent deliverable — exactly the editorial workflow a real sell-side desk follows.

### Framework: Microsoft Semantic Kernel

Each agent class mirrors a **Semantic Kernel ChatCompletionAgent** pattern with its own kernel plugin (the two tool functions). `SharedMemory` maps directly to SK's `KernelArguments` / context store, acting as the shared blackboard every agent reads and writes. The pipeline in `manager.py` mirrors SK's `AgentGroupChat` fan-out execution model.

---

## Tools Per Agent

| Agent | Tool 1 | Tool 2 |
|-------|--------|--------|
| Extraction Agent | `parse_financial_figures(text)` — regex KPI extraction | `retrieve_relevant_chunks(text, top_k)` — keyword-scored RAG |
| Revenue Analyst | `compute_revenue_metrics(current, previous)` — derives YoY/QoQ growth | `format_revenue_commentary(metrics, figures)` — sourced narrative |
| Risk Analyst | `scan_risk_signals(text)` — 8-category keyword risk scan | `score_and_rank_risks(signals, figures)` — severity ranking + formatting |
| Outlook Analyst | `extract_guidance_statements(text, figures)` — forward-looking sentence extraction | `assess_guidance_quality(guidance_data)` — specificity/tone rating |
| Comparison Agent | `compute_metric_deltas(current, previous)` — absolute and % QoQ changes | `format_comparison_table(deltas)` — markdown delta table |
| Editor Manager | `detect_disagreements(rev, risk, out)` — cross-analyst sentiment check | `assemble_analyst_note(...)` — final one-page note assembly |

---

## What the Memory / Retrieval Holds

**Shared Blackboard (`SharedMemory`)** — a single Python object passed by reference to every agent:

| Field | Written by | Read by |
|-------|-----------|---------|
| `raw_text` | Manager (document loader) | Extraction, Risk, Outlook agents |
| `current_figures` | Extraction Agent | Revenue, Risk, Outlook, Comparison, Editor |
| `previous_figures` | Manager / Comparison Agent | Comparison, Revenue Analyst |
| `revenue_analysis` | Revenue Analyst | Editor Manager |
| `risk_analysis` | Risk Analyst | Editor Manager |
| `outlook_analysis` | Outlook Analyst | Editor Manager |
| `comparison_report` | Comparison Agent | Editor Manager |
| `final_note` | Editor Manager | — (output) |
| `agent_trace` | All agents (append-only) | Demo notebook display |

**RAG Layer** — `retrieve_relevant_chunks()` applies keyword-scored retrieval over 400-word overlapping document windows. Every extracted figure carries its verbatim `source` sentence so every claim in the final note is traceable.

**Run Log** — `run_log.jsonl` is an append-only on-disk JSONL file. Every tool call and agent event is persisted.

---

## Honest Failure Handled

**Failure:** When no previous-quarter earnings document is available, the `ComparisonAgent` cannot produce a real QoQ delta table, making the comparison section empty and degrading the note quality.

**How it's handled:** The `document_loader.make_previous_quarter_figures()` function synthesises plausible prior-quarter figures by scaling the current extracted KPIs by a configurable `delta_pct` parameter (default –7%). The Comparison Agent detects when `SharedMemory.previous_figures` is empty and records a `WARN` trace event, and the comparison section explicitly labels figures as `[Synthetic prior-quarter estimate]`. This keeps the pipeline runnable and the note complete without silently fabricating data. In production, a real prior-quarter PDF/text would replace the synthetic fallback.

---

## File Index

```
FIN/
├── manager.py                  # Orchestration pipeline (CLI entry point)
├── shared_memory.py            # Shared blackboard + run log
├── document_loader.py          # Report ingestion utility
├── extraction_agent.py         # Agent 1
├── revenue_analyst.py          # Agent 2
├── risk_analyst.py             # Agent 3
├── outlook_analyst.py          # Agent 4
├── comparison_agent.py         # Agent 5  (Group-of-3)
├── editor_manager.py           # Agent 6  (Fan-in / Manager)
├── llm_client.py               # Unified LLM client (Groq / OpenAI / Azure / Offline)
├── test_agents.py              # pytest test suite (3+ scenarios)
├── demo_notebook.ipynb         # Runnable demo notebook
├── sample_report_q3_fy2024.txt # Demo earnings report (current quarter)
├── sample_report_q2_fy2024.txt # Demo earnings report (previous quarter)
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .env                        # Local environment configuration
├── .gitignore                  # Git ignore rules
├── README.md                   # System documentation
└── run_log.jsonl               # Append-only run log (auto-generated)
```

## Environment & LLM Configuration

Configure execution mode and API keys in `.env` (or copy from `.env.example`):

- **Groq API:** Set `GROQ_API_KEY=gsk_...` to enable ultra-fast inference via `llama-3.3-70b-versatile` or `mixtral-8x7b-32768`.
- **Azure OpenAI / OpenAI:** Set `AZURE_OPENAI_API_KEY` or `OPENAI_API_KEY` for GPT-4o models.
- **Offline Mode (Default):** Set `EXECUTION_MODE=offline` for fully grounded, deterministic extraction and RAG scoring without external API costs.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the pipeline on the sample report
python manager.py sample_report_q3_fy2024.txt \
  --company "Apex Technologies Inc." \
  --quarter "Q3 FY2024" \
  --prev sample_report_q2_fy2024.txt \
  --output analyst_note.md

# 3. Run the test suite
pytest test_agents.py -v

# 4. Open and run the demo notebook
jupyter notebook demo_notebook.ipynb
```

