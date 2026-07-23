"""COMPLY-CA — California AI Policy Compliance Platform.

Upload -> Initial Report (per-policy scoreboard) -> Policy Detail
(examine, gap, amended language, CA law rationale, Anthropic benchmark)
-> Compliance Overview (domain rollup) -> Gap Analysis & Revision export.

Anchors: SB 1288 | AB 2225 | CDE Model Policy (26 Principles)
         SOPIPA | AB 1584 | Ed Code 49073.1 | FERPA | COPPA | IDEA
         Title VI | Title IX | SB 243 | AB 2013 | CPPA ADMT regs
"""
from __future__ import annotations

import io
import os
import re
import tempfile
from pathlib import Path

import streamlit as st

from ca_engine import (
    chunk_text, compare_to_anthropic, judge, measure_text,
    parse_document, render_html, run, score, _get_client,
)
from ca_rubric import build_rubric, MODULES

HERE = Path(__file__).parent
LOGO = HERE / "assets" / "csba_logo.png"
DISTRICTS_DIR = HERE / "districts"

MODULE_ORDER = list(MODULES.keys())

# ── brand colours ────────────────────────────────────────────────────────────
NAVY   = "#003DA5"
NAVY2  = "#001F5B"
RAIL   = "#F0F4FA"
LINE   = "#d7dee8"
INK    = "#1c2431"
MUTED  = "#546E7A"
STAT   = "#2f6b3d"   # Statutory / Addressed
ENACT  = "#003DA5"   # Enacted
GUID   = "#8a6d1a"   # Guidance / Partial
CONT   = "#8a2f2f"   # Not addressed
STATBG = "#e4f3e8"
GUIDBG = "#fff3d6"
CONTBG = "#f7dede"


def _render_header() -> None:
    left, right = st.columns([3, 2])
    with left:
        if LOGO.exists():
            st.image(str(LOGO), width=420)
    with right:
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;align-items:center;'
            f'height:100%;padding-top:24px">'
            f'<span style="display:inline-block;font-size:12px;font-weight:700;'
            f'background:{CONTBG};color:{CONT};border:1px solid #e6b7b7;'
            f'padding:6px 12px;border-radius:6px;text-transform:uppercase;letter-spacing:.04em">'
            f'Prototype for CSBA review — not an official CSBA product'
            f'</span></div>',
            unsafe_allow_html=True,
        )


def inject_css() -> None:
    st.markdown(f"""
    <style>
    .block-container {{padding-top:1.2rem;padding-bottom:3rem;max-width:1100px;}}
    [data-testid="stSidebar"] {{background:{RAIL};border-right:1px solid {LINE};}}
    [data-testid="stSidebar"] .stButton>button {{
        width:100%;text-align:left;background:{NAVY};color:#fff;
        border:none;border-radius:6px;padding:9px 12px;margin-bottom:6px;font-size:13px;
    }}
    h1{{color:{NAVY};font-size:27px;margin:4px 0;}}
    h2,h3{{color:{NAVY};}}
    .sub{{color:{MUTED};margin:0 0 18px;}}
    .pill{{display:inline-block;font-size:11px;padding:3px 9px;border-radius:20px;
        background:{GUIDBG};color:{GUID};border:1px solid #e6cf93;margin-bottom:14px;}}
    .brand{{color:{NAVY};font-weight:700;font-size:19px;text-align:center;}}
    .brand small{{display:block;color:{MUTED};font-weight:500;font-size:12px;margin-top:3px;}}
    .tile{{border:1.5px solid {NAVY};border-radius:9px;padding:14px 16px;background:#fff;text-align:center;}}
    .tile .n{{font-size:30px;font-weight:700;color:{NAVY};}}
    .tile .lbl{{font-size:12px;color:{MUTED};text-transform:uppercase;letter-spacing:.05em;}}
    .badge{{font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:4px;
        text-transform:uppercase;letter-spacing:.03em;}}
    .b-Statutory{{background:{CONTBG};color:{CONT};}}
    .b-Enacted{{background:{STATBG};color:{STAT};}}
    .b-Guidance{{background:{GUIDBG};color:{GUID};}}
    .b-Addressed{{background:{STATBG};color:{STAT};}}
    .b-Partial{{background:{GUIDBG};color:{GUID};}}
    .b-NotAddressed{{background:{CONTBG};color:{CONT};}}
    .b-High{{background:{CONTBG};color:{CONT};}}
    .b-Medium{{background:{GUIDBG};color:{GUID};}}
    .b-Low{{background:{STATBG};color:{STAT};}}
    .polcard{{border:1px solid {LINE};border-radius:8px;padding:12px 14px;margin-bottom:10px;background:#fff;}}
    .polcard .code{{font-family:ui-monospace,Menlo,monospace;font-weight:700;color:{NAVY};}}
    .polcard .rat{{font-size:12.5px;color:#33414f;margin-top:4px;}}
    .polcard .mods{{font-size:11.5px;color:{MUTED};margin-top:4px;}}
    .ev{{background:#f6f9fc;border-left:3px solid #cfe0f2;padding:10px 14px;margin:8px 0;border-radius:4px;font-size:13px;}}
    .rev{{background:#eef4fb;border:1px solid #cfe0f2;border-radius:6px;padding:10px 14px;margin:8px 0;color:{NAVY};font-size:13px;}}
    .model{{background:#eef4fb;border:1px solid #cfe0f2;border-radius:8px;padding:14px;color:{NAVY2};font-size:14px;line-height:1.5;margin:6px 0 18px;}}
    .anthropic{{background:#f5f0ff;border:1px solid #c8b8f0;border-radius:8px;padding:14px;color:#3d2b7a;font-size:13px;line-height:1.5;margin:6px 0 18px;}}
    .anthropic .lbl{{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#7a5bbf;font-weight:700;margin-bottom:6px;}}
    .verdict-ok{{background:{STATBG};color:{STAT};padding:12px 16px;border-radius:8px;font-weight:700;margin:10px 0;}}
    .verdict-no{{background:{CONTBG};color:{CONT};padding:12px 16px;border-radius:8px;font-weight:700;margin:10px 0;}}
    .note{{font-size:12px;color:{MUTED};margin-top:22px;border-top:1px solid {LINE};padding-top:12px;}}
    </style>
    """, unsafe_allow_html=True)


# ── state ────────────────────────────────────────────────────────────────────
def init_state() -> None:
    ss = st.session_state
    ss.setdefault("view", "load_amend")
    ss.setdefault("district_name", "")
    ss.setdefault("district_source", "")
    ss.setdefault("report", None)
    ss.setdefault("report_amended", None)
    ss.setdefault("la_policy_text", None)
    ss.setdefault("la_policy_name", None)
    ss.setdefault("la_policy_code", None)
    ss.setdefault("la_report", None)
    ss.setdefault("la_report_amended", None)
    ss.setdefault("la_amended_text", None)
    ss.setdefault("la_step", 1)
    ss.setdefault("show_amended", False)
    ss.setdefault("scope_confirmed", {})
    ss.setdefault("selected_policy", None)
    ss.setdefault("anthropic_comparisons", {})
    ss.setdefault("district_library", {})
    ss.setdefault("active_district", "")
    ss.setdefault("_districts_preloaded", False)
    ss.setdefault("manual_text", None)         # full text of uploaded manual
    ss.setdefault("policies", None)            # {code: {title, report}} per-policy
    ss.setdefault("district_policies", {})     # district_label -> policies dict
    ss.setdefault("selected_policy_code", None)  # code clicked in per-policy report
    ss.setdefault("benchmark_results", {})     # {criterion_id: comparison text}
    if not ss._districts_preloaded:
        _preload_districts(ss)
        ss._districts_preloaded = True


def run_text(text: str) -> dict:
    """Run the CA compliance engine on a raw text string."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write(text)
        path = tmp.name
    try:
        return run(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _pretty_district(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def _preload_districts(ss) -> None:
    """Load pre-computed district reports from districts/<slug>/<slug>_report.json."""
    if not DISTRICTS_DIR.exists():
        return
    for district_dir in sorted(DISTRICTS_DIR.iterdir(), reverse=True):
        if not district_dir.is_dir():
            continue
        slug = district_dir.name
        label = _pretty_district(slug)
        if label in ss.district_library:
            continue
        report_file = district_dir / f"{slug}_report.json"
        if not report_file.exists():
            continue
        import json as _json
        report = _json.loads(report_file.read_text(encoding="utf-8"))
        ss.district_library[label] = report
        policies_file = district_dir / f"{slug}_policies.json"
        if policies_file.exists():
            ss.district_policies[label] = _json.loads(policies_file.read_text(encoding="utf-8"))
        # Store manual path for on-demand text extraction
        manual_file = district_dir / f"{slug}_manual.txt"
        if "district_manual_paths" not in ss:
            ss["district_manual_paths"] = {}
        if manual_file.exists():
            ss["district_manual_paths"][label] = str(manual_file)
        if not ss.active_district:
            ss.active_district = label
            ss.district_name = label
            ss.report = report
            ss.policies = ss.district_policies.get(label)


def _active_report() -> dict | None:
    ss = st.session_state
    if ss.report is not None:
        return ss.report_amended if (ss.show_amended and ss.report_amended) else ss.report
    if ss.la_report is not None:
        return ss.la_report_amended if (ss.show_amended and ss.la_report_amended) else ss.la_report
    return None


def _build_additions_block(gaps: list[dict]) -> str:
    if not gaps:
        return ""
    lines = ["", "---", "", "## Additions to satisfy California AI Policy Requirements", ""]
    by_module: dict[str, list] = {}
    for r in gaps:
        by_module.setdefault(r["module"], []).append(r)
    for m in MODULE_ORDER:
        if m not in by_module:
            continue
        lines.append(f"### {m} — {MODULES[m]}")
        lines.append("")
        for r in by_module[m]:
            lines.append(f"**[{r['id']} · {r['term']} · {r['ag_test_tier']} · {r['hook']}]**")
            lines.append("")
            lines.append(r.get("revision", ""))
            lines.append("")
    return "\n".join(lines)


def _ensure_amended() -> None:
    ss = st.session_state
    if ss.la_policy_text is not None and ss.la_report is None:
        with st.spinner("Measuring policy against CA criteria..."):
            ss.la_report = measure_text(ss.la_policy_text)
    if ss.la_report is not None and ss.la_report_amended is None and ss.la_policy_text is not None:
        gaps = [r for r in ss.la_report["results"] if r["measured"]["status"] != "Addressed"]
        additions = _build_additions_block(gaps)
        amended = ss.la_policy_text.rstrip() + "\n\n" + additions
        ss.la_amended_text = amended
        with st.spinner("Re-measuring amended policy..."):
            ss.la_report_amended = measure_text(amended)
    have_amended = (ss.la_report_amended is not None) or (ss.report_amended is not None)
    if have_amended and "_amend_toggle" not in ss and not ss.show_amended:
        ss.show_amended = True


def _render_amended_toggle() -> None:
    ss = st.session_state
    have_amended = (ss.la_report_amended is not None) or (ss.report_amended is not None)
    if not have_amended:
        return
    options = ["Original (before amendment)", "Amended (after generated additions)"]
    if "_amend_toggle" not in ss:
        ss["_amend_toggle"] = options[1 if ss.show_amended else 0]

    def _on_change():
        ss.show_amended = ss["_amend_toggle"].startswith("Amended")

    st.radio("Measurement view", options=options, horizontal=True,
             key="_amend_toggle", on_change=_on_change)


def _reset_load_amend() -> None:
    for k in ("la_policy_text", "la_policy_name", "la_policy_code",
              "la_report", "la_report_amended", "la_amended_text", "selected_policy"):
        st.session_state[k] = None
    st.session_state.la_step = 1
    st.session_state.show_amended = False
    if "_amend_toggle" in st.session_state:
        del st.session_state["_amend_toggle"]


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── sidebar ───────────────────────────────────────────────────────────────────
def sidebar() -> None:
    ss = st.session_state
    manual_loaded = _active_report() is not None or ss.la_policy_text is not None

    with st.sidebar:
        st.markdown(
            f'<div class="brand">COMPLY-CA<small>SB 1288 · AB 2225 · California</small></div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        if ss.district_library:
            district_options = list(ss.district_library.keys())
            active = ss.active_district if ss.active_district in district_options else district_options[0]
            chosen = st.selectbox("Switch district", district_options,
                index=district_options.index(active), key="district_switcher")
            if chosen != ss.active_district:
                ss.active_district = chosen
                ss.district_name = chosen
                ss.report = ss.district_library[chosen]
                ss.policies = ss.district_policies.get(chosen)
                ss.selected_policy_code = None
                ss.report_amended = None
                ss.show_amended = False
                if "_amend_toggle" in ss: del ss["_amend_toggle"]
                ss.view = "report"
                st.rerun()
        elif ss.district_name:
            st.caption(f"District: {ss.district_name}")
            st.markdown("---")

        for label, key in [("Load & Amend a Policy", "load_amend"),
                            ("Upload Manual", "upload")]:
            if st.button(label, key=f"nav_{key}"):
                ss.view = key

        st.markdown("---")
        st.markdown(
            f'<div style="font-size:11px;color:{MUTED};text-transform:uppercase;'
            f'letter-spacing:.05em;margin:6px 4px">Manual views</div>',
            unsafe_allow_html=True,
        )
        st.button("Initial Report",          key="nav_report",   disabled=not manual_loaded,
                  on_click=lambda: ss.__setitem__("view", "report"))
        st.button("Policy Detail",           key="nav_detail",   disabled=not (manual_loaded and (ss.selected_policy or ss.selected_policy_code)),
                  on_click=lambda: ss.__setitem__("view", "detail"))
        st.button("Compliance Overview",     key="nav_overview", disabled=not manual_loaded,
                  on_click=lambda: ss.__setitem__("view", "overview"))
        st.button("Gap Analysis & Revision", key="nav_gap",      disabled=not manual_loaded,
                  on_click=lambda: ss.__setitem__("view", "gap"))
        policy_loaded = bool(ss.selected_policy or ss.selected_policy_code)
        st.button("Benchmark Comparison",    key="nav_benchmark", disabled=not policy_loaded,
                  on_click=lambda: ss.__setitem__("view", "benchmark"))

        if not manual_loaded:
            st.caption("Load a manual to unlock these views.")

        st.markdown("---")
        st.caption(
            "Measured against SB 1288, AB 2225, and the CDE Model AI Policy. "
            "Statutory items are hard enacted requirements. Enacted items reflect "
            "CDE compliance standards. Guidance items are best practice. Not legal advice."
        )


# ── view: load & amend ────────────────────────────────────────────────────────
def view_load_amend() -> None:
    _render_header()
    st.markdown('<div class="pill">SB 1288 · AB 2225 · CDE Model Policy</div>', unsafe_allow_html=True)
    st.markdown("# Load & Amend a Policy")
    st.markdown(
        '<p class="sub">Single-policy workflow: <b>Load → Analyze → Amend (before/after) → Rationale</b>.<br>'
        'Work one policy end to end; Upload Manual runs the scoreboard across your full policy set.</p>',
        unsafe_allow_html=True,
    )

    steps = ["1. Load", "2. Analyze", "3. Amend", "4. Rationale"]
    cur = st.session_state.la_step
    cols = st.columns(4)
    for i, s in enumerate(steps, start=1):
        marker = "●" if i == cur else ("✓" if i < cur else "○")
        style = (f"color:{NAVY};font-weight:700" if i == cur else
                 (f"color:{STAT}" if i < cur else f"color:{MUTED}"))
        cols[i - 1].markdown(f'<div style="{style};font-size:14px">{marker} {s}</div>', unsafe_allow_html=True)
    st.markdown("---")

    # ── Step 1: Load ──
    if cur == 1:
        st.markdown("### Step 1 — Load a policy")
        ss = st.session_state
        # Show pre-loaded district policies if available
        if ss.get("policies") and ss.get("district_name"):
            st.markdown(f"**Policies on file for {ss.district_name}**")
            shown = 0
            for code, pd in ss.policies.items():
                s = pd["report"]["score"]
                ok = s["within_ca_threshold"]
                col_name, col_size, col_btn = st.columns([5, 2, 1])
                with col_name:
                    color = STAT if ok else CONT
                    st.markdown(
                        f'<span style="font-family:ui-monospace,Menlo,monospace;color:{color}">'
                        f'{code} — {pd["title"]}</span>',
                        unsafe_allow_html=True
                    )
                with col_size:
                    st.markdown(
                        f'<span style="color:{MUTED};font-size:13px">'
                        f'{s["must_pass_addressed"]}/{s["must_pass_total"]} must-pass</span>',
                        unsafe_allow_html=True
                    )
                with col_btn:
                    if st.button("Load", key=f"load_pol_{code}"):
                        ss.selected_policy_code = code
                        ss.view = "detail"
                        st.rerun()
                shown += 1
                if shown >= 10:
                    st.caption(f"… and {len(ss.policies) - 10} more. See Initial Report for the full list.")
                    break
            st.markdown("---")
        st.markdown("### Or upload your own single policy (PDF / DOCX / TXT / MD)")
        up = st.file_uploader("Single-policy upload", type=["pdf", "docx", "txt", "md"], key="la_upload")
        if up is not None:
            suffix = os.path.splitext(up.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(up.read())
                path = tmp.name
            try:
                text = parse_document(path)
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            st.session_state.la_policy_text = text
            st.session_state.la_policy_name = up.name
            code = os.path.splitext(up.name)[0]
            st.session_state.la_policy_code = code
            st.session_state.selected_policy = code
            st.session_state.district_source = f"Upload: {up.name}"
            st.session_state.la_step = 2
            st.rerun()
        return

    # Steps 2+ need a loaded policy
    if st.session_state.la_policy_text is None:
        st.warning("No policy loaded. Go back to Step 1.")
        if st.button("← Back to Load"):
            _reset_load_amend()
            st.rerun()
        return

    st.markdown(
        f"**Loaded:** `{st.session_state.la_policy_name}` &nbsp;·&nbsp; "
        f"{len(st.session_state.la_policy_text):,} characters",
        unsafe_allow_html=True,
    )
    if st.button("Load a different policy", key="la_change"):
        _reset_load_amend()
        st.rerun()
    st.markdown("")

    # ── Step 2: Analyze ──
    if cur == 2:
        st.markdown("### Step 2 — Analyze against California AI Policy Requirements")
        if st.session_state.la_report is None:
            with st.spinner("Measuring against CA rubric (44 criteria across 11 domains)..."):
                st.session_state.la_report = measure_text(st.session_state.la_policy_text)
        rep = st.session_state.la_report
        s = rep["score"]

        st.markdown(f"**Provisions found:** {rep['provisions']}")
        st.markdown(f"**Must-pass requirements addressed:** {s['must_pass_addressed']} of {s['must_pass_total']}")

        verdict = (
            '<div class="verdict-ok">Within the CA compliance threshold on all must-pass requirements.</div>'
            if s["within_ca_threshold"] else
            f'<div class="verdict-no">Not yet within the CA compliance threshold — '
            f'{len(s["failing"])} must-pass requirements unmet.</div>'
        )
        st.markdown(verdict, unsafe_allow_html=True)

        if st.session_state.la_report_amended is not None:
            s2 = st.session_state.la_report_amended["score"]
            st.markdown("**After amendment:**")
            st.markdown(
                f'<div class="verdict-ok">Amended: {s2["must_pass_addressed"]}/{s2["must_pass_total"]} must-pass addressed.</div>'
                if s2["within_ca_threshold"] else
                f'<div class="verdict-no">Amended still unmet on {len(s2["failing"])}: {", ".join(s2["failing"])}.</div>',
                unsafe_allow_html=True,
            )

        results = rep["results"]
        by_module: dict[str, list] = {}
        for r in results:
            by_module.setdefault(r["module"], []).append(r)
        for m in MODULE_ORDER:
            if m not in by_module:
                continue
            rows = by_module[m]
            addr = sum(1 for r in rows if r["measured"]["status"] == "Addressed")
            partial = sum(1 for r in rows if r["measured"]["status"] == "Partial")
            missing = sum(1 for r in rows if r["measured"]["status"] == "Not addressed")
            st.markdown(
                f'**{m} — {MODULES[m]}**  ·  '
                f'<span style="color:{STAT}">{addr} addressed</span>  ·  '
                f'<span style="color:{GUID}">{partial} partial</span>  ·  '
                f'<span style="color:{CONT}">{missing} missing</span>',
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="la_back_2"):
                st.session_state.la_step = 1; st.rerun()
        with col2:
            if st.button("Amend policy →", type="primary", key="la_next_2"):
                st.session_state.la_step = 3; st.rerun()
        return

    # ── Step 3: Amend ──
    if cur == 3:
        st.markdown("### Step 3 — Amend the policy")
        rep = st.session_state.la_report
        gaps = [r for r in rep["results"] if r["measured"]["status"] != "Addressed"]

        original = st.session_state.la_policy_text
        additions = _build_additions_block(gaps)
        amended = original.rstrip() + "\n\n" + additions

        if st.session_state.la_amended_text != amended:
            st.session_state.la_amended_text = amended
            st.session_state.la_report_amended = None

        st.caption(
            "**Before** is your policy as loaded. **After** splices in California-compliant language "
            "for each gap, tagged with the criterion ID and statutory hook it satisfies. "
            "This is the redline for attorney review."
        )

        col_b, col_a = st.columns(2)
        with col_b:
            st.markdown("**Before**")
            st.markdown(
                f'<div style="max-height:600px;overflow:auto;border:1px solid {LINE};'
                f'border-radius:6px;padding:12px;background:#fafbfd;font-size:12.5px;'
                f'white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace">'
                f'{_escape(original)}</div>',
                unsafe_allow_html=True,
            )
        with col_a:
            st.markdown("**After**")
            before_len = len(original.rstrip())
            st.markdown(
                f'<div style="max-height:600px;overflow:auto;border:1px solid {LINE};'
                f'border-radius:6px;padding:12px;background:#fafbfd;font-size:12.5px;'
                f'white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace">'
                f'{_escape(amended[:before_len])}'
                f'<span style="background:#e4f3e8;border-left:3px solid {STAT};'
                f'display:block;padding:8px 10px;margin-top:8px">'
                f'{_escape(amended[before_len:])}</span></div>',
                unsafe_allow_html=True,
            )

        st.download_button(
            "Download amended policy (Markdown)",
            data=amended,
            file_name=f"{st.session_state.la_policy_code}_amended_ca.md",
            mime="text/markdown",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="la_back_3"):
                st.session_state.la_step = 2; st.rerun()
        with col2:
            if st.button("See rationale →", type="primary", key="la_next_3"):
                st.session_state.la_step = 4; st.rerun()
        return

    # ── Step 4: Rationale + Anthropic benchmark ──
    if cur == 4:
        st.markdown("### Step 4 — Why each change was made + Anthropic policy benchmark")
        rep = st.session_state.la_report
        gaps = [r for r in rep["results"] if r["measured"]["status"] != "Addressed"]
        client = _get_client()

        if not gaps:
            st.success("No gaps found. The policy as loaded satisfies all CA must-pass requirements.")
        else:
            st.caption(
                f"{len(gaps)} gap(s). Each block explains what was missing, why the language was added, "
                "and how it compares to Anthropic's published AI policy on the same domain."
            )
            for r in gaps:
                mm = r["measured"]
                tier = r["ag_test_tier"]
                tier_note = {
                    "Statutory": "Hard enacted requirement — directly from SB 1288, AB 2225, Ed Code, SOPIPA, FERPA, or COPPA. Any district deploying AI must address this.",
                    "Enacted": "Built to the CDE Model AI Policy compliance standard. Required to meet the CDE compliance threshold.",
                    "Guidance": "Best-practice per CDE 26 principles. Not a hard compliance bar, but expected in a comprehensive district AI policy.",
                }.get(tier, "")

                gap_labels = mm.get("gap") or []
                evidence_summary = (
                    f'The policy mentions "{(mm["evidence"]["text"][:180] + "...") if mm["evidence"] and len(mm["evidence"]["text"]) > 180 else (mm["evidence"]["text"] if mm["evidence"] else "")}" but does not fully satisfy the requirement.'
                    if mm["evidence"]
                    else "The policy contains no provision addressing this requirement."
                )

                # Anthropic comparison (cached per criterion)
                comp_key = r["id"]
                if comp_key not in st.session_state.anthropic_comparisons and client:
                    amended_text = r.get("revision", "")
                    st.session_state.anthropic_comparisons[comp_key] = compare_to_anthropic(r, amended_text, client)
                anthropic_note = st.session_state.anthropic_comparisons.get(comp_key, "")

                st.markdown(
                    f'''
<div style="border:1px solid {LINE};border-radius:8px;padding:14px 16px;margin:10px 0;background:#fff">
<div style="display:flex;justify-content:space-between;align-items:center">
<div><span style="font-family:ui-monospace,Menlo,monospace;font-weight:700;color:{NAVY}">{r["id"]} · {r["term"]}</span></div>
<div><span class="badge b-{tier}">{tier}</span></div>
</div>
<div style="font-size:11.5px;color:{MUTED};font-family:ui-monospace,Menlo,monospace;margin:4px 0 10px">{r["hook"]}</div>

<div style="margin-bottom:8px"><b>What was missing.</b> {evidence_summary}
{"Specifically: " + "; ".join(gap_labels) + "." if gap_labels else ""}
</div>

<div style="margin-bottom:8px"><b>Why this language was added.</b> Satisfies the pass condition — {r.get("pass_condition","")}</div>

<div style="background:#eef4fb;border:1px solid #cfe0f2;border-radius:6px;padding:10px 12px;margin:8px 0;color:{NAVY};font-size:13px">
<b>Inserted language.</b> "{r.get("revision","")}"
</div>

<div style="margin-bottom:8px"><b>CA law rationale.</b> {tier_note}</div>

{"" if not anthropic_note else f'<div class="anthropic"><div class="lbl">Anthropic policy benchmark</div>{anthropic_note}</div>'}

<div style="font-size:12px;color:{MUTED};border-top:1px solid {LINE};padding-top:8px;margin-top:8px">
<b>Pass semantics:</b> {r["pass_semantics"]}
</div>
</div>''',
                    unsafe_allow_html=True,
                )

        st.markdown(
            f'<div class="note">Not legal advice. All insertions must be attorney-reviewed before '
            f'board adoption. Statutory items directly implement enacted California law. Enacted items '
            f'follow CDE Model Policy standards. Guidance items reflect best practice.</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back", key="la_back_4"):
                st.session_state.la_step = 3; st.rerun()
        with col2:
            if st.button("Load another policy", key="la_restart"):
                _reset_load_amend(); st.rerun()
        return


# ── view: upload manual ───────────────────────────────────────────────────────
def view_upload() -> None:
    _render_header()
    st.markdown('<div class="pill">SB 1288 · AB 2225 · CDE Model Policy</div>', unsafe_allow_html=True)
    st.markdown("# Step 2 — Upload Manual")
    st.markdown(
        '<p class="sub">Upload your full district policy manual and get a scoreboard of every policy '
        'measured against California AI law — showing which pass, which are partial, and which need work.</p>',
        unsafe_allow_html=True,
    )

    ss = st.session_state

    # Show pre-baked districts in preferred order: Natomas first, Lodi second
    DISTRICT_ORDER = ["Natomas", "Lodi"]
    ordered = [d for d in DISTRICT_ORDER if d in ss.district_library]
    ordered += [d for d in ss.district_library if d not in DISTRICT_ORDER]
    if ordered:
        st.markdown("### Districts on file")
        for label in ordered:
            col_name, col_btn = st.columns([6, 1])
            with col_name:
                st.markdown(f'**{label}**')
            with col_btn:
                if st.button("Load", key=f"upload_load_{label}"):
                    ss.active_district = label
                    ss.district_name = label
                    ss.report = ss.district_library[label]
                    ss.policies = ss.district_policies.get(label)
                    ss.selected_policy_code = None
                    ss.report_amended = None
                    ss.show_amended = False
                    if "_amend_toggle" in ss: del ss["_amend_toggle"]
                    ss.view = "report"
                    st.rerun()
        st.markdown("---")

    st.markdown("### Or provide your own policy manual")
    col_a, col_b = st.columns(2)
    with col_a:
        entered_name = st.text_input(
            "District name", value="", key="upload_district_name")
        st.session_state.district_name = entered_name
    with col_b:
        st.selectbox("State", ["California"], index=0)

    up = st.file_uploader(
        "Upload PDF, DOCX, TXT, or MD",
        type=["pdf", "docx", "txt", "md"],
        help="The full policy manual is split into provisions and each is measured against 44 CA criteria.",
    )
    if up is not None:
        suffix = os.path.splitext(up.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(up.read())
            path = tmp.name
        try:
            with st.spinner(f"Examining {up.name} against CA AI law — this may take a minute..."):
                raw_text = parse_document(path)
                st.session_state.manual_text = raw_text
                st.session_state.report = run(path)
            district_key = entered_name.strip() or os.path.splitext(up.name)[0]
            st.session_state.district_source = f"Upload: {up.name}"
            st.session_state.district_name = district_key
            st.session_state.district_library[district_key] = st.session_state.report
            st.session_state.active_district = district_key
            # Build per-policy reports from the manual
            pol_map = _split_manual_policies(raw_text)
            if pol_map:
                per_pol = {}
                total = len(pol_map)
                prog = st.progress(0, text="Measuring individual policies...")
                for idx, (code, pd) in enumerate(pol_map.items()):
                    try:
                        per_pol[code] = {"title": pd["title"], "report": measure_text(pd["text"])}
                    except Exception:
                        pass
                    prog.progress((idx + 1) / total, text=f"Measuring {code}... ({idx+1}/{total})")
                prog.empty()
                st.session_state.policies = per_pol
                st.session_state.district_policies[district_key] = per_pol
            else:
                st.session_state.policies = None
            st.session_state.selected_policy_code = None
            st.session_state.view = "report"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        st.rerun()


# ── view: initial report ──────────────────────────────────────────────────────
def view_report() -> None:
    ss = st.session_state
    _ensure_amended()
    rep = _active_report()
    if rep is None and ss.la_policy_text is None:
        st.info("Load a policy on **Load & Amend a Policy**, or a full manual on **Upload Manual**.")
        return

    st.markdown('<div class="pill">SB 1288 · AB 2225 · CDE Model Policy</div>', unsafe_allow_html=True)
    st.markdown(f"# Initial Report — {ss.district_name or 'District'}")
    single = " · single-policy view" if ss.report is None and ss.la_report is not None else ""
    st.markdown(f'<p class="sub">Source: {ss.district_source}{single}</p>', unsafe_allow_html=True)

    _render_amended_toggle()

    if rep is not None:
        s = rep["score"]
        ok = s["within_ca_threshold"]
        st.markdown(
            f'<div class="{"verdict-ok" if ok else "verdict-no"}">'
            f'{"Within the CA compliance threshold on all must-pass requirements." if ok else f"Not yet within threshold — {len(s[chr(102)+chr(97)+chr(105)+chr(108)+chr(105)+chr(110)+chr(103)])} must-pass requirements unmet."}'
            f'</div>',
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="tile"><div class="n">{rep["provisions"]}</div><div class="lbl">Provisions examined</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="tile"><div class="n">{s["must_pass_addressed"]}/{s["must_pass_total"]}</div><div class="lbl">Must-pass addressed</div></div>', unsafe_allow_html=True)
        by_tier = s["by_tier"]
        stat = by_tier.get("Statutory", {"addressed": 0, "total": 0})
        enact = by_tier.get("Enacted", {"addressed": 0, "total": 0})
        c3.markdown(f'<div class="tile"><div class="n">{stat["addressed"]}/{stat["total"]}</div><div class="lbl">Statutory</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="tile"><div class="n">{enact["addressed"]}/{enact["total"]}</div><div class="lbl">Enacted</div></div>', unsafe_allow_html=True)

        # Per-policy scoreboard (when per-policy data is available)
        if ss.policies:
            col_chk, col_hint = st.columns([3, 2])
            with col_chk:
                show_only_gaps = st.checkbox("Show only policies with gaps", value=False)
            with col_hint:
                st.markdown(
                    "<span style='font-size:15px;font-weight:900'>"
                    "✅ CLICK OPEN TO GENERATE POLICY DETAIL"
                    "</span>", unsafe_allow_html=True
                )
            st.markdown("### Per-policy compliance")
            for code, pd in ss.policies.items():
                pr = pd["report"]
                ps = pr["score"]
                addressed = ps["must_pass_addressed"]
                total_mp = ps["must_pass_total"]
                ok = ps["within_ca_threshold"]
                if show_only_gaps and ok:
                    continue
                pri = "Low" if ok else ("Medium" if addressed >= total_mp // 2 else "High")
                cols = st.columns([1, 5, 2])
                with cols[0]:
                    st.markdown(f'<span class="badge b-{pri}">{pri}</span>', unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(
                        f'<div class="polcard">'
                        f'<span class="code">{code}</span> · <b>{pd["title"]}</b>'
                        f'<div class="rat">'
                        f'<span style="color:{STAT}">✓ {addressed}</span> must-pass addressed'
                        f' &nbsp;·&nbsp; <span style="color:{CONT}">{total_mp - addressed}</span> gaps'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                with cols[2]:
                    if st.button("Open", key=f"open_pol_{code}"):
                        ss.selected_policy_code = code
                        ss.view = "detail"
                        st.rerun()
            return

        # Per-domain scoreboard (fallback when no per-policy data)
        st.markdown("### Domain scoreboard")
        results = [r for r in rep["results"]]
        by_module: dict[str, list] = {}
        for r in results:
            by_module.setdefault(r["module"], []).append(r)

        for m in MODULE_ORDER:
            if m not in by_module:
                continue
            rows = by_module[m]
            addr = sum(1 for r in rows if r["measured"]["status"] == "Addressed")
            partial = sum(1 for r in rows if r["measured"]["status"] == "Partial")
            missing = sum(1 for r in rows if r["measured"]["status"] == "Not addressed")
            total = len(rows)
            pri = "High" if missing > 0 else ("Medium" if partial > 0 else "Low")
            cols = st.columns([1, 5, 2])
            with cols[0]:
                st.markdown(f'<span class="badge b-{pri}">{pri}</span>', unsafe_allow_html=True)
            with cols[1]:
                st.markdown(
                    f'<div class="polcard">'
                    f'<span class="code">{m}</span> · <b>{MODULES[m]}</b>'
                    f'<div class="rat">'
                    f'<span style="color:{STAT}">✓ {addr}</span> addressed &nbsp;·&nbsp; '
                    f'<span style="color:{GUID}">~ {partial}</span> partial &nbsp;·&nbsp; '
                    f'<span style="color:{CONT}">✗ {missing}</span> missing'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with cols[2]:
                if st.button("Open", key=f"open_{m}"):
                    ss.selected_policy = m
                    ss.view = "detail"
                    st.rerun()


# ── view: policy detail ────────────────────────────────────────────────────────
def _split_manual_policies(text: str) -> dict:
    """Split a full manual into {code: {title, text}} by POLICY CODE -- Title headers."""
    import re as _re
    pattern = _re.compile(r'(?m)^POLICY\s+(\S+)\s+--\s+(.+)$')
    matches = list(pattern.finditer(text))
    if not matches:
        return {}
    result = {}
    for i, m in enumerate(matches):
        code = m.group(1).strip()
        title = m.group(2).strip().rstrip("\r")
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result[code] = {"title": title, "text": text[start:end].strip()}
    return result


def _build_policy_additions(gaps: list[dict]) -> str:
    if not gaps:
        return ""
    lines = ["", "---", "", "## Additions to satisfy California AI Policy Requirements", ""]
    by_module: dict[str, list] = {}
    for r in gaps:
        by_module.setdefault(r["module"], []).append(r)
    for m in MODULE_ORDER:
        if m not in by_module:
            continue
        lines.append(f"### {m} — {MODULES[m]}")
        lines.append("")
        for r in by_module[m]:
            lines.append(f"**[{r['id']} · {r['term']} · {r['ag_test_tier']} · {r['hook']}]**")
            lines.append("")
            lines.append(r.get("revision", ""))
            lines.append("")
    return "\n".join(lines)


def view_detail() -> None:
    ss = st.session_state
    _ensure_amended()
    rep = _active_report()

    # ── Per-policy detail (from per-policy Initial Report) ───────────────
    if ss.selected_policy_code is not None and ss.policies is not None:
        code = ss.selected_policy_code
        pd = ss.policies.get(code)
        if pd is None:
            st.warning(f"Policy {code} not found in loaded policies.")
            return
        st.markdown('<div class="pill">SB 1288 · AB 2225 · CDE Model Policy</div>', unsafe_allow_html=True)
        st.markdown(f"# {code} — {pd['title']}")
        pol_rep = pd["report"]
        gaps = [r for r in pol_rep["results"] if r["measured"]["status"] != "Addressed"]
        # text may not be in pre-baked JSON — extract from manual_text or district manual
        if "text" in pd:
            original = pd["text"]
        elif ss.get("manual_text"):
            pol_map = _split_manual_policies(ss.manual_text)
            original = pol_map.get(code, {}).get("text", "")
        else:
            # Load district manual from disk
            manual_paths = ss.get("district_manual_paths", {})
            manual_path = manual_paths.get(ss.district_name, "")
            if manual_path:
                raw = open(manual_path, encoding="utf-8").read()
                ss["manual_text"] = raw
                pol_map = _split_manual_policies(raw)
                original = pol_map.get(code, {}).get("text", "")
            else:
                original = ""
        additions = _build_policy_additions(gaps)
        amended = original.rstrip() + "\n\n" + additions if additions else original
        col_b, col_a = st.columns(2)
        with col_b:
            st.markdown("**Before — existing policy**")
            st.markdown(
                f'<div style="max-height:600px;overflow:auto;border:1px solid {LINE};border-radius:6px;'
                f'padding:12px;background:#fafbfd;font-size:12.5px;white-space:pre-wrap;'
                f'font-family:ui-monospace,Menlo,monospace">{_escape(original)}</div>',
                unsafe_allow_html=True,
            )
        with col_a:
            st.markdown("**After — CA AI compliance additions**")
            additions_only = additions.strip() if additions.strip() else "No additions needed — policy satisfies all CA must-pass requirements."
            st.markdown(
                f'<div style="max-height:600px;overflow:auto;border:1px solid {STAT};border-radius:6px;'
                f'padding:12px;background:#e4f3e8;font-size:12.5px;white-space:pre-wrap;'
                f'font-family:ui-monospace,Menlo,monospace">{_escape(additions_only)}</div>',
                unsafe_allow_html=True,
            )
        if gaps:
            st.markdown(f"**{len(gaps)} gap(s) found across {len(pol_rep['results'])} criteria.**")
            for r in gaps:
                mm = r["measured"]
                st_status = mm["status"]
                badge_class = "b-Partial" if st_status == "Partial" else "b-NotAddressed"
                icon = "🟡" if st_status == "Partial" else "🔴"
                with st.expander(f"{icon} {r['id']} · {r['term']} — {st_status}  [{r['ag_test_tier']}]"):
                    st.caption(f"{r['hook']} · {r['pass_semantics']}")
                    if mm["evidence"]:
                        st.markdown(
                            f'<div class="ev"><b>{mm["evidence"]["heading"]}</b> — '
                            f'"{mm["evidence"]["text"][:600]}"</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown('<div class="ev">No matching provision found.</div>', unsafe_allow_html=True)
                    if mm["gap"]:
                        st.markdown(f"**Gap:** missing {'; '.join(mm['gap'])}.")
                    if r.get("revision"):
                        st.markdown(
                            f'<div class="rev"><b>Suggested language</b><br>"{r["revision"]}"</div>',
                            unsafe_allow_html=True,
                        )
        else:
            st.success("This policy satisfies all CA must-pass requirements.")
        st.download_button(
            "Download amended policy (Markdown)",
            data=amended,
            file_name=f"{code}_amended_ca.md",
            mime="text/markdown",
        )
        if st.button("← Back to Initial Report"):
            ss.view = "report"
            st.rerun()
        return

    if ss.selected_policy is None or rep is None:
        st.info("Select a domain from **Initial Report** to open its detail.")
        return

    m = ss.selected_policy
    if m not in MODULES:
        # Could be a single-policy code — show full policy detail
        m = None

    st.markdown('<div class="pill">SB 1288 · AB 2225 · CDE Model Policy</div>', unsafe_allow_html=True)

    results = [r for r in rep["results"] if (m is None or r["module"] == m)]

    if m:
        st.markdown(f"# {m} — {MODULES[m]}")
    else:
        st.markdown(f"# Policy Detail — {ss.selected_policy}")

    _render_amended_toggle()

    for r in results:
        mm = r["measured"]
        st_status = mm["status"]
        badge_class = ("b-Addressed" if st_status == "Addressed" else
                       "b-Partial" if st_status == "Partial" else "b-NotAddressed")
        icon = {"Addressed": "✅", "Partial": "🟡", "Not addressed": "🔴"}.get(st_status, "•")

        with st.expander(f"{icon} {r['id']} · {r['term']} — {st_status}  [{r['ag_test_tier']}]"):
            st.caption(f"{r['hook']} · {r['pass_semantics']}")
            if mm["evidence"]:
                st.markdown(
                    f'<div class="ev"><b>{mm["evidence"]["heading"]}</b> — '
                    f'"{mm["evidence"]["text"][:600]}"</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown('<div class="ev">No matching provision found.</div>', unsafe_allow_html=True)
            if mm["gap"]:
                st.markdown(f"**Gap:** missing {'; '.join(mm['gap'])}.")
            else:
                st.markdown("**Fully satisfied.**")
            if r.get("revision") and st_status != "Addressed":
                st.markdown(
                    f'<div class="rev"><b>Suggested language</b> (re-measured: {r.get("remeasured","—")})'
                    f'<br>"{r["revision"]}"</div>',
                    unsafe_allow_html=True,
                )
                # Anthropic benchmark
                comp_key = r["id"]
                client = _get_client()
                if comp_key not in ss.anthropic_comparisons and client:
                    ss.anthropic_comparisons[comp_key] = compare_to_anthropic(r, r["revision"], client)
                if comp_key in ss.anthropic_comparisons:
                    st.markdown(
                        f'<div class="anthropic"><div class="lbl">Anthropic policy benchmark</div>'
                        f'{ss.anthropic_comparisons[comp_key]}</div>',
                        unsafe_allow_html=True,
                    )


# ── view: compliance overview ─────────────────────────────────────────────────
def view_overview() -> None:
    ss = st.session_state
    _ensure_amended()
    rep = _active_report()
    if rep is None:
        st.info("Load a policy or manual first.")
        return

    st.markdown('<div class="pill">SB 1288 · AB 2225 · CDE Model Policy</div>', unsafe_allow_html=True)
    st.markdown("# Compliance Overview")
    st.markdown('<p class="sub">Criterion-level rollup across all 44 CA requirements. The auditor view.</p>',
                unsafe_allow_html=True)

    _render_amended_toggle()

    s = rep["score"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Provisions examined", rep["provisions"])
    c2.metric("Must-pass addressed", f"{s['must_pass_addressed']}/{s['must_pass_total']}")
    c3.metric("Within CA threshold", "Yes" if s["within_ca_threshold"] else "Not yet")

    results = rep["results"]
    by_module: dict[str, list] = {}
    for r in results:
        by_module.setdefault(r["module"], []).append(r)

    for m in MODULE_ORDER:
        if m not in by_module:
            continue
        rows = by_module[m]
        addressed = sum(1 for r in rows if r["measured"]["status"] == "Addressed")
        st.markdown(f"### {m} — {MODULES[m]}  ·  {addressed}/{len(rows)} addressed")
        for r in rows:
            mm = r["measured"]
            st_status = mm["status"]
            icon = {"Addressed": "✅", "Partial": "🟡", "Not addressed": "🔴"}.get(st_status, "•")
            with st.expander(f"{icon} {r['id']} · {r['term']} — {st_status}  [{r['ag_test_tier']}]"):
                st.caption(f"{r['hook']} · {r['pass_semantics']}")
                if mm["evidence"]:
                    st.markdown(
                        f'<div class="ev"><b>{mm["evidence"]["heading"]}</b> — '
                        f'"{mm["evidence"]["text"][:600]}"</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<div class="ev">No matching provision found.</div>', unsafe_allow_html=True)
                if mm["gap"]:
                    st.markdown(f"**Gap:** missing {'; '.join(mm['gap'])}.")
                else:
                    st.markdown("**Fully satisfied.**")
                if r.get("revision") and st_status != "Addressed":
                    st.markdown(
                        f'<div class="rev"><b>Suggested language</b><br>"{r["revision"]}"</div>',
                        unsafe_allow_html=True,
                    )


# ── view: gap analysis & revision ─────────────────────────────────────────────
def view_gap() -> None:
    ss = st.session_state
    _ensure_amended()
    rep = _active_report()
    if rep is None:
        st.info("Load a policy or manual first.")
        return

    st.markdown("# Gap Analysis & Revision")
    st.markdown(
        '<p class="sub">Every must-pass gap and the generated language that closes it. '
        'Export the full report as HTML for attorney review.</p>',
        unsafe_allow_html=True,
    )

    _render_amended_toggle()

    results = rep["results"]
    gaps = [r for r in results if r["measured"]["status"] != "Addressed"]
    st.markdown(f"**{len(gaps)} gaps** identified across {len(results)} criteria.")

    for m in MODULE_ORDER:
        mod_gaps = [r for r in gaps if r["module"] == m]
        if not mod_gaps:
            continue
        st.markdown(f"### {m} — {MODULES[m]}  ·  {len(mod_gaps)} gap(s)")
        for r in mod_gaps:
            mm = r["measured"]
            st.markdown(f"**{r['id']} · {r['term']}** — {mm['status']}  ·  `{r['hook']}`")
            if mm["gap"]:
                st.caption(f"Missing: {'; '.join(mm['gap'])}")
            if r.get("revision"):
                st.markdown(f'<div class="rev">{r["revision"]}</div>', unsafe_allow_html=True)

    html = render_html(rep, district=ss.district_name or "District")
    st.download_button(
        "Download full measurement report (HTML)",
        data=html,
        file_name=f"comply_ca_report_{re.sub(r'[^A-Za-z0-9]+','_', ss.district_name or 'district').lower()}.html",
        mime="text/html",
    )


# ── view: benchmark comparison ──────────────────────────────────────────────
def view_benchmark() -> None:
    ss = st.session_state

    # Determine which policy report to use
    pol_rep = None
    pol_name = None
    pol_text = None

    if ss.selected_policy_code and ss.policies:
        code = ss.selected_policy_code
        pd = ss.policies.get(code, {})
        pol_rep = pd.get("report")
        pol_name = f"{code} — {pd.get('title', code)}"
        # Get policy text on demand
        if "text" in pd:
            pol_text = pd["text"]
        elif ss.get("manual_text"):
            pol_map = _split_manual_policies(ss.manual_text)
            pol_text = pol_map.get(code, {}).get("text", "")
        else:
            manual_paths = ss.get("district_manual_paths", {})
            manual_path = manual_paths.get(ss.district_name, "")
            if manual_path:
                raw = open(manual_path, encoding="utf-8").read()
                ss["manual_text"] = raw
                pol_map = _split_manual_policies(raw)
                pol_text = pol_map.get(code, {}).get("text", "")
    elif ss.la_policy_text:
        pol_rep = ss.la_report
        pol_name = ss.la_policy_name or "Loaded policy"
        pol_text = ss.la_policy_text

    if pol_rep is None:
        st.info("Load or open a policy first to run a benchmark comparison.")
        return

    st.markdown('<div class="pill">SB 1288 · AB 2225 · CDE Model Policy</div>', unsafe_allow_html=True)
    st.markdown("# Benchmark Comparison")
    st.markdown(
        f'<p class="sub">Compare <b>{pol_name}</b> against a model AI policy '
        'to identify where district language aligns and where it could be strengthened.</p>',
        unsafe_allow_html=True,
    )

    # Find domains with gaps in this policy
    gaps = [r for r in pol_rep["results"] if r["measured"]["status"] != "Addressed"]
    gap_modules = list(dict.fromkeys(r["module"] for r in gaps))  # preserve order, dedupe

    if not gaps:
        st.success("This policy satisfies all CA must-pass requirements — no gaps to benchmark.")
        return

    st.markdown(f"**{len(gap_modules)} domain(s) with gaps** in this policy. Select one to compare against the model policy.")
    st.markdown("")

    domain_options = [f"{m} — {MODULES[m]}" for m in gap_modules]
    chosen = st.selectbox("Select domain to benchmark", domain_options, key="benchmark_domain")
    chosen_module = chosen.split(" — ")[0]

    domain_gaps = [r for r in gaps if r["module"] == chosen_module]

    if st.button("Run benchmark comparison", type="primary", key="run_benchmark"):
        client = _get_client()
        if not client:
            st.error("ANTHROPIC_API_KEY not set — cannot run benchmark.")
        else:
            with st.spinner(f"Comparing {chosen_module} against model policy..."):
                for r in domain_gaps:
                    key = f"{ss.selected_policy_code or 'la'}_{r['id']}"
                    if key not in ss.benchmark_results:
                        amended_text = r.get("revision", "")
                        ss.benchmark_results[key] = compare_to_anthropic(r, amended_text, client)
            st.rerun()

    # Show any already-computed results for this domain
    any_shown = False
    for r in domain_gaps:
        key = f"{ss.selected_policy_code or 'la'}_{r['id']}"
        if key in ss.benchmark_results:
            if not any_shown:
                st.markdown(f"### {chosen_module} — {MODULES[chosen_module]}")
                any_shown = True
            tier = r["ag_test_tier"]
            st.markdown(
                f'<div style="border:1px solid {LINE};border-radius:8px;padding:14px 16px;margin:10px 0;background:#fff">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                f'<span style="font-family:ui-monospace,Menlo,monospace;font-weight:700;color:{NAVY}">{r["id"]} · {r["term"]}</span>'
                f'<span class="badge b-{tier}">{tier}</span></div>'
                f'<div style="font-size:11.5px;color:{MUTED};font-family:ui-monospace,Menlo,monospace;margin-bottom:10px">{r["hook"]}</div>'
                f'<div style="background:#f5f0ff;border:1px solid #c8b8f0;border-radius:6px;padding:12px 14px;color:#3d2b7a;font-size:13px;line-height:1.5">'
                f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#7a5bbf;font-weight:700;margin-bottom:6px">Model policy comparison</div>'
                f'{ss.benchmark_results[key]}</div></div>',
                unsafe_allow_html=True,
            )

    if st.button("← Back to Policy Detail", key="benchmark_back"):
        ss.view = "detail"
        st.rerun()


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title="COMPLY-CA | H-EDU.Solutions",
        page_icon="⚖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    init_state()
    sidebar()

    v = st.session_state.view
    if v == "load_amend":
        view_load_amend()
    elif v == "upload":
        view_upload()
    elif v == "report":
        view_report()
    elif v == "detail":
        view_detail()
    elif v == "overview":
        view_overview()
    elif v == "gap":
        view_gap()
    elif v == "benchmark":
        view_benchmark()
    else:
        view_load_amend()


if __name__ == "__main__":
    main()
