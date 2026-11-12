"""
server.py
=========
Executive Financial Intelligence Terminal — Multi-Agent Desk (FERAD)
Pattern: Professional Tabbed FinTech Portal with Interactive Agent Visualizer,
Executive Live Analysis, Groq LLM Inference Settings & Grounded Citations.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

from shared_memory import SharedMemory
from document_loader import make_previous_quarter_figures
from extraction_agent import ExtractionAgent
from revenue_analyst import RevenueAnalyst
from risk_analyst import RiskAnalyst
from outlook_analyst import OutlookAnalyst
from comparison_agent import ComparisonAgent
from editor_manager import EditorManager
import llm_client

app = FastAPI(title="FERAD Financial Terminal")

SAMPLE_Q3 = Path(__file__).parent / "sample_report_q3_fy2024.txt"
SAMPLE_Q2 = Path(__file__).parent / "sample_report_q2_fy2024.txt"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FERAD Financial Terminal &bull; Multi-Agent Intelligence</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {
      --bg: #030712;
      --card-bg: rgba(17, 24, 39, 0.75);
      --card-hover: rgba(31, 41, 55, 0.8);
      --border: rgba(255, 255, 255, 0.08);
      --accent: #3b82f6;
      --accent-cyan: #06b6d4;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --text: #f9fafb;
      --text-muted: #9ca3af;
      --text-dim: #6b7280;
      --font: 'Plus Jakarta Sans', sans-serif;
      --mono: 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      background-image: 
        radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.12) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(99, 102, 241, 0.1) 0px, transparent 50%);
      background-attachment: fixed;
      color: var(--text);
      font-family: var(--font);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Header Nav */
    header {
      height: 64px;
      border-bottom: 1px solid var(--border);
      background: rgba(3, 7, 18, 0.85);
      backdrop-filter: blur(16px);
      padding: 0 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .logo-container {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .logo-badge {
      background: linear-gradient(135deg, #3b82f6, #06b6d4);
      width: 32px;
      height: 32px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      color: #fff;
      font-size: 0.95rem;
      box-shadow: 0 0 12px rgba(59, 130, 246, 0.5);
    }
    .logo-text {
      font-weight: 700;
      font-size: 1.1rem;
      letter-spacing: -0.02em;
    }
    .logo-subtitle {
      font-size: 0.75rem;
      color: var(--text-dim);
      font-family: var(--mono);
    }
    .nav-tags {
      display: flex;
      gap: 0.75rem;
      align-items: center;
    }
    .status-pill {
      font-size: 0.75rem;
      font-family: var(--mono);
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--accent-emerald);
      padding: 0.35rem 0.85rem;
      border-radius: 9999px;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .pulse-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--accent-emerald);
      box-shadow: 0 0 8px var(--accent-emerald);
      animation: pulse 1.8s infinite;
    }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

    /* Layout Pattern: Top Navigation Tabs */
    .tabs-bar {
      display: flex;
      border-bottom: 1px solid var(--border);
      background: rgba(17, 24, 39, 0.5);
      padding: 0 2rem;
      gap: 1.5rem;
    }
    .tab-btn {
      background: none;
      border: none;
      color: var(--text-muted);
      padding: 1rem 0.5rem;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
    }
    .tab-btn:hover { color: var(--text); }
    .tab-btn.active {
      color: var(--accent-cyan);
      border-bottom-color: var(--accent-cyan);
    }

    /* Main Container */
    .content-area {
      flex: 1;
      padding: 2rem;
      max-width: 1600px;
      margin: 0 auto;
      width: 100%;
    }

    /* Tab Page 1: Analysis Desk (Side-by-side or stacked) */
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    .desk-grid {
      display: grid;
      grid-template-columns: 460px 1fr;
      gap: 2rem;
    }
    @media (max-width: 1100px) {
      .desk-grid { grid-template-columns: 1fr; }
    }

    .card {
      background: var(--card-bg);
      backdrop-filter: blur(20px);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.5rem;
      box-shadow: 0 20px 30px -15px rgba(0,0,0,0.5);
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border);
    }
    .card-title {
      font-size: 1rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    /* Input Controls */
    .form-group { margin-bottom: 1.15rem; }
    .label-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.4rem;
    }
    label {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-muted);
    }
    .btn-link {
      background: none;
      border: none;
      color: var(--accent-cyan);
      font-size: 0.75rem;
      cursor: pointer;
      font-weight: 600;
      text-decoration: underline;
    }
    .btn-link:hover { color: #67e8f9; }
    input[type="text"], textarea, select {
      width: 100%;
      background: rgba(3, 7, 18, 0.85);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.7rem 0.9rem;
      color: var(--text);
      font-family: inherit;
      font-size: 0.9rem;
    }
    input[type="text"]:focus, textarea:focus, select:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }
    textarea {
      font-family: var(--mono);
      font-size: 0.82rem;
      resize: vertical;
      line-height: 1.5;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }

    /* Button Action */
    .btn-primary {
      width: 100%;
      padding: 0.95rem;
      border-radius: 10px;
      border: none;
      background: linear-gradient(135deg, #3b82f6, #06b6d4);
      color: #fff;
      font-size: 0.95rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      transition: all 0.2s;
      box-shadow: 0 8px 20px -4px rgba(59, 130, 246, 0.4);
    }
    .btn-primary:hover {
      box-shadow: 0 10px 25px -4px rgba(59, 130, 246, 0.6);
      transform: translateY(-1px);
    }
    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }

    /* Agent Coordination Flow Pills */
    .agent-pipeline {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1.25rem;
      flex-wrap: wrap;
    }
    .agent-chip {
      padding: 0.5rem 0.8rem;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border);
      font-size: 0.75rem;
      font-family: var(--mono);
      display: flex;
      align-items: center;
      gap: 0.4rem;
      color: var(--text-muted);
      transition: all 0.3s;
    }
    .agent-chip.active {
      border-color: var(--accent-cyan);
      background: rgba(6, 182, 212, 0.1);
      color: var(--accent-cyan);
    }
    .agent-chip.done {
      border-color: var(--accent-emerald);
      background: rgba(16, 185, 129, 0.08);
      color: var(--accent-emerald);
    }

    /* KPI Highlights */
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }
    @media (max-width: 768px) {
      .kpi-row { grid-template-columns: repeat(2, 1fr); }
    }
    .kpi-card {
      background: rgba(3, 7, 18, 0.7);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.85rem;
      position: relative;
    }
    .kpi-card::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 3px;
      background: var(--accent-cyan);
      border-radius: 8px 0 0 8px;
    }
    .kpi-title { font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700; }
    .kpi-value { font-size: 1.35rem; font-weight: 800; font-family: var(--mono); color: #fff; margin-top: 0.2rem; }

    /* Deliverable Area */
    .deliverable-box {
      background: rgba(3, 7, 18, 0.9);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1.75rem;
      max-height: 600px;
      overflow-y: auto;
      font-size: 0.92rem;
      line-height: 1.7;
    }
    .deliverable-box h1 { font-size: 1.4rem; color: #fff; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem; }
    .deliverable-box h2 { font-size: 1.15rem; color: #38bdf8; margin: 1.25rem 0 0.5rem; }
    .deliverable-box h3 { font-size: 0.95rem; color: #f3f4f6; margin: 0.85rem 0 0.35rem; }
    .deliverable-box blockquote {
      border-left: 3px solid var(--accent-cyan);
      background: rgba(6, 182, 212, 0.05);
      padding: 0.5rem 1rem;
      margin: 0.75rem 0;
      color: var(--text-muted);
      font-style: italic;
      border-radius: 0 6px 6px 0;
    }
    .deliverable-box table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-family: var(--mono); font-size: 0.82rem; }
    .deliverable-box th, .deliverable-box td { border: 1px solid var(--border); padding: 0.5rem 0.75rem; }
    .deliverable-box th { background: rgba(255, 255, 255, 0.03); color: #38bdf8; text-transform: uppercase; }

    /* Spinner */
    .spinner {
      display: none;
      width: 18px;
      height: 18px;
      border: 2px solid rgba(255,255,255,0.2);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Tab 2: Architecture & Flow Pattern */
    .arch-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 2rem;
      max-width: 1000px;
      margin: 0 auto;
    }
    .diagram-pre {
      background: #020617;
      border: 1px solid var(--border);
      padding: 1.5rem;
      border-radius: 10px;
      font-family: var(--mono);
      font-size: 0.85rem;
      color: #38bdf8;
      overflow-x: auto;
      line-height: 1.5;
      margin: 1.25rem 0;
    }

    /* Tab 3: Groq LLM Diagnostics */
    .groq-box {
      background: #020617;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1.25rem;
      margin-top: 1rem;
      font-family: var(--mono);
      font-size: 0.85rem;
    }
    .groq-badge {
      display: inline-block;
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: var(--accent-amber);
    }
  </style>
</head>
<body>
  <!-- Top Bar -->
  <header>
    <div class="logo-container">
      <div class="logo-badge">F</div>
      <div>
        <div class="logo-text">FERAD Executive Terminal</div>
        <div class="logo-subtitle">Financial Earnings Report Analysis Desk</div>
      </div>
    </div>
    <div class="nav-tags">
      <div class="status-pill">
        <div class="pulse-dot"></div>
        <span id="navProviderStatus">GROQ / LLM ONLINE</span>
      </div>
    </div>
  </header>

  <!-- Pattern Navigation Tabs -->
  <nav class="tabs-bar">
    <button class="tab-btn active" onclick="switchTab('deskTab', this)">
      <span>📊</span> Real-Time Analysis Desk
    </button>
    <button class="tab-btn" onclick="switchTab('archTab', this)">
      <span>🏛️</span> Multi-Agent Pattern Architecture
    </button>
    <button class="tab-btn" onclick="switchTab('groqTab', this)">
      <span>⚡</span> Groq LLM Cloud Diagnostics
    </button>
  </nav>

  <main class="content-area">
    <!-- TAB 1: Real-Time Analysis Desk -->
    <div id="deskTab" class="tab-content active">
      <div class="desk-grid">
        <!-- Input Form -->
        <div class="card">
          <div class="card-header">
            <div class="card-title"><span>📥</span> Document Ingestion</div>
            <button type="button" class="btn-link" onclick="loadSampleReport()">Load Sample Q3</button>
          </div>

          <form id="analysisForm">
            <div class="row">
              <div class="form-group">
                <label>Company Identifier</label>
                <input type="text" id="company_name" value="Apex Technologies Inc." required>
              </div>
              <div class="form-group">
                <label>Reporting Period</label>
                <input type="text" id="quarter_label" value="Q3 FY2024" required>
              </div>
            </div>

            <div class="form-group">
              <div class="label-row">
                <label>Current Quarter Text / Filings</label>
                <button type="button" class="btn-link" onclick="loadSampleReport()">Insert Sample</button>
              </div>
              <textarea id="raw_text" rows="8" placeholder="Paste full quarterly text or click 'Load Sample Q3'..." required></textarea>
            </div>

            <div class="form-group">
              <div class="label-row">
                <label>Prior Quarter (QoQ Deltas)</label>
                <button type="button" class="btn-link" onclick="loadSamplePrevReport()">Insert Sample Q2</button>
              </div>
              <textarea id="prev_text" rows="3" placeholder="Optional. If omitted, synthetic -7% baseline is applied."></textarea>
            </div>

            <button type="submit" id="submitBtn" class="btn-primary">
              <div class="spinner" id="spinner"></div>
              <span id="btnText">🚀 Execute 6-Agent Synthesis</span>
            </button>
          </form>
        </div>

        <!-- Output Deliverable -->
        <div class="card">
          <div class="card-header">
            <div class="card-title"><span>📑</span> Sell-Side Note & Audits</div>
            <span id="traceCounter" style="font-size:0.75rem; font-family:var(--mono); color:var(--text-dim);">Ready</span>
          </div>

          <!-- Active Agent Flow Chips -->
          <div class="agent-pipeline">
            <div class="agent-chip" id="chipExt">1. Extraction Agent</div>
            <div class="agent-chip" id="chipRev">2. Revenue Analyst</div>
            <div class="agent-chip" id="chipRisk">3. Risk Analyst</div>
            <div class="agent-chip" id="chipOut">4. Outlook Analyst</div>
            <div class="agent-chip" id="chipComp">5. Comparison Agent</div>
            <div class="agent-chip" id="chipEdit">6. Editor Manager</div>
          </div>

          <!-- KPI Metric Pill Deck -->
          <div class="kpi-row" id="kpiDeck" style="display:none;">
            <div class="kpi-card">
              <div class="kpi-title">Headline Revenue</div>
              <div class="kpi-value" id="valRev">-</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-title">YoY Growth</div>
              <div class="kpi-value" id="valGrowth">-</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-title">Gross Margin</div>
              <div class="kpi-value" id="valMargin">-</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-title">Operating Margin</div>
              <div class="kpi-value" id="valOpMargin">-</div>
            </div>
          </div>

          <!-- Deliverable Viewer -->
          <div class="deliverable-box" id="noteOutput">
            <div style="text-align:center; padding: 4rem 1rem; color:var(--text-dim);">
              <div style="font-size:2.5rem; margin-bottom:0.75rem; opacity:0.4;">📊</div>
              <div>Click <strong>Execute 6-Agent Synthesis</strong> to run the full pipeline with grounded RAG & Groq LLM integration.</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: Multi-Agent Architecture -->
    <div id="archTab" class="tab-content">
      <div class="arch-card">
        <h2 style="font-size:1.4rem; margin-bottom:0.5rem;">Orchestration Pattern: Fan-Out / Fan-In with Editor Manager</h2>
        <p style="color:var(--text-muted); font-size:0.95rem;">
          The system implements Microsoft Semantic Kernel agent design patterns. Independent analyst agents read from a central shared blackboard (<code style="color:var(--accent-cyan);">SharedMemory</code>) in parallel fan-out branches.
        </p>

        <pre class="diagram-pre">
                    ┌──────────────────────────┐
                    │     DOCUMENT LOADER      │
                    │  (txt / pdf / raw string) │
                    └────────────┬─────────────┘
                                 │ raw_text
                                 ▼
                    ┌──────────────────────────┐
                    │    EXTRACTION AGENT      │  (Sequential: must run first)
                    │  Tool 1: parse_figures() │
                    │  Tool 2: retrieve_chunks()│
                    └────────────┬─────────────┘
                                 │ current_figures → SharedMemory
                    ┌────────────┴──────────────────────────────────────┐
                    │               FAN-OUT (parallel)                  │
          ┌─────────▼──────────┐ ┌──────────▼──────────┐ ┌─────────────▼──────────┐ ┌──────────▼─────────┐
          │  REVENUE ANALYST   │ │   RISK ANALYST      │ │   OUTLOOK ANALYST      │ │ COMPARISON AGENT   │
          │ compute_metrics()  │ │ scan_risk_signals() │ │ extract_guidance()     │ │ compute_deltas()   │
          │ format_commentary()│ │ score_and_rank()    │ │ assess_quality()       │ │ format_table()     │
          └─────────┬──────────┘ └──────────┬──────────┘ └─────────────┬──────────┘ └──────────┬─────────┘
                    │ revenue_analysis       │ risk_analysis             │ outlook_analysis       │ comparison_report
                    └────────────────────────┴───────────────────────────┴────────────────────────┘
                                                          │
                                                          ▼  FAN-IN
                                          ┌───────────────────────────────┐
                                          │       EDITOR MANAGER          │
                                          │  detect_disagreements()       │
                                          │  assemble_analyst_note()      │
                                          └───────────────┬───────────────┘
                                                          │
                                                   analyst_note.md
        </pre>
      </div>
    </div>

    <!-- TAB 3: Groq LLM Cloud Diagnostics -->
    <div id="groqTab" class="tab-content">
      <div class="arch-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
          <div>
            <h2 style="font-size:1.3rem;">Groq Cloud LLM Status</h2>
            <p style="color:var(--text-muted); font-size:0.85rem;">Live verification of Groq API connection and available production models.</p>
          </div>
          <button class="btn-primary" style="width:auto; padding:0.6rem 1.25rem;" onclick="testGroqLive()">⚡ Ping Groq API</button>
        </div>

        <div class="groq-box" id="groqDiagnostics">
          Loading provider and key status...
        </div>
      </div>
    </div>
  </main>

  <script>
    function switchTab(tabId, el) {
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      el.classList.add('active');
    }

    async function loadSampleReport() {
      const res = await fetch('/sample/current');
      const text = await res.text();
      document.getElementById('raw_text').value = text;
    }

    async function loadSamplePrevReport() {
      const res = await fetch('/sample/previous');
      const text = await res.text();
      document.getElementById('prev_text').value = text;
    }

    async function testGroqLive() {
      const box = document.getElementById('groqDiagnostics');
      box.innerHTML = 'Testing live Groq API endpoint...';
      try {
        const res = await fetch('/api/groq-status');
        const data = await res.json();
        box.innerHTML = `
<div style="color:#10b981; font-weight:700; margin-bottom:0.5rem;">✅ Connection Status: ${data.status}</div>
<div><strong>Active Model:</strong> ${data.model}</div>
<div><strong>API Key Detected:</strong> ${data.key_masked}</div>
<div><strong>Live Inference Test:</strong> "${data.sample_response}"</div>
<div style="margin-top:0.75rem; color:var(--text-dim); font-size:0.75rem;">Endpoint: https://api.groq.com/openai/v1/chat/completions</div>
        `;
      } catch (err) {
        box.innerHTML = `<div style="color:#ef4444;">Error testing Groq: ${err.message}</div>`;
      }
    }

    const form = document.getElementById('analysisForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const spinner = document.getElementById('spinner');

    const chips = {
      ext: document.getElementById('chipExt'),
      rev: document.getElementById('chipRev'),
      risk: document.getElementById('chipRisk'),
      out: document.getElementById('chipOut'),
      comp: document.getElementById('chipComp'),
      edit: document.getElementById('chipEdit')
    };

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      submitBtn.disabled = true;
      spinner.style.display = 'block';
      btnText.textContent = 'Orchestrating Agents...';

      // Animate stages
      chips.ext.className = 'agent-chip active';
      ['rev', 'risk', 'out', 'comp', 'edit'].forEach(k => chips[k].className = 'agent-chip');

      const payload = {
        company_name: document.getElementById('company_name').value,
        quarter_label: document.getElementById('quarter_label').value,
        raw_text: document.getElementById('raw_text').value,
        prev_text: document.getElementById('prev_text').value
      };

      try {
        setTimeout(() => {
          chips.ext.className = 'agent-chip done';
          ['rev', 'risk', 'out', 'comp'].forEach(k => chips[k].className = 'agent-chip active');
        }, 500);

        setTimeout(() => {
          ['rev', 'risk', 'out', 'comp'].forEach(k => chips[k].className = 'agent-chip done');
          chips.edit.className = 'agent-chip active';
        }, 1100);

        const res = await fetch('/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await res.json();
        chips.edit.className = 'agent-chip done';

        if (data.status === 'ok') {
          document.getElementById('noteOutput').innerHTML = marked.parse(data.analyst_note);
          if (data.figures) {
            document.getElementById('kpiDeck').style.display = 'grid';
            document.getElementById('valRev').textContent = data.figures.revenue ? '$' + data.figures.revenue.value + 'M' : 'N/A';
            document.getElementById('valGrowth').textContent = data.figures.yoy_growth ? data.figures.yoy_growth.value + '%' : 'N/A';
            document.getElementById('valMargin').textContent = data.figures.gross_margin ? data.figures.gross_margin.value + '%' : 'N/A';
            document.getElementById('valOpMargin').textContent = data.figures.operating_margin ? data.figures.operating_margin.value + '%' : 'N/A';
          }
          if (data.trace_count) {
            document.getElementById('traceCounter').textContent = data.trace_count + ' TRACE EVENTS LOGGED';
          }
        } else {
          document.getElementById('noteOutput').innerHTML = '<div style="color:#ef4444; padding:1rem;">Error: ' + data.error + '</div>';
        }
      } catch (err) {
        document.getElementById('noteOutput').innerHTML = '<div style="color:#ef4444; padding:1rem;">Network Error: ' + err.message + '</div>';
      } finally {
        submitBtn.disabled = false;
        spinner.style.display = 'none';
        btnText.textContent = '🚀 Execute 6-Agent Synthesis';
      }
    });

    window.addEventListener('DOMContentLoaded', () => {
      loadSampleReport();
      loadSamplePrevReport();
      testGroqLive();
    });
  </script>
</body>
</html>
"""

class AnalysisRequest(BaseModel):
    company_name: str = "Apex Technologies Inc."
    quarter_label: str = "Q3 FY2024"
    raw_text: Optional[str] = None
    prev_text: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=HTML_TEMPLATE)

@app.get("/sample/current")
def get_sample_current():
    if SAMPLE_Q3.exists():
        return SAMPLE_Q3.read_text(encoding="utf-8")
    return ""

@app.get("/sample/previous")
def get_sample_previous():
    if SAMPLE_Q2.exists():
        return SAMPLE_Q2.read_text(encoding="utf-8")
    return ""

@app.get("/api/groq-status")
def get_groq_status():
    api_key = os.getenv("GROQ_API_KEY", "")
    masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "None"
    model = os.getenv("GROQ_MODEL_NAME", "qwen/qwen3.8-27b")
    
    sample_text = "N/A"
    try:
        sample_text = llm_client.query_groq("Provide a 5-word confirmation that Groq LLM is online.")
    except Exception as e:
        sample_text = f"Error: {e}"

    return {
        "status": "Online and Validated" if not sample_text.startswith("Error") else "Degraded",
        "model": model,
        "key_masked": masked,
        "sample_response": sample_text
    }

@app.post("/analyze")
async def analyze(req: AnalysisRequest):
    try:
        if not req.raw_text or not req.raw_text.strip():
            return JSONResponse({"status": "error", "error": "No input report text provided."})

        source_text = req.raw_text.strip()
        company_name = req.company_name or "Apex Technologies Inc."
        quarter_label = req.quarter_label or "Q3 FY2024"

        memory = SharedMemory()
        memory.raw_text = source_text
        memory.record("Manager", "PIPELINE_START", f"{company_name} / {quarter_label}")

        # Step 1: Extraction
        ext_agent = ExtractionAgent(memory)
        figures = ext_agent.run()

        # Previous quarter
        if req.prev_text and req.prev_text.strip():
            prev_mem = SharedMemory()
            prev_mem.raw_text = req.prev_text.strip()
            prev_agent = ExtractionAgent(prev_mem)
            memory.previous_figures = prev_agent.run()
        else:
            memory.previous_figures = make_previous_quarter_figures(figures, -7.0)

        # Step 2: Fan-out
        rev_agent = RevenueAnalyst(memory)
        rev_agent.run()

        risk_agent = RiskAnalyst(memory)
        risk_agent.run()

        out_agent = OutlookAnalyst(memory)
        out_agent.run()

        comp_agent = ComparisonAgent(memory)
        comp_agent.run()

        # Step 3: Fan-in
        editor = EditorManager(memory, company_name=company_name, quarter_label=quarter_label)
        final_note = editor.run()

        # Save output copy
        try:
            Path("analyst_note.md").write_text(final_note, encoding="utf-8")
        except Exception:
            pass

        return JSONResponse({
            "status": "ok",
            "analyst_note": final_note,
            "figures": figures,
            "trace_count": len(memory.agent_trace)
        })

    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting FERAD Portal on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
