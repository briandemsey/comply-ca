"""
comply-ca — California AI Policy Compliance Platform
H-EDU.Solutions

Two tools in one:
  Tab 1 — Policy Generator: guided self-assessment against SB 1288 + AB 2225,
           produces a board-ready AI policy document.
  Tab 2 — Policy Analyzer: paste or upload an existing district policy;
           app scores it domain-by-domain against the CA criteria engine
           and produces a prioritized gap report.

Legal anchors: SB 1288 (CDE Model Policy, 26 principles), AB 2225,
CPPA ADMT regulations, Ed Code 49073.1 / SOPIPA / AB 1584,
SB 942 / SB 243 / AB 2013, FERPA / COPPA / IDEA / Title VI / Title IX.
"""

import re
import io
import streamlit as st
from datetime import date, datetime

# ── brand ──────────────────────────────────────────────────────────────────
CA_BLUE   = "#003DA5"
CA_GOLD   = "#FFB81C"
CA_LIGHT  = "#F0F4FA"
CA_DARK   = "#001F5B"
CA_GREEN  = "#2E7D32"
CA_RED    = "#C62828"
CA_GRAY   = "#546E7A"

# ── CA criteria engine ─────────────────────────────────────────────────────
# 11 domains derived from SB 1288 / CDE 26 principles / AB 2225 /
# CPPA ADMT / Ed Code / federal floor.
# Each domain: title, description, authority, required_elements (testable),
# model_language, questions (for generator tab).

DOMAINS = {
    "GOV": {
        "title": "Governance & Strategy",
        "short": "Governance",
        "authority": "CDE Principles 21, 22, 25; SB 1288 §1(a)",
        "description": (
            "Named AI strategy, multistakeholder development, biennial review, "
            "institutional accountability, and ongoing monitoring."
        ),
        "required_elements": [
            "District has a named, board-adopted AI strategy or policy",
            "Policy developed with input from educators, families, and students",
            "Policy includes a review cycle of at least every two years",
            "Responsibility for AI oversight is assigned to a named role or committee",
            "Board receives regular AI program monitoring reports",
        ],
        "model_language": """\
The Board of Education adopts this policy as the District's formal Artificial
Intelligence Strategy. The Superintendent shall designate an AI Coordinator
responsible for implementation and monitoring. This policy shall be reviewed
biennially or sooner if material changes occur in applicable law or technology.

Policy development shall engage educators, classified staff, students, families,
and community members. The Superintendent shall report to the Board at least
annually on AI program outcomes, equity impacts, and compliance status.
""",
        "questions": [
            "Does your district have a board-adopted AI policy or strategy?",
            "Was the policy developed with community and staff input?",
            "Is there a named AI coordinator or oversight committee?",
            "Does the policy specify a review cycle?",
            "Does the Board receive regular AI program reports?",
        ],
    },
    "PRIV": {
        "title": "Data Privacy & Security",
        "short": "Privacy",
        "authority": "CDE 7, 9; FERPA; Ed Code 49073.1; SOPIPA; AB 1584; COPPA",
        "description": (
            "Privacy-by-design, restricted data entry, prohibition on training "
            "commercial models, breach security, and vendor data agreements."
        ),
        "required_elements": [
            "AI tools may not use student PII to train commercial AI models",
            "Data Privacy Agreements (DPAs) required before any AI tool deployment",
            "Privacy impact assessment conducted before new tool adoption",
            "Student data retention and deletion schedules are defined",
            "Breach notification procedures address AI-system incidents",
        ],
        "model_language": """\
No artificial intelligence system may use student personally identifiable
information (PII) to train, improve, or develop commercial AI models without
explicit, informed written consent.

Prior to deploying any AI tool that processes student data, the District shall:
1. Execute a Data Privacy Agreement (DPA) with the vendor
2. Conduct a privacy impact assessment
3. Verify compliance with FERPA, Ed Code 49073.1, SOPIPA, AB 1584, and COPPA
4. Establish data retention and deletion schedules

Student data shall not be sold, shared for advertising purposes, or used for
any purpose beyond the contracted educational service.
""",
        "questions": [
            "Do you require DPAs before deploying AI tools?",
            "Have you conducted privacy impact assessments for current AI tools?",
            "Is there a prohibition on using student data to train commercial models?",
            "Are data retention and deletion schedules defined for AI vendors?",
            "Do breach notification procedures cover AI system incidents?",
        ],
    },
    "TRANS": {
        "title": "Transparency & Disclosure",
        "short": "Transparency",
        "authority": "CDE 10; SB 243; AB 2013; SB 942",
        "description": (
            "Informed annual consent, AI interaction disclosure, "
            "AI-identity disclosure for minors, and training-data transparency."
        ),
        "required_elements": [
            "Annual parent/guardian notification of AI tools in use",
            "Students are informed when they are interacting with an AI system",
            "AI systems disclose AI identity when asked by a minor (SB 243)",
            "Vendors must disclose training data sources upon request (AB 2013)",
            "District publishes a registry of approved AI tools",
        ],
        "model_language": """\
The District shall publish and annually update a registry of AI tools in use,
including vendor name, purpose, data accessed, and applicable privacy certifications.
Parents and guardians shall receive annual notification of AI tools used in
their child's educational environment.

Any AI system that may interact directly with students shall:
- Identify itself as an AI when asked by the user (SB 243)
- Not claim to be human in contexts designed to deceive
- Provide clear mechanisms for students to escalate to a human

The District shall require vendors to disclose training data provenance upon
request, consistent with AB 2013 (effective January 1, 2026).
""",
        "questions": [
            "Do parents receive annual notification of AI tools used?",
            "Are students informed when interacting with an AI system?",
            "Do AI tools disclose AI identity to minors when asked?",
            "Do you require vendors to disclose training data sources?",
            "Does the district maintain a public registry of approved AI tools?",
        ],
    },
    "HUMAN": {
        "title": "Human Review & Automated Decisions",
        "short": "Human Review",
        "authority": "CDE 11, 18, 20; CPPA ADMT regulations (eff. Jan 1, 2027); AB 2225",
        "description": (
            "Human override authority, guardian review rights, educator sole grading "
            "authority, pre-use notice/opt-out/appeal for education decisions (ADMT)."
        ),
        "required_elements": [
            "No AI output affecting student placement, discipline, or services is implemented without qualified human review",
            "Reviewers must have authority to override AI recommendations",
            "Parents/guardians may request human review of any AI-influenced education decision",
            "Educators retain sole authority over grades and academic advancement",
            "Pre-use notice, opt-out right, and appeal path provided for significant AI-driven education decisions",
        ],
        "model_language": """\
No AI-generated recommendation shall be implemented without review by a qualified
educator or administrator who has the authority to override that recommendation.

Mandatory human review applies before AI output influences:
- Special education eligibility or services (IDEA)
- Student discipline decisions
- Grade-level placement or advancement
- Intervention or support service assignments
- Any other significant education decision

Parents and guardians shall have the right to:
- Receive notice before an AI system substantially influences a significant
  decision about their child
- Opt their child out of non-essential AI systems
- Request a human review and appeal of any AI-influenced decision

Educators hold sole authority over student grades. AI tools may support
assessment but shall not independently assign grades or determine proficiency.

Consistent with AB 2225 and the CPPA's Automated Decisionmaking Technology
(ADMT) regulations (effective January 1, 2027), vendors supplying AI that
substantially influences enrollment or educational opportunity decisions must
provide pre-use notices, opt-out mechanisms, and documented appeal paths.
""",
        "questions": [
            "Is human review required before AI affects student decisions?",
            "Do reviewers have explicit authority to override AI recommendations?",
            "Can parents request human review of AI-influenced decisions?",
            "Do educators retain sole authority over student grades?",
            "Do vendor contracts address ADMT opt-out and appeal requirements?",
        ],
    },
    "INTEG": {
        "title": "Academic Integrity",
        "short": "Integrity",
        "authority": "CDE 1, 2; SB 1288 §1(b)",
        "description": (
            "Disclosure and citation requirements for AI use; AI-detection tools "
            "may not serve as the sole basis for discipline."
        ),
        "required_elements": [
            "Students must disclose AI use when required by the instructor",
            "AI-generated content submitted as original work without disclosure is academic dishonesty",
            "Educators communicate AI-use expectations per assignment",
            "AI detection tool output alone is insufficient basis for academic discipline",
            "Consequences for AI-related academic dishonesty are defined",
        ],
        "model_language": """\
Students shall disclose the use of AI tools in completing assignments when
required by the instructor. Submitting AI-generated content as original work
without disclosure constitutes academic dishonesty subject to existing
disciplinary procedures.

Educators shall clearly communicate expectations regarding AI use for each
assignment. AI detection software may be used as one factor in investigating
academic integrity concerns, but shall not serve as the sole basis for
academic discipline — a student shall not be disciplined for AI-generated
content without corroborating evidence.
""",
        "questions": [
            "Is AI disclosure required when instructors specify it?",
            "Is undisclosed AI submission defined as academic dishonesty?",
            "Are educators expected to set per-assignment AI expectations?",
            "Does policy prohibit relying solely on AI detection for discipline?",
            "Are consequences for AI-related dishonesty defined?",
        ],
    },
    "SAFE": {
        "title": "Acceptable Use & Student Safety",
        "short": "Safety",
        "authority": "CDE 3, 4, 12, 19; SB 243; AB 2225",
        "description": (
            "Authorized-use limits, no-harm rules, risk-response procedures, "
            "and vendor well-being monitoring requirements."
        ),
        "required_elements": [
            "Approved AI tool list maintained; unapproved tools prohibited for instruction",
            "AI tools may not facilitate self-harm, bullying, or illegal activity",
            "Clear risk-response procedure exists for AI-related safety incidents",
            "Companion or social AI tools evaluated for minor well-being impact (SB 243)",
            "Staff report AI-generated harmful content through established safety protocols",
        ],
        "model_language": """\
Only AI tools approved through the District's procurement process may be used
for instruction or administrative purposes involving student data.

AI tools shall not be used to:
- Generate content that facilitates self-harm, bullying, or harassment
- Circumvent content filters or safety controls
- Access, store, or transmit student PII outside approved systems
- Deceive students about the AI nature of the system

The District shall evaluate companion or social AI tools for potential impacts
on student mental health and well-being prior to deployment (SB 243). Staff
shall report AI-generated harmful content through established incident-reporting
protocols. The Superintendent shall establish a risk-response procedure for
AI-related safety incidents.
""",
        "questions": [
            "Is there a maintained approved AI tool list?",
            "Are prohibited AI uses clearly defined?",
            "Is there an incident-response procedure for AI safety events?",
            "Are companion/social AI tools evaluated for student well-being?",
            "Do staff know how to report AI-generated harmful content?",
        ],
    },
    "EQUITY": {
        "title": "Nondiscrimination & Equity",
        "short": "Equity",
        "authority": "CDE 23, 24; Title VI; Title IX; §504/ADA; IDEA; Ed Code 200",
        "description": (
            "Bias and fairness audits, equitable access across student groups, "
            "and protected-class safeguards in AI outputs."
        ),
        "required_elements": [
            "AI tools are evaluated for bias against protected classes before deployment",
            "Equitable access to approved AI tools across all student populations",
            "AI recommendations are monitored for disparate impact by race, disability, EL status",
            "Disability accommodations are maintained regardless of AI system design",
            "Annual equity review of AI tool outcomes is conducted",
        ],
        "model_language": """\
Prior to deploying any AI tool, the District shall evaluate the tool for
potential bias against students based on race, ethnicity, national origin,
sex, disability, English learner status, or other protected characteristics
under Title VI, Title IX, Section 504, the ADA, IDEA, and California Ed Code §200.

The District shall:
- Ensure equitable access to beneficial AI tools across all schools and student groups
- Monitor AI-generated recommendations for disparate impact
- Conduct an annual equity review of AI tool outcomes
- Ensure that IEP and 504 accommodations are maintained and not undermined
  by AI system design
""",
        "questions": [
            "Are AI tools evaluated for bias before deployment?",
            "Is equitable access to AI tools ensured across all student groups?",
            "Are AI recommendations monitored for disparate impact?",
            "Are disability accommodations maintained in AI systems?",
            "Is there an annual equity review of AI tool outcomes?",
        ],
    },
    "VENDOR": {
        "title": "Vendor Management & Procurement",
        "short": "Vendors",
        "authority": "CDE 12, 13, 14; AB 1584; ESSA; FTC §5; Ed Code 49073.1",
        "description": (
            "Approved vendor list, pre-deployment evaluation, enforceable contract "
            "safeguards, and evidence basis for educational AI tools."
        ),
        "required_elements": [
            "Formal AI tool vetting process exists before any classroom deployment",
            "Vendor contracts include data ownership, deletion, and audit rights",
            "AI tools used for instruction have an evidence base for educational effectiveness",
            "Approved vendor registry is centrally maintained and publicly accessible",
            "Vendor compliance with CA student privacy law is verified before contract execution",
        ],
        "model_language": """\
Prior to procuring any AI-enabled tool, the District shall:
1. Conduct a formal evaluation including privacy review, bias assessment,
   and evidence-of-effectiveness review
2. Execute a Data Privacy Agreement meeting the requirements of AB 1584
   and Ed Code 49073.1
3. Verify vendor compliance with SOPIPA, COPPA, and FERPA
4. Confirm that student data will not be used to train commercial AI models
5. Establish contract provisions for data deletion upon contract end

The District shall maintain a centrally-managed, publicly-accessible registry
of approved AI tools including vendor, purpose, data elements accessed,
privacy certification status, and contract renewal date.

AI tools used for academic instruction shall have peer-reviewed evidence of
educational effectiveness, or shall be piloted under monitored conditions
consistent with ESSA evidence standards.
""",
        "questions": [
            "Is there a formal AI procurement and vetting process?",
            "Do contracts include data deletion and audit rights?",
            "Is an evidence base required for instructional AI tools?",
            "Is an approved vendor registry maintained and public?",
            "Is CA student privacy law compliance verified before contract?",
        ],
    },
    "INST": {
        "title": "Instructional Discretion",
        "short": "Instruction",
        "authority": "CDE 5, 6, 15, 16",
        "description": (
            "Educator control per assignment, AI as efficiency tool, "
            "modeling appropriate use, and curriculum redesign."
        ),
        "required_elements": [
            "Educators may authorize or restrict AI use at the assignment level",
            "AI tools are positioned as supports for — not replacements of — educator judgment",
            "Teachers model appropriate AI use for students",
            "Curriculum is being redesigned to integrate AI literacy into learning objectives",
        ],
        "model_language": """\
Educators retain full discretion to authorize, limit, or prohibit the use of
AI tools for any specific assignment or assessment. This discretion shall be
communicated clearly to students for each task.

AI tools shall be used to support educator effectiveness — for planning,
differentiation, feedback, and efficiency — not to replace professional
judgment. Teachers are encouraged to model appropriate AI use as part of
digital citizenship instruction. The District shall support the redesign of
curriculum units to authentically integrate AI literacy as a learning objective.
""",
        "questions": [
            "Can educators set AI-use rules at the assignment level?",
            "Is AI positioned as a support, not a replacement, for teachers?",
            "Are teachers expected to model appropriate AI use?",
            "Is curriculum being redesigned to integrate AI literacy?",
        ],
    },
    "LIT": {
        "title": "AI Literacy",
        "short": "Literacy",
        "authority": "CDE 17; Ed Code 33548; EO 14277 (federal, directional)",
        "description": (
            "Developmentally appropriate AI literacy as a core student competency, "
            "including how AI works, its limitations, and ethical considerations."
        ),
        "required_elements": [
            "AI literacy is included as a learning objective across grade levels",
            "Students learn how AI systems work, including training data and bias",
            "AI literacy instruction is developmentally appropriate",
            "Students are taught to critically evaluate AI-generated content",
        ],
        "model_language": """\
The District shall ensure that all students develop foundational AI literacy
appropriate to their grade level. AI literacy instruction shall include:

- How AI systems are built and trained, including the role of data
- The potential for bias, error, and hallucination in AI outputs
- Ethical and social implications of AI use
- How to critically evaluate AI-generated content
- Privacy and safety considerations when using AI tools

AI literacy shall be integrated into existing digital citizenship curricula
and shall be treated as a core 21st-century competency. (Ed Code 33548)
""",
        "questions": [
            "Is AI literacy included as a learning objective?",
            "Do students learn how AI systems work and their limitations?",
            "Is AI literacy instruction developmentally appropriate by grade?",
            "Are students taught to critically evaluate AI-generated content?",
        ],
    },
    "PD": {
        "title": "Professional Development",
        "short": "Prof Dev",
        "authority": "CDE 26",
        "description": (
            "Training for all staff coupled to every AI tool deployment; "
            "ongoing professional learning on ethical and responsible AI use."
        ),
        "required_elements": [
            "Professional development is provided before any new AI tool is deployed to staff",
            "PD covers ethical use, bias awareness, and student safety considerations",
            "PD is ongoing — not a one-time event",
            "Classified staff receive AI training appropriate to their roles",
        ],
        "model_language": """\
No AI tool shall be deployed for staff or student use without accompanying
professional development. Training shall cover:
- Purpose and capabilities of the tool
- Student privacy and data security obligations
- Ethical and responsible use, including bias awareness
- Student safety protocols
- How to recognize and report AI-related concerns

Professional development shall be ongoing and differentiated by role.
Classified staff, certificated educators, and administrators shall each
receive role-appropriate AI training. The District shall document completion
and evaluate PD effectiveness annually.
""",
        "questions": [
            "Is PD required before any new AI tool deployment?",
            "Does PD cover ethics, bias, privacy, and student safety?",
            "Is PD ongoing rather than a one-time event?",
            "Do classified staff receive role-appropriate AI training?",
        ],
    },
}

DOMAIN_KEYS = list(DOMAINS.keys())

SCORE_OPTIONS = ["Not addressed", "Partially addressed", "Fully addressed"]
SCORE_VALUES  = {"Not addressed": 0, "Partially addressed": 1, "Fully addressed": 2}
SCORE_COLORS  = {"Not addressed": CA_RED, "Partially addressed": CA_GOLD, "Fully addressed": CA_GREEN}

# ── session state ──────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "tab":              "generator",
        "gen_step":         "district",   # district | domain_GOV | ... | review
        "district":         {},
        "responses":        {k: {} for k in DOMAIN_KEYS},
        "custom_lang":      {k: "" for k in DOMAIN_KEYS},
        "domain_done":      {k: False for k in DOMAIN_KEYS},
        "analyzer_text":    "",
        "analyzer_scores":  {},
        "analyzer_done":    False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ── helpers ────────────────────────────────────────────────────────────────
def score_badge(score_label):
    color = SCORE_COLORS.get(score_label, CA_GRAY)
    return (
        f'<span style="background:{color};color:white;border-radius:4px;'
        f'padding:2px 8px;font-size:0.8em;font-weight:bold;">{score_label}</span>'
    )

def overall_pct(responses):
    total, earned = 0, 0
    for domain_r in responses.values():
        for v in domain_r.values():
            total += 2
            earned += SCORE_VALUES.get(v, 0)
    return int(earned / total * 100) if total else 0

def analyze_policy_text(text):
    """
    Score uploaded policy text against each domain's required_elements.
    Uses keyword presence as a proxy — not legal advice.
    Returns dict {domain_key: {"element": score_label, ...}, ...}
    """
    text_lower = text.lower()
    results = {}

    keyword_map = {
        "GOV": [
            ["strategy", "policy", "board-adopted", "board adopted"],
            ["community", "stakeholder", "educator input", "family input"],
            ["review", "biennial", "annual review", "two year", "two-year"],
            ["coordinator", "oversight", "committee", "responsible"],
            ["monitor", "report", "board report", "annual report"],
        ],
        "PRIV": [
            ["train", "commercial model", "not use student data", "not train"],
            ["data privacy agreement", "dpa", "vendor agreement"],
            ["privacy impact", "privacy assessment", "privacy review"],
            ["retention", "deletion", "data deletion", "data retention"],
            ["breach", "incident", "notification", "security incident"],
        ],
        "TRANS": [
            ["annual notification", "notify parent", "parent notification", "annual notice"],
            ["disclose", "inform student", "student know", "identify as ai"],
            ["identify itself", "ai identity", "disclose ai", "sb 243"],
            ["training data", "ab 2013", "data provenance", "data source"],
            ["registry", "approved tool", "tool list", "approved list"],
        ],
        "HUMAN": [
            ["human review", "qualified human", "human oversight", "educator review"],
            ["override", "authority to override", "override authority"],
            ["parent request", "guardian request", "request review", "appeal"],
            ["sole authority", "educator grade", "grade authority", "educator alone"],
            ["notice", "opt-out", "opt out", "appeal path", "admt", "ab 2225"],
        ],
        "INTEG": [
            ["disclose", "disclosure", "ai use disclosure", "cite ai"],
            ["academic dishonesty", "original work", "plagiarism"],
            ["per assignment", "assignment level", "instructor requirement"],
            ["detection", "ai detection", "sole basis", "not sole"],
            ["consequence", "discipline", "penalty", "consequence for"],
        ],
        "SAFE": [
            ["approved tool", "approved list", "unapproved", "prohibited tool"],
            ["self-harm", "bullying", "harassment", "harmful content"],
            ["incident response", "risk response", "safety incident", "safety protocol"],
            ["companion", "social ai", "well-being", "sb 243", "mental health"],
            ["report", "staff report", "harmful content report"],
        ],
        "EQUITY": [
            ["bias", "bias evaluation", "bias assessment", "bias audit"],
            ["equitable access", "all students", "across schools", "equity"],
            ["disparate impact", "monitor", "equity monitoring", "outcome"],
            ["iep", "504", "disability", "accommodation"],
            ["equity review", "annual equity", "outcome review"],
        ],
        "VENDOR": [
            ["vetting", "procurement", "evaluation process", "review process"],
            ["contract", "data deletion", "audit right", "vendor contract"],
            ["evidence", "evidence-based", "peer-reviewed", "essa"],
            ["registry", "centrally", "vendor registry", "approved vendor"],
            ["sopipa", "coppa", "ferpa", "ab 1584", "ed code 49073"],
        ],
        "INST": [
            ["educator discretion", "teacher discretion", "assignment level", "per assignment"],
            ["support", "not replace", "educator judgment", "professional judgment"],
            ["model", "teacher model", "demonstrate", "modeling"],
            ["curriculum", "redesign", "integrate ai", "ai literacy objective"],
        ],
        "LIT": [
            ["ai literacy", "artificial intelligence literacy", "literacy objective"],
            ["how ai works", "training data", "how ai is built", "ai systems"],
            ["grade level", "developmentally", "age appropriate", "grade-appropriate"],
            ["critical", "evaluate", "critically evaluate", "evaluate ai content"],
        ],
        "PD": [
            ["professional development", "training", "pd", "before deployment"],
            ["ethics", "ethical use", "bias awareness", "responsible use"],
            ["ongoing", "continuous", "not one-time", "annual training"],
            ["classified", "all staff", "role appropriate", "differentiated"],
        ],
    }

    for domain_key, element_kws in keyword_map.items():
        domain_results = {}
        domain = DOMAINS[domain_key]
        for i, kws in enumerate(element_kws):
            element_text = domain["required_elements"][i] if i < len(domain["required_elements"]) else f"Element {i+1}"
            found = any(kw in text_lower for kw in kws)
            # Partial: some related terms but not the core phrase
            partial_kws = kws[:1]
            partial = any(kw.split()[0] in text_lower for kw in partial_kws) if not found else False
            if found:
                domain_results[element_text] = "Fully addressed"
            elif partial:
                domain_results[element_text] = "Partially addressed"
            else:
                domain_results[element_text] = "Not addressed"
        results[domain_key] = domain_results

    return results

# ── CSS ───────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: {CA_LIGHT}; }}
    h1, h2, h3 {{ color: {CA_DARK}; }}
    .ca-header {{
        background: linear-gradient(135deg, {CA_BLUE} 0%, {CA_DARK} 100%);
        color: white; padding: 24px 32px; border-radius: 10px;
        margin-bottom: 24px;
    }}
    .ca-header h1 {{ color: white; margin: 0; font-size: 1.8em; }}
    .ca-header p  {{ color: #cce0ff; margin: 4px 0 0 0; font-size: 0.95em; }}
    .domain-card {{
        border: 2px solid {CA_BLUE}; border-radius: 8px;
        padding: 14px; margin: 8px 0; background: white;
    }}
    .domain-card h4 {{ color: {CA_BLUE}; margin: 0 0 4px 0; }}
    .gap-card {{
        border-left: 4px solid {CA_RED}; background: #fff5f5;
        padding: 10px 14px; border-radius: 0 6px 6px 0; margin: 6px 0;
    }}
    .ok-card {{
        border-left: 4px solid {CA_GREEN}; background: #f5fff7;
        padding: 10px 14px; border-radius: 0 6px 6px 0; margin: 6px 0;
    }}
    .warn-card {{
        border-left: 4px solid {CA_GOLD}; background: #fffdf0;
        padding: 10px 14px; border-radius: 0 6px 6px 0; margin: 6px 0;
    }}
    div[data-testid="stMetricValue"] {{ color: {CA_BLUE}; }}
    </style>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — POLICY GENERATOR
# ══════════════════════════════════════════════════════════════════════════
def tab_generator():
    st.markdown(f"""
    <div style="border-left:4px solid {CA_GOLD}; padding: 8px 16px;
         background:white; border-radius:0 8px 8px 0; margin-bottom:20px;">
      <strong>Guided self-assessment</strong> — answer questions for each domain,
      customize model language, and export a board-ready AI policy document
      anchored to SB 1288, AB 2225, and the CDE Model Policy.
    </div>
    """, unsafe_allow_html=True)

    step = st.session_state.gen_step

    # ── sidebar progress ──
    with st.sidebar:
        st.markdown(f"**Generator Progress**")
        done_count = sum(1 for v in st.session_state.domain_done.values() if v)
        st.progress(done_count / len(DOMAIN_KEYS))
        st.caption(f"{done_count} of {len(DOMAIN_KEYS)} domains complete")
        st.divider()
        if st.button("District Info", use_container_width=True):
            st.session_state.gen_step = "district"; st.rerun()
        for k, d in DOMAINS.items():
            done = st.session_state.domain_done[k]
            icon = "✓" if done else "○"
            label = f"{icon} {d['short']}"
            if st.button(label, key=f"nav_gen_{k}", use_container_width=True):
                st.session_state.gen_step = f"domain_{k}"; st.rerun()
        st.divider()
        if st.button("Review & Export", use_container_width=True):
            st.session_state.gen_step = "review"; st.rerun()

    if step == "district":
        _gen_district()
    elif step.startswith("domain_"):
        _gen_domain(step.split("_", 1)[1])
    elif step == "review":
        _gen_review()


def _gen_district():
    st.subheader("District Information")
    d = st.session_state.district

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("District Name", value=d.get("name", ""))
        county = st.selectbox("County", [""] + [
            "Alameda","Alpine","Amador","Butte","Calaveras","Colusa",
            "Contra Costa","Del Norte","El Dorado","Fresno","Glenn",
            "Humboldt","Imperial","Inyo","Kern","Kings","Lake","Lassen",
            "Los Angeles","Madera","Marin","Mariposa","Mendocino","Merced",
            "Modoc","Mono","Monterey","Napa","Nevada","Orange","Placer",
            "Plumas","Riverside","Sacramento","San Benito","San Bernardino",
            "San Diego","San Francisco","San Joaquin","San Luis Obispo",
            "San Mateo","Santa Barbara","Santa Clara","Santa Cruz","Shasta",
            "Sierra","Siskiyou","Solano","Sonoma","Stanislaus","Sutter",
            "Tehama","Trinity","Tulare","Tuolumne","Ventura","Yolo","Yuba",
        ])
    with col2:
        enrollment = st.number_input("Student Enrollment", min_value=0,
                                     value=d.get("enrollment", 0))
        contact = st.text_input("Primary Contact", value=d.get("contact", ""))

    email = st.text_input("Contact Email", value=d.get("email", ""))

    if st.button("Save & Begin Assessment", type="primary"):
        st.session_state.district = {
            "name": name, "county": county,
            "enrollment": enrollment, "contact": contact, "email": email,
        }
        st.session_state.gen_step = f"domain_{DOMAIN_KEYS[0]}"
        st.rerun()


def _gen_domain(key):
    if key not in DOMAINS:
        st.error(f"Unknown domain: {key}"); return

    domain = DOMAINS[key]
    idx    = DOMAIN_KEYS.index(key)

    st.subheader(f"Domain {idx+1} of {len(DOMAIN_KEYS)}: {domain['title']}")
    st.caption(f"Authority: {domain['authority']}")
    st.write(domain["description"])

    st.markdown("#### Model Policy Language")
    st.info(domain["model_language"])

    st.markdown("#### Current Status Assessment")
    responses = st.session_state.responses[key]
    for i, q in enumerate(domain["questions"]):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(q)
        with col2:
            val = st.selectbox(
                q, SCORE_OPTIONS,
                index=SCORE_OPTIONS.index(responses.get(f"q{i}", "Not addressed")),
                key=f"gen_{key}_q{i}", label_visibility="collapsed",
            )
            responses[f"q{i}"] = val
    st.session_state.responses[key] = responses

    st.markdown("#### District-Specific Language (optional)")
    st.caption("Customize the model language for your district. Leave blank to use the model text.")
    custom = st.text_area(
        "Custom language", height=140,
        value=st.session_state.custom_lang.get(key, ""),
        key=f"custom_{key}", label_visibility="collapsed",
    )
    st.session_state.custom_lang[key] = custom

    col1, col2, col3 = st.columns(3)
    with col1:
        if idx > 0 and st.button(f"< {DOMAINS[DOMAIN_KEYS[idx-1]]['short']}"):
            st.session_state.gen_step = f"domain_{DOMAIN_KEYS[idx-1]}"; st.rerun()
    with col2:
        if st.button("Mark Complete", type="primary"):
            st.session_state.domain_done[key] = True
            next_idx = idx + 1
            if next_idx < len(DOMAIN_KEYS):
                st.session_state.gen_step = f"domain_{DOMAIN_KEYS[next_idx]}"
            else:
                st.session_state.gen_step = "review"
            st.rerun()
    with col3:
        if idx < len(DOMAIN_KEYS) - 1 and st.button(f"{DOMAINS[DOMAIN_KEYS[idx+1]]['short']} >"):
            st.session_state.gen_step = f"domain_{DOMAIN_KEYS[idx+1]}"; st.rerun()


def _gen_review():
    st.subheader("Review & Export")
    d = st.session_state.district
    pct = overall_pct(st.session_state.responses)

    col1, col2, col3 = st.columns(3)
    col1.metric("District", d.get("name", "—"))
    col2.metric("Domains Complete", f"{sum(st.session_state.domain_done.values())}/{len(DOMAIN_KEYS)}")
    col3.metric("Self-Assessment Score", f"{pct}%")
    st.progress(pct / 100)
    st.divider()

    # Per-domain summary
    for key, domain in DOMAINS.items():
        responses = st.session_state.responses[key]
        done = st.session_state.domain_done[key]
        fully = sum(1 for v in responses.values() if v == "Fully addressed")
        total_q = len(domain["questions"])
        st.markdown(
            f'<div class="domain-card"><h4>{domain["title"]}</h4>'
            f'Status: {"✓ Complete" if done else "Incomplete"} &nbsp;|&nbsp; '
            f'{fully}/{total_q} questions fully addressed</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("Generate Board-Ready Policy Document")

    if st.button("Generate AI Policy Document", type="primary"):
        doc = _build_policy_doc()
        st.text_area("Policy Document", value=doc, height=500)
        fname = f"AI_Policy_{d.get('name','District').replace(' ','_')}_{date.today():%Y%m%d}.txt"
        st.download_button("Download Policy Document", data=doc,
                           file_name=fname, mime="text/plain")


def _build_policy_doc():
    d   = st.session_state.district
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "=" * 72,
        "          ARTIFICIAL INTELLIGENCE POLICY",
        "     California SB 1288 / AB 2225 Compliant — Board Ready",
        "=" * 72,
        "",
        f"DISTRICT : {d.get('name','[District Name]')}",
        f"COUNTY   : {d.get('county','[County]')}",
        f"DATE     : {date.today():%B %d, %Y}",
        f"PREPARED : COMPLY-CA — H-EDU.Solutions",
        "",
        "LEGAL ANCHORS: SB 1288 | AB 2225 | CDE Model Policy (26 Principles)",
        "               CPPA ADMT Regulations | Ed Code 49073.1 | SOPIPA",
        "               FERPA | COPPA | IDEA | Title VI | Title IX",
        "",
    ]
    for i, (key, domain) in enumerate(DOMAINS.items(), 1):
        lang = st.session_state.custom_lang.get(key, "").strip() or domain["model_language"]
        lines += [
            "=" * 72,
            f"SECTION {i}: {domain['title'].upper()}",
            f"Authority: {domain['authority']}",
            "=" * 72,
            lang,
            "",
        ]
    lines += [
        "=" * 72,
        "CERTIFICATION",
        "=" * 72,
        "",
        "This policy was developed in compliance with California Senate Bill 1288,",
        "Assembly Bill 2225, and the model policy guidance issued by the California",
        "Department of Education AI in Education Working Group.",
        "",
        f"Generated by COMPLY-CA (H-EDU.Solutions) on {now}",
        "This document is for informational purposes. Consult district legal",
        "counsel before board adoption.",
        "=" * 72,
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — POLICY ANALYZER
# ══════════════════════════════════════════════════════════════════════════
def tab_analyzer():
    st.markdown(f"""
    <div style="border-left:4px solid {CA_GOLD}; padding: 8px 16px;
         background:white; border-radius:0 8px 8px 0; margin-bottom:20px;">
      <strong>Paste or upload your district's existing AI policy</strong> — the
      analyzer scores it against all 11 California criteria domains and produces
      a prioritized gap report anchored to SB 1288, AB 2225, and the CDE Model Policy.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### Step 1 — Provide Policy Text")
    input_method = st.radio("Input method", ["Paste text", "Upload .txt file"],
                            horizontal=True, label_visibility="collapsed")

    policy_text = ""
    if input_method == "Paste text":
        policy_text = st.text_area(
            "Paste your policy text here", height=250,
            value=st.session_state.analyzer_text,
            placeholder="Paste the full text of your district's AI/technology policy...",
            label_visibility="collapsed",
        )
        st.session_state.analyzer_text = policy_text
    else:
        uploaded = st.file_uploader("Upload policy (.txt)", type=["txt"])
        if uploaded:
            policy_text = uploaded.read().decode("utf-8", errors="replace")
            st.session_state.analyzer_text = policy_text
            st.success(f"Loaded {len(policy_text):,} characters")

    if not policy_text.strip():
        st.info("Provide policy text above, then click Analyze.")
        return

    if st.button("Analyze Policy", type="primary"):
        with st.spinner("Scoring against CA criteria engine..."):
            scores = analyze_policy_text(policy_text)
        st.session_state.analyzer_scores = scores
        st.session_state.analyzer_done   = True

    if not st.session_state.analyzer_done or not st.session_state.analyzer_scores:
        return

    scores = st.session_state.analyzer_scores

    # ── summary metrics ──
    st.divider()
    st.subheader("Analysis Results")

    all_elements = []
    for domain_scores in scores.values():
        all_elements.extend(domain_scores.values())
    total   = len(all_elements)
    fully   = sum(1 for v in all_elements if v == "Fully addressed")
    partial = sum(1 for v in all_elements if v == "Partially addressed")
    missing = sum(1 for v in all_elements if v == "Not addressed")
    pct     = int(fully / total * 100) if total else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall Score",     f"{pct}%")
    col2.metric("Fully Addressed",   fully,   delta=None)
    col3.metric("Partial",           partial, delta=None)
    col4.metric("Not Addressed",     missing, delta=None)
    st.progress(pct / 100)

    st.caption(
        "**Note:** This analysis uses keyword matching as a screening tool — "
        "not a legal determination. Consult district legal counsel for compliance advice."
    )
    st.divider()

    # ── per-domain results ──
    st.subheader("Domain-by-Domain Breakdown")
    tabs = st.tabs([DOMAINS[k]["short"] for k in DOMAIN_KEYS])

    for tab_widget, key in zip(tabs, DOMAIN_KEYS):
        domain        = DOMAINS[key]
        domain_scores = scores.get(key, {})
        domain_fully  = sum(1 for v in domain_scores.values() if v == "Fully addressed")
        domain_total  = len(domain_scores)
        domain_pct    = int(domain_fully / domain_total * 100) if domain_total else 0

        with tab_widget:
            st.markdown(f"**{domain['title']}** &nbsp;|&nbsp; Authority: *{domain['authority']}*")
            st.progress(domain_pct / 100)
            st.caption(f"{domain_fully}/{domain_total} elements found · {domain_pct}%")

            for element, score_label in domain_scores.items():
                css_cls = {"Fully addressed": "ok-card",
                           "Partially addressed": "warn-card",
                           "Not addressed": "gap-card"}.get(score_label, "domain-card")
                icon = {"Fully addressed": "✓",
                        "Partially addressed": "~",
                        "Not addressed": "✗"}.get(score_label, "?")
                st.markdown(
                    f'<div class="{css_cls}">'
                    f'{icon} <strong>{score_label}</strong> — {element}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Show model language as suggested fix for any gaps
            gaps = [e for e, v in domain_scores.items() if v == "Not addressed"]
            if gaps:
                with st.expander("Suggested language to close gaps"):
                    st.write(f"**Authority:** {domain['authority']}")
                    st.info(domain["model_language"])

    # ── gap report export ──
    st.divider()
    st.subheader("Export Gap Report")
    if st.button("Generate Gap Report", type="primary"):
        report = _build_gap_report(scores)
        fname  = f"CA_AI_Policy_Gap_Report_{date.today():%Y%m%d}.txt"
        st.download_button("Download Gap Report", data=report,
                           file_name=fname, mime="text/plain")


def _build_gap_report(scores):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "=" * 72,
        "    CALIFORNIA AI POLICY GAP REPORT",
        "    COMPLY-CA — H-EDU.Solutions",
        "=" * 72,
        f"Generated: {now}",
        "Anchors: SB 1288 | AB 2225 | CDE Model Policy | CPPA ADMT | Ed Code",
        "",
        "DISCLAIMER: Keyword-based screening only. Not legal advice.",
        "Consult district legal counsel before board action.",
        "",
    ]
    for key in DOMAIN_KEYS:
        domain        = DOMAINS[key]
        domain_scores = scores.get(key, {})
        fully  = sum(1 for v in domain_scores.values() if v == "Fully addressed")
        total  = len(domain_scores)
        pct    = int(fully / total * 100) if total else 0

        lines += [
            "=" * 72,
            f"{domain['title'].upper()}",
            f"Authority: {domain['authority']}",
            f"Score: {fully}/{total} ({pct}%)",
            "=" * 72,
        ]
        gaps = [(e, v) for e, v in domain_scores.items() if v != "Fully addressed"]
        ok   = [(e, v) for e, v in domain_scores.items() if v == "Fully addressed"]

        if ok:
            lines.append("ADDRESSED:")
            for e, _ in ok:
                lines.append(f"  [OK] {e}")
        if gaps:
            lines.append("GAPS / PARTIAL:")
            for e, v in gaps:
                lines.append(f"  [{v.upper()}] {e}")
            lines.append("")
            lines.append("SUGGESTED LANGUAGE:")
            lines.append(domain["model_language"])
        lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(
        page_title="COMPLY-CA | H-EDU.Solutions",
        page_icon="⚖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    inject_css()

    # Header
    st.markdown(f"""
    <div class="ca-header">
      <h1>COMPLY-CA</h1>
      <p>California AI Policy Compliance Platform &nbsp;·&nbsp; H-EDU.Solutions
         &nbsp;·&nbsp; SB 1288 &nbsp;|&nbsp; AB 2225 &nbsp;|&nbsp; CDE Model Policy</p>
    </div>
    """, unsafe_allow_html=True)

    # Tab selector
    tab_choice = st.radio(
        "Tool",
        ["Policy Generator", "Policy Analyzer"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.divider()

    if tab_choice == "Policy Generator":
        st.session_state.tab = "generator"
        tab_generator()
    else:
        st.session_state.tab = "analyzer"
        # Analyzer has no sidebar navigation — clear sidebar
        with st.sidebar:
            st.markdown(f"**COMPLY-CA**")
            st.caption("Policy Analyzer")
            st.divider()
            st.markdown("Paste or upload your district policy text, then click **Analyze Policy**.")
            st.divider()
            st.caption(f"H-EDU.Solutions · {date.today().year}")
        tab_analyzer()


if __name__ == "__main__":
    main()
