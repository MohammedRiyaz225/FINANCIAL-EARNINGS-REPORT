"""
outlook_analyst.py
==================
Agent 4 – Outlook Analyst
Role  : Assesses the company's forward guidance, growth catalysts, and
        management commentary about the future.

Tools
-----
1. extract_guidance_statements() – finds forward-looking sentences by
                                   tense / modal verb patterns and
                                   cross-references guidance KPIs.
2. assess_guidance_quality()     – rates the quality and reliability of
                                   guidance (specificity, revision history,
                                   bull/bear balance) and formats the section.
"""

import re
from typing import Any, Dict, List, Tuple
from shared_memory import SharedMemory


# ══════════════════════════════════════════════════════════════
# Tool 1 – Extract forward-looking statements
# ══════════════════════════════════════════════════════════════

# Patterns that indicate a forward-looking statement
_FORWARD_PATTERNS = [
    r"\bwill\b", r"\bexpect[s]?\b", r"\bforecast[s]?\b", r"\bguidance\b",
    r"\boutlook\b", r"\banticipate[s]?\b", r"\bproject[s]?\b",
    r"\btarget[s]?\b", r"\baim[s]?\b", r"\bplan[s]? to\b",
    r"\bnext quarter\b", r"\bnext fiscal\b", r"\bfull.year\b",
    r"\bfuture\b", r"\bgoing forward\b", r"\bdriv(?:e|es|ing)\b",
    r"\bgrowth opportunity\b", r"\binvestment\b",
]

# Positive catalysts vs. cautious language
_POSITIVE_SIGNALS = [
    r"strong demand", r"accelerat", r"expand", r"new product", r"launch",
    r"win", r"record", r"momentum", r"opportunity", r"pipeline",
    r"partnership", r"market share gain",
]
_CAUTIOUS_SIGNALS = [
    r"uncertain", r"cautious", r"headwind", r"slower", r"challenging",
    r"difficult", r"below.*expect", r"lower.*guidance",
    r"cut.*forecast", r"reduce.*outlook",
]


def extract_guidance_statements(text: str, figures: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool 1 – Extract forward-looking sentences and guidance KPIs.

    Returns
    -------
    dict with:
        forward_sentences : list of relevant forward-looking sentences
        guidance_revenue  : guidance revenue KPI (if extracted)
        guidance_eps      : guidance EPS KPI (if extracted)
        positive_count    : number of bullish signals
        cautious_count    : number of cautious signals
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    forward_sentences: List[str] = []

    for sent in sentences:
        if any(re.search(p, sent, re.IGNORECASE) for p in _FORWARD_PATTERNS):
            forward_sentences.append(sent.strip())

    # Deduplicate while preserving order
    seen: set = set()
    unique_fwd: List[str] = []
    for s in forward_sentences:
        key = s[:80]
        if key not in seen:
            seen.add(key)
            unique_fwd.append(s)

    # Count sentiment signals
    all_fwd_text = " ".join(unique_fwd).lower()
    positive_count = sum(
        1 for p in _POSITIVE_SIGNALS if re.search(p, all_fwd_text, re.IGNORECASE)
    )
    cautious_count = sum(
        1 for p in _CAUTIOUS_SIGNALS if re.search(p, all_fwd_text, re.IGNORECASE)
    )

    return {
        "forward_sentences": unique_fwd[:12],       # top 12 most relevant
        "guidance_revenue":  figures.get("guidance_revenue"),
        "guidance_eps":      figures.get("guidance_eps"),
        "positive_count":    positive_count,
        "cautious_count":    cautious_count,
    }


# ══════════════════════════════════════════════════════════════
# Tool 2 – Assess guidance quality and format the section
# ══════════════════════════════════════════════════════════════

def assess_guidance_quality(guidance_data: Dict[str, Any]) -> str:
    """
    Tool 2 – Evaluate guidance specificity, tone balance, and produce
    a formatted, sourced Outlook section.
    """
    lines = ["## Outlook & Forward Guidance", ""]

    fwd_sents = guidance_data.get("forward_sentences", [])
    g_rev     = guidance_data.get("guidance_revenue")
    g_eps     = guidance_data.get("guidance_eps")
    pos_cnt   = guidance_data.get("positive_count", 0)
    caut_cnt  = guidance_data.get("cautious_count", 0)

    # Quantitative guidance
    if g_rev or g_eps:
        lines.append("**Quantitative Guidance Provided:**")
        if g_rev:
            lines.append(
                f"  - Revenue Guidance: ${g_rev['value']:,.1f} {g_rev.get('unit', 'M USD')}"
            )
            lines.append(f"    > *Source:* \"{g_rev.get('source', '')[:150]}\"")
        if g_eps:
            lines.append(f"  - EPS Guidance: ${g_eps['value']:.2f}")
            lines.append(f"    > *Source:* \"{g_eps.get('source', '')[:150]}\"")
        lines.append("")
        specificity = "HIGH – Quantitative targets provided."
    else:
        specificity = "LOW – No specific numerical guidance found."

    lines.append(f"**Guidance Specificity:** {specificity}")
    lines.append("")

    # Management tone
    total_signals = pos_cnt + caut_cnt
    if total_signals == 0:
        tone = "NEUTRAL – Insufficient forward-looking language."
    elif pos_cnt > caut_cnt * 1.5:
        tone = f"🟢 BULLISH – {pos_cnt} positive vs. {caut_cnt} cautious signals."
    elif caut_cnt > pos_cnt * 1.5:
        tone = f"🔴 CAUTIOUS – {caut_cnt} cautious vs. {pos_cnt} positive signals."
    else:
        tone = f"🟡 MIXED – {pos_cnt} positive and {caut_cnt} cautious signals."

    lines.append(f"**Management Tone:** {tone}")
    lines.append("")

    # Key forward-looking statements (verbatim citations)
    if fwd_sents:
        lines.append("**Key Forward-Looking Statements:**")
        lines.append("")
        for i, sent in enumerate(fwd_sents[:6], 1):   # show top 6
            lines.append(f"{i}. \"{sent[:200]}\"")
        lines.append("")

    # Overall outlook rating
    if pos_cnt >= 3 and caut_cnt <= 1:
        rating = "POSITIVE OUTLOOK 🟢"
    elif caut_cnt >= 3:
        rating = "CAUTIOUS OUTLOOK 🔴"
    else:
        rating = "NEUTRAL / MIXED OUTLOOK 🟡"

    lines.append(f"**Outlook Rating:** {rating}")
    lines.append("")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# Agent class
# ══════════════════════════════════════════════════════════════

class OutlookAnalyst:
    NAME = "Outlook Analyst"

    def __init__(self, memory: SharedMemory) -> None:
        self.memory = memory

    def run(self) -> str:
        mem = self.memory
        mem.record(self.NAME, "START", "Extracting forward-looking statements")

        if not mem.raw_text:
            raise ValueError("SharedMemory.raw_text is empty.")

        # ── Tool 1 ──────────────────────────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "extract_guidance_statements")
        guidance_data = extract_guidance_statements(mem.raw_text, mem.current_figures)
        mem.record(
            self.NAME, "TOOL_RESULT",
            f"{len(guidance_data['forward_sentences'])} forward-looking sentences found; "
            f"pos={guidance_data['positive_count']}, caut={guidance_data['cautious_count']}"
        )

        # ── Tool 2 ──────────────────────────────────────────────────────────
        mem.record(self.NAME, "CALL_TOOL", "assess_guidance_quality")
        section = assess_guidance_quality(guidance_data)
        mem.record(self.NAME, "TOOL_RESULT", f"Outlook section: {len(section)} chars")

        mem.outlook_analysis = section
        mem.record(self.NAME, "WRITE_MEMORY", "outlook_analysis")
        mem.record(self.NAME, "END", "Outlook analysis complete")

        return section
