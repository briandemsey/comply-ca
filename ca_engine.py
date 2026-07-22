#!/usr/bin/env python3
"""COMPLY-CA measurement engine.

Pipeline: ingest -> chunk (provisions) -> measure (Claude API judge)
          -> score against CA tiers -> generate revision -> report.

Uses Claude API for intelligent judgment instead of keyword heuristics.
Falls back to cue-based matching if ANTHROPIC_API_KEY is not set.
"""
import html as _html
import json
import os
import re
import tempfile

from ca_rubric import build_rubric, MODULES

# ── Anthropic policy benchmark text (fetched from published policy) ─────────
ANTHROPIC_POLICY = """
Anthropic's usage policies and responsible AI principles address the following areas:

GOVERNANCE: Anthropic maintains a Responsible Scaling Policy (RSP) requiring safety
evaluations before deploying more capable models. An Acceptable Use Policy governs all
API use. Regular safety reviews are conducted by internal and external teams. Named
responsible AI roles exist across safety, policy, and trust teams.

DATA PRIVACY: User data is not used to train models without explicit consent. Data
retention periods are defined. Security controls include encryption at rest and in
transit. Anthropic follows GDPR, CCPA, and other applicable privacy laws. Vendor
agreements include data processing addenda.

TRANSPARENCY: Anthropic publishes model cards and system prompt disclosure norms.
Claude identifies itself as an AI when sincerely asked. Usage policies are publicly
available. Anthropic publishes research on AI capabilities and safety.

HUMAN REVIEW: High-stakes decisions involving AI outputs should include human review.
Anthropic builds override mechanisms into Claude's design. Users retain authority to
accept, reject, or modify AI outputs. Claude is designed not to encourage over-reliance.

ACADEMIC INTEGRITY: Claude is designed to help users learn rather than do work for them.
When asked to write academic work, Claude flags that disclosure to instructors may be
required. AI assistance should be disclosed consistent with applicable policies.

SAFETY: Claude refuses requests for harmful content including self-harm facilitation,
harassment, and illegal activity. Safety mitigations are layered across training, RLHF,
and system-level controls. Incident response processes address safety failures.

EQUITY: Anthropic actively evaluates models for discriminatory outputs. Bias testing
is part of model evaluation. Anthropic's Acceptable Use Policy prohibits use of Claude
to discriminate based on protected characteristics.

VENDOR MANAGEMENT: Anthropic's API terms include data processing agreements, audit
rights, and use restrictions. Operators must agree to usage policies before API access.
Anthropic evaluates third-party use cases for safety and policy compliance.

PROFESSIONAL DEVELOPMENT: Anthropic publishes educational resources on responsible AI
use including model cards, usage policies, and interpretability research. Anthropic
encourages organizations to train staff on AI limitations and appropriate use.
"""


# ── Layer 1: ingest + chunk ──────────────────────────────────────────────────
def parse_document(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md"):
        return open(path, encoding="utf-8").read()
    if ext == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                return "\n".join((p.extract_text() or "") for p in pdf.pages)
        except Exception as e:
            raise RuntimeError(f"PDF parse needs pdfplumber: {e}")
    if ext == ".docx":
        try:
            from docx import Document
            return "\n".join(p.text for p in Document(path).paragraphs)
        except Exception as e:
            raise RuntimeError(f"DOCX parse needs python-docx: {e}")
    raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text: str) -> list[dict]:
    """Split policy text into addressable provisions by heading/paragraph."""
    provisions = []
    heading = "(preamble)"
    buf = []

    def flush():
        t = " ".join(buf).strip()
        if t:
            provisions.append({"heading": heading, "text": t})

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush(); buf = []; continue
        if (len(line) < 100 and (
            line.isupper() or
            re.match(r'^(section|policy|article|part|chapter)\b', line, re.I) or
            re.match(r'^([A-Z]{1,4}[-.]?\d+\.?\d*\.?\s)', line) or
            re.match(r'^(\d+(\.\d+)*\.?\s+\S)', line)
        )):
            flush(); buf = []; heading = line; continue
        buf.append(line)
    flush()
    return provisions


# ── Layer 2: measure ─────────────────────────────────────────────────────────
def _group_hit(text: str, group: list[str]) -> bool:
    def norm(s):
        return s.lower().replace("-", " ").replace("  ", " ")
    t = norm(text)
    return any(norm(term) in t for term in group)


def judge_cue(crit: dict, provisions: list[dict]) -> dict:
    """Cue-based fallback judge — same logic as comply-co."""
    cues = crit.get("cues", [])
    labels = crit.get("gap_labels", [])
    if not cues:
        return {"status": "n/a", "evidence": None, "gap": []}
    anchor = cues[0]
    relevant = [p for p in provisions if _group_hit(p["text"], anchor)]
    if not relevant:
        return {"status": "Not addressed", "evidence": None, "gap": labels[:]}
    met = [any(_group_hit(p["text"], g) for p in relevant) for g in cues]
    best = max(relevant, key=lambda p: sum(1 for g in cues if _group_hit(p["text"], g)))
    gap = [labels[i] if i < len(labels) else f'"{cues[i][0]}"' for i, ok in enumerate(met) if not ok]
    status = "Addressed" if all(met) else "Partial"
    return {"status": status, "evidence": {"heading": best["heading"], "text": best["text"]}, "gap": gap}


def judge_claude(crit: dict, provisions: list[dict], client) -> dict:
    """Claude API judge — reads policy provisions and scores against criterion."""
    if not provisions:
        return {"status": "Not addressed", "evidence": None, "gap": crit.get("gap_labels", [])}

    # Build context from the most relevant provisions (first 8000 chars to stay within limits)
    policy_text = "\n\n".join(
        f"[{p['heading']}]\n{p['text']}" for p in provisions
    )[:8000]

    prompt = f"""You are a California school policy compliance auditor.

CRITERION: {crit['id']} — {crit['term']}
HOOK: {crit['hook']}
PASS CONDITION: {crit['pass_condition']}

POLICY TEXT:
{policy_text}

Evaluate whether this policy text satisfies the pass condition above.
Respond with ONLY a JSON object in this exact format:
{{
  "status": "Addressed" | "Partial" | "Not addressed",
  "evidence_heading": "the heading of the most relevant provision, or null",
  "evidence_text": "the most relevant passage from the policy (max 300 chars), or null",
  "gap": ["short phrase describing what is missing", ...]
}}

Rules:
- "Addressed" = policy clearly satisfies the pass condition
- "Partial" = policy touches the topic but misses required elements
- "Not addressed" = policy has nothing relevant
- gap list is empty if status is "Addressed"
- Only cite evidence that actually exists in the policy text above"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        evidence = None
        if data.get("evidence_text"):
            evidence = {
                "heading": data.get("evidence_heading") or "(policy text)",
                "text": data["evidence_text"],
            }
        return {
            "status": data.get("status", "Not addressed"),
            "evidence": evidence,
            "gap": data.get("gap", []),
        }
    except Exception:
        # Fall back to cue-based on any error
        return judge_cue(crit, provisions)


def compare_to_anthropic(crit: dict, amended_text: str, client) -> str:
    """Compare amended policy language to Anthropic's published policy on the same domain."""
    module_name = MODULES.get(crit["module"], crit["module"])

    prompt = f"""You are comparing a California school district's AI policy to Anthropic's published usage and safety policies.

DOMAIN: {module_name}
CRITERION: {crit['term']}

DISTRICT POLICY LANGUAGE (amended):
{amended_text[:2000]}

ANTHROPIC'S POLICY APPROACH:
{ANTHROPIC_POLICY}

In 2-3 sentences, describe:
1. Where the district's approach aligns with Anthropic's
2. Where Anthropic's approach could strengthen the district's language
Be specific and practical. No preamble."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception:
        return "Anthropic comparison unavailable — check API key."


def judge(crit: dict, provisions: list[dict], client=None) -> dict:
    """Route to Claude judge or cue fallback."""
    if client is not None:
        return judge_claude(crit, provisions, client)
    return judge_cue(crit, provisions)


# ── Layer 3: score ───────────────────────────────────────────────────────────
def score(results: list[dict]) -> dict:
    measured = [r for r in results if not r["context_only"]]
    must = [r for r in measured if r["must_pass"]]
    passed = [r for r in must if r["measured"]["status"] == "Addressed"]
    failing = [r for r in must if r["measured"]["status"] != "Addressed"]
    by_tier = {}
    for r in measured:
        t = r["ag_test_tier"]
        d = by_tier.setdefault(t, {"total": 0, "addressed": 0})
        d["total"] += 1
        d["addressed"] += (r["measured"]["status"] == "Addressed")
    return {
        "within_ca_threshold": len(failing) == 0,
        "must_pass_total": len(must),
        "must_pass_addressed": len(passed),
        "failing": [r["id"] for r in failing],
        "by_tier": by_tier,
    }


# ── Orchestration ────────────────────────────────────────────────────────────
def _get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        return None


def run(policy_path: str) -> dict:
    rubric = build_rubric()
    provisions = chunk_text(parse_document(policy_path))
    client = _get_client()
    results = []
    for c in rubric:
        row = {k: c[k] for k in ("id", "module", "module_name", "term", "hook",
                                  "ag_test_tier", "pass_semantics", "must_pass", "context_only")}
        row["context_only"] = False
        row["pass_condition"] = c.get("pass_condition", "")
        row["revision"] = c.get("revision", "")
        m = judge(c, provisions, client)
        row["measured"] = m
        if m["status"] != "Addressed":
            rem = judge(c, [{"heading": "Proposed revision", "text": c["revision"]}], client)
            row["remeasured"] = rem["status"]
        results.append(row)
    return {"provisions": len(provisions), "score": score(results), "results": results}


def measure_text(text: str) -> dict:
    """Run rubric against raw text (used by single-policy Load & Amend flow)."""
    rubric = build_rubric()
    provisions = chunk_text(text)
    client = _get_client()
    results = []
    for c in rubric:
        row = {k: c[k] for k in ("id", "module", "module_name", "term", "hook",
                                  "ag_test_tier", "pass_semantics", "must_pass", "context_only")}
        row["context_only"] = False
        row["pass_condition"] = c.get("pass_condition", "")
        row["revision"] = c.get("revision", "")
        m = judge(c, provisions, client)
        row["measured"] = m
        if m["status"] != "Addressed":
            rem = judge(c, [{"heading": "Proposed revision", "text": c["revision"]}], client)
            row["remeasured"] = rem["status"]
        results.append(row)
    return {"provisions": len(provisions), "score": score(results), "results": results}


def render_html(report: dict, district: str = "Sample District") -> str:
    s = report["score"]
    ok = s["within_ca_threshold"]

    def esc(x):
        return _html.escape(str(x or ""))

    badge = {"Statutory": "#8a2f2f", "Enacted": "#2f6b3d", "Guidance": "#8a6d1a"}
    stbg = {"Addressed": "#e4f3e8", "Partial": "#fff3d6", "Not addressed": "#f7dede"}
    stfg = {"Addressed": "#2f6b3d", "Partial": "#8a6d1a", "Not addressed": "#8a2f2f"}

    rows = ""
    cur_mod = None
    for r in report["results"]:
        if r["module"] != cur_mod:
            cur_mod = r["module"]
            rows += f'<h2>{esc(r["module"])} — {esc(r["module_name"])}</h2>'
        m = r["measured"]
        st = m["status"]
        ev = (f'<div class="ev"><span class="evh">{esc(m["evidence"]["heading"])}</span> '
              f'"{esc(m["evidence"]["text"])}"</div>') if m["evidence"] else \
             '<div class="ev none">No matching provision found.</div>'
        gap = ('<div class="gap"><b>Gap:</b> missing ' + esc("; ".join(m["gap"])) + '.</div>') \
            if m["gap"] else '<div class="gap ok">Fully satisfied.</div>'
        rev = (f'<div class="rev"><b>Suggested language</b> (re-measured: {esc(r.get("remeasured",""))}) '
               f'— "{esc(r.get("revision",""))}"</div>') if st != "Addressed" else ""
        rows += (
            f'<div class="crit">'
            f'<div class="top"><span class="id">{esc(r["id"])} · {esc(r["term"])}</span>'
            f'<span class="tier" style="color:{badge.get(r["ag_test_tier"],"#333")}">'
            f'{esc(r["ag_test_tier"])}</span></div>'
            f'<div class="hook">{esc(r["hook"])} · <i>{esc(r["pass_semantics"])}</i></div>'
            f'<div class="status" style="background:{stbg.get(st,"#eee")};color:{stfg.get(st,"#333")}">'
            f'Measured: {esc(st)}</div>'
            f'{ev}{gap}{rev}</div>'
        )

    tiers = "".join(
        f'<span class="tstat">{esc(t)}: {d["addressed"]}/{d["total"]}</span>'
        for t, d in s["by_tier"].items()
    )
    verdict = ('<span class="ok">Within the CA compliance threshold on all must-pass requirements.</span>'
               if ok else
               f'<span class="no">Not yet within the CA compliance threshold — '
               f'{len(s["failing"])} must-pass requirements unmet.</span>')

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>COMPLY-CA Measurement Report</title>
<style>
body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1c2431;max-width:960px;margin:24px auto;padding:0 18px;line-height:1.45}}
h1{{color:#003DA5;margin-bottom:2px}}h2{{color:#003DA5;border-bottom:2px solid #e7ecf2;padding-bottom:4px;margin-top:28px}}
.sub{{color:#5b6b7f;margin-top:0}}
.summary{{border:1px solid #d7dee8;border-radius:10px;padding:16px 18px;margin:16px 0;background:#f8fafc}}
.summary .v{{font-size:18px;font-weight:700;margin-bottom:6px}}
.ok{{color:#2f6b3d}}.no{{color:#8a2f2f}}
.tstat{{display:inline-block;background:#eef4fb;border:1px solid #cfe0f2;border-radius:20px;padding:3px 10px;margin:4px 6px 0 0;font-size:12.5px;color:#003DA5}}
.crit{{border:1px solid #e2e8f0;border-radius:9px;padding:13px 15px;margin:11px 0}}
.top{{display:flex;justify-content:space-between;gap:10px}}
.id{{font-weight:700;color:#003DA5}}.tier{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.03em}}
.hook{{font-size:11.5px;color:#5b6b7f;font-family:ui-monospace,Menlo,monospace;margin:2px 0 8px}}
.status{{display:inline-block;font-weight:700;font-size:12.5px;padding:3px 10px;border-radius:5px;margin-bottom:8px}}
.ev{{font-size:13px;background:#f6f9fc;border-left:3px solid #cfe0f2;padding:8px 12px;margin:6px 0;border-radius:4px}}
.ev.none{{color:#8a2f2f;border-left-color:#e6b7b7}}.evh{{font-weight:700;color:#003DA5}}
.gap{{font-size:13px;color:#8a2f2f;margin:6px 0}}.gap.ok{{color:#2f6b3d}}
.rev{{font-size:13px;background:#eef4fb;border:1px solid #cfe0f2;border-radius:6px;padding:9px 12px;margin-top:8px;color:#003DA5}}
.note{{font-size:12px;color:#5b6b7f;border-top:1px solid #e7ecf2;margin-top:26px;padding-top:12px}}
</style></head>
<body>
<h1>COMPLY-CA — Measurement Report</h1>
<p class="sub">{esc(district)} · measured against SB 1288 / AB 2225 / CDE Model Policy · {report['provisions']} provisions examined</p>
<div class="summary">
<div class="v">{verdict}</div>
<div>Must-pass requirements addressed: <b>{s['must_pass_addressed']}/{s['must_pass_total']}</b></div>
<div style="margin-top:6px">{tiers}</div>
</div>
{rows}
<div class="note">Measured by COMPLY-CA (H-EDU.Solutions) against SB 1288, AB 2225, and the CDE Model AI Policy.
Statutory items directly implement enacted law. Enacted items reflect CDE compliance standards.
Guidance items reflect best practice. Not legal advice — consult district legal counsel before board action.</div>
</body></html>"""
