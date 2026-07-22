#!/usr/bin/env python3
"""COMPLY-CA measurable rubric — 11 domains, 44 criteria.

Each criterion has:
  id              - domain code + number (e.g. GOV1)
  module          - domain key (GOV, PRIV, TRANS, HUMAN, INTEG, SAFE, EQUITY, VENDOR, INST, LIT, PD)
  module_name     - human label
  term            - short label
  hook            - statutory hook
  pass_condition  - what must be present in the policy to satisfy this criterion
  cues            - concept groups (lists of synonyms); group met if any synonym appears
  gap_labels      - human phrase per concept group (used to state what is missing)
  revision        - original gap-fill language that satisfies the criterion
  ca_tier         - Statutory | Enacted | Guidance
  must_pass       - True for Statutory and Enacted
"""

MODULES = {
    "GOV":    "Governance & Strategy",
    "PRIV":   "Data Privacy & Security",
    "TRANS":  "Transparency & Disclosure",
    "HUMAN":  "Human Review & Automated Decisions",
    "INTEG":  "Academic Integrity",
    "SAFE":   "Acceptable Use & Student Safety",
    "EQUITY": "Nondiscrimination & Equity",
    "VENDOR": "Vendor Management & Procurement",
    "INST":   "Instructional Discretion",
    "LIT":    "AI Literacy",
    "PD":     "Professional Development",
}

TIERS = {
    "Statutory": {
        "tier": "Statutory",
        "pass_semantics": "Hard enacted requirement — directly from SB 1288, AB 2225, Ed Code, FERPA, COPPA, SOPIPA, or AB 1584. Must fully pass.",
        "must_pass": True,
    },
    "Enacted": {
        "tier": "Enacted",
        "pass_semantics": "Built to the standard set by enacted law and CDE model policy. Must pass to meet the CDE compliance threshold.",
        "must_pass": True,
    },
    "Guidance": {
        "tier": "Guidance",
        "pass_semantics": "Best-practice guidance from CDE 26 principles. Failure flagged but not a hard compliance bar.",
        "must_pass": False,
    },
}

CRITERIA = [
    # ── GOV ──────────────────────────────────────────────────────────────────
    {"id": "GOV1", "module": "GOV", "term": "Board-adopted AI strategy",
     "hook": "CDE Principle 21; SB 1288 §1(a)", "tier": "Statutory",
     "pass": "Policy is named, board-adopted, and governs district AI use.",
     "cues": [["board-adopted","board adopted","adopted by the board","board policy","board approval"],
              ["artificial intelligence","ai policy","ai strategy","ai use"]],
     "labels": ["a board-adopted instrument","governing district AI use"],
     "rev": "The Board of Education adopts this policy as the District's formal Artificial Intelligence Strategy governing the acquisition, deployment, and use of AI tools and systems."},

    {"id": "GOV2", "module": "GOV", "term": "Named AI coordinator / oversight role",
     "hook": "CDE Principle 22", "tier": "Enacted",
     "pass": "Policy designates a named role or committee responsible for AI oversight.",
     "cues": [["ai coordinator","ai oversight","responsible for ai","designat","oversight committee"],
              ["superintendent","principal","administrator","staff","official"]],
     "labels": ["a named oversight role or committee","its responsibility for AI"],
     "rev": "The Superintendent shall designate an AI Coordinator responsible for implementation, monitoring, and compliance. The AI Coordinator shall report to the Board at least annually."},

    {"id": "GOV3", "module": "GOV", "term": "Biennial review cycle",
     "hook": "CDE Principle 25", "tier": "Enacted",
     "pass": "Policy specifies a review cycle of at least every two years.",
     "cues": [["biennial","every two year","two-year","2-year","review cycle","reviewed at least"],
              ["policy","strategy","review","update"]],
     "labels": ["a biennial or more-frequent review cycle"],
     "rev": "This policy shall be reviewed biennially, or sooner upon material changes in applicable law, technology, or district AI use."},

    {"id": "GOV4", "module": "GOV", "term": "Stakeholder development process",
     "hook": "CDE Principle 21", "tier": "Guidance",
     "pass": "Policy was developed with input from educators, families, and students.",
     "cues": [["educator","teacher","staff","classified"],["family","parent","guardian"],["student","community"]],
     "labels": ["educator input","family/parent input","student or community input"],
     "rev": "This policy shall be developed and periodically revised with input from educators, classified staff, students, families, and community members."},

    # ── PRIV ─────────────────────────────────────────────────────────────────
    {"id": "PRIV1", "module": "PRIV", "term": "No student PII to train commercial models",
     "hook": "SOPIPA; Ed Code 49073.1; CDE Principle 7", "tier": "Statutory",
     "pass": "Policy prohibits using student PII to train, improve, or develop commercial AI models.",
     "cues": [["student","student data","student information","student pii","personally identifiable"],
              ["train","improve","develop","build"],["commercial","commercial model","ai model","machine learning model"]],
     "labels": ["a prohibition on student PII use","for training commercial AI models"],
     "rev": "No AI system may use student personally identifiable information (PII) to train, improve, or develop commercial AI models without explicit, informed written consent from the parent or eligible student."},

    {"id": "PRIV2", "module": "PRIV", "term": "Data Privacy Agreements required",
     "hook": "AB 1584; Ed Code 49073.1", "tier": "Statutory",
     "pass": "Policy requires a signed Data Privacy Agreement before any AI tool that processes student data is deployed.",
     "cues": [["data privacy agreement","dpa","privacy agreement","privacy contract"],
              ["before","prior to","before deployment","required"],["student data","student information","student record"]],
     "labels": ["a DPA requirement","that it precedes deployment","coverage of student data"],
     "rev": "Prior to deploying any AI tool that processes student data, the District shall execute a Data Privacy Agreement (DPA) with the vendor meeting the requirements of AB 1584 and Ed Code 49073.1."},

    {"id": "PRIV3", "module": "PRIV", "term": "Privacy impact assessment",
     "hook": "CDE Principle 9", "tier": "Enacted",
     "pass": "Policy requires a privacy impact assessment before adopting any new AI tool.",
     "cues": [["privacy impact","privacy assessment","privacy review","privacy evaluation"],
              ["before","prior to","new tool","adoption","deploy"]],
     "labels": ["a privacy impact assessment","conducted before adoption"],
     "rev": "The District shall conduct a privacy impact assessment before adopting any AI tool that accesses or processes student or staff data."},

    {"id": "PRIV4", "module": "PRIV", "term": "Data retention and deletion schedules",
     "hook": "FERPA; CDE Principle 9", "tier": "Enacted",
     "pass": "Policy defines data retention and deletion schedules for AI vendor data.",
     "cues": [["retention","deletion","destroy","purge","data schedule"],
              ["vendor","ai tool","system"],["schedule","period","timeline","years"]],
     "labels": ["defined retention periods","deletion or destruction requirements"],
     "rev": "The District shall establish data retention and deletion schedules for all AI vendor systems, consistent with FERPA and district records-management policy. Vendor contracts shall require data deletion upon contract termination."},

    {"id": "PRIV5", "module": "PRIV", "term": "Breach notification covers AI incidents",
     "hook": "Ed Code 49073.6; CDE Principle 7", "tier": "Statutory",
     "pass": "Policy's breach notification procedures explicitly cover AI system incidents.",
     "cues": [["breach","incident","security incident","data breach"],
              ["notification","notify","report"],["ai","ai system","ai tool","automated"]],
     "labels": ["breach notification procedures","covering AI system incidents"],
     "rev": "The District's breach notification procedures apply to incidents involving AI systems. Any breach or unauthorized disclosure of student data by an AI vendor shall trigger the District's standard breach notification process."},

    # ── TRANS ────────────────────────────────────────────────────────────────
    {"id": "TRANS1", "module": "TRANS", "term": "Annual parent notification of AI tools",
     "hook": "CDE Principle 10; SB 1288", "tier": "Enacted",
     "pass": "Policy requires annual notification to parents/guardians of AI tools in use.",
     "cues": [["annual","annually","each year","yearly"],
              ["parent","guardian","family"],["notif","inform","notice","disclos"]],
     "labels": ["annual notification","to parents/guardians"],
     "rev": "The District shall notify parents and guardians annually of AI tools in use in their child's educational environment, including the tool's purpose and any student data accessed."},

    {"id": "TRANS2", "module": "TRANS", "term": "Students informed when interacting with AI",
     "hook": "CDE Principle 10; SB 243", "tier": "Statutory",
     "pass": "Policy requires that students be informed when they are interacting with an AI system.",
     "cues": [["student","students"],["informed","disclose","notify","aware","told"],
              ["interacting with","talking to","using","engaging with"],["ai","artificial intelligence","ai system","chatbot","bot"]],
     "labels": ["a duty to inform students","when they interact with AI"],
     "rev": "Students shall be informed when they are interacting with an AI system. Any AI system that may interact directly with students shall identify itself as AI when asked."},

    {"id": "TRANS3", "module": "TRANS", "term": "AI identity disclosure to minors (SB 243)",
     "hook": "SB 243", "tier": "Statutory",
     "pass": "Policy requires AI systems to disclose their AI identity when asked by a minor.",
     "cues": [["sb 243","sb243"],["disclose","identify","reveal"],["ai","artificial intelligence","not human","i am an ai"],
              ["minor","student","child"]],
     "labels": ["SB 243 compliance","AI identity disclosure to minors"],
     "rev": "Consistent with SB 243, any AI system that may interact with minors shall identify itself as an AI when directly and sincerely asked, and shall not claim to be human in contexts designed to deceive."},

    {"id": "TRANS4", "module": "TRANS", "term": "Training data disclosure (AB 2013)",
     "hook": "AB 2013 (eff. Jan 1, 2026)", "tier": "Statutory",
     "pass": "Policy requires vendors to disclose training data provenance upon request, consistent with AB 2013.",
     "cues": [["ab 2013","ab2013","training data","data provenance","data source"],
              ["disclos","provide","vendor","request"]],
     "labels": ["an AB 2013 training-data disclosure requirement"],
     "rev": "The District shall require vendors to disclose training data sources and provenance upon request, consistent with AB 2013 (effective January 1, 2026)."},

    {"id": "TRANS5", "module": "TRANS", "term": "Public AI tool registry",
     "hook": "CDE Principle 10", "tier": "Enacted",
     "pass": "Policy requires a publicly accessible registry of approved AI tools.",
     "cues": [["registry","approved tool","tool list","approved list","published list"],
              ["public","publicly","available","accessible"]],
     "labels": ["an AI tool registry","publicly accessible"],
     "rev": "The District shall maintain and publish a registry of approved AI tools, including vendor name, purpose, data accessed, and applicable privacy certifications."},

    # ── HUMAN ────────────────────────────────────────────────────────────────
    {"id": "HUMAN1", "module": "HUMAN", "term": "Human review before consequential AI decisions",
     "hook": "CDE Principles 11,18,20; AB 2225", "tier": "Statutory",
     "pass": "No AI output affecting student placement, discipline, or services is implemented without qualified human review.",
     "cues": [["human review","educator review","qualified review","human oversight"],
              ["before","prior to","before implementing","before a decision"],
              ["placement","discipline","eligibility","services","significant decision","consequential"]],
     "labels": ["human review requirement","before implementation","for consequential decisions"],
     "rev": "No AI-generated recommendation shall be implemented without review by a qualified educator or administrator. Human review is mandatory before any AI output influences student placement, discipline, eligibility, or services."},

    {"id": "HUMAN2", "module": "HUMAN", "term": "Reviewer authority to override AI",
     "hook": "CDE Principle 20; AB 2225", "tier": "Statutory",
     "pass": "Policy grants reviewers explicit authority to override AI recommendations.",
     "cues": [["override","overrule","reverse","reject","modify","authority to"],
              ["ai","recommendation","output","decision","system"]],
     "labels": ["explicit override authority","over AI recommendations"],
     "rev": "Designated reviewers shall have the authority to approve, modify, or override any AI recommendation and shall not default to the system's output."},

    {"id": "HUMAN3", "module": "HUMAN", "term": "Parent right to request human review",
     "hook": "CDE Principle 18; AB 2225", "tier": "Statutory",
     "pass": "Parents/guardians may request human review of any AI-influenced education decision.",
     "cues": [["parent","guardian","family"],["request","appeal","ask for"],
              ["human review","human decision","review by","override","reconsider"]],
     "labels": ["parent/guardian right","to request human review"],
     "rev": "Parents and guardians may request human review of any AI-influenced decision affecting their child. The District shall provide a clear process for submitting such requests."},

    {"id": "HUMAN4", "module": "HUMAN", "term": "Educator sole grading authority",
     "hook": "CDE Principle 11", "tier": "Enacted",
     "pass": "Educators retain sole authority over student grades and academic advancement.",
     "cues": [["sole authority","sole grading","educator grade","teacher grade","educator alone","final grade"],
              ["grade","academic","advancement","proficiency"]],
     "labels": ["educator sole grading authority"],
     "rev": "Educators hold sole authority over student grades and academic advancement. AI tools may support assessment but shall not independently assign grades or determine academic proficiency."},

    {"id": "HUMAN5", "module": "HUMAN", "term": "ADMT opt-out and appeal path (AB 2225)",
     "hook": "AB 2225; CPPA ADMT regulations (eff. Jan 1, 2027)", "tier": "Statutory",
     "pass": "Policy provides pre-use notice, opt-out right, and appeal path for significant AI-driven education decisions.",
     "cues": [["opt-out","opt out","right to opt"],["appeal","appeal path","appeal process","challenge"],
              ["notice","pre-use notice","prior notice"],["ab 2225","admt","automated decision"]],
     "labels": ["pre-use notice","an opt-out right","an appeal path","AB 2225 compliance"],
     "rev": "Consistent with AB 2225 and the CPPA ADMT regulations (effective January 1, 2027), the District shall provide pre-use notice, opt-out rights, and a documented appeal path for significant AI-driven education decisions."},

    # ── INTEG ────────────────────────────────────────────────────────────────
    {"id": "INTEG1", "module": "INTEG", "term": "Student AI disclosure requirement",
     "hook": "CDE Principles 1,2; SB 1288 §1(b)", "tier": "Enacted",
     "pass": "Students must disclose AI use when required by the instructor.",
     "cues": [["student","students"],["disclos","cite","acknowledge","attribute"],
              ["ai","artificial intelligence","ai tool","ai-generated"],
              ["required","when required","instructor","assignment"]],
     "labels": ["a student disclosure duty","when required by instructor"],
     "rev": "Students shall disclose the use of AI tools in completing assignments when required by the instructor."},

    {"id": "INTEG2", "module": "INTEG", "term": "Undisclosed AI = academic dishonesty",
     "hook": "CDE Principle 2", "tier": "Enacted",
     "pass": "Submitting AI-generated content as original work without disclosure is defined as academic dishonesty.",
     "cues": [["academic dishonesty","dishonest","plagiarism","misconduct"],
              ["ai-generated","ai generated","original work","without disclosure","without attribution"]],
     "labels": ["academic dishonesty definition","for undisclosed AI-generated work"],
     "rev": "Submitting AI-generated content as original work without disclosure constitutes academic dishonesty subject to existing disciplinary procedures."},

    {"id": "INTEG3", "module": "INTEG", "term": "Per-assignment AI expectations",
     "hook": "CDE Principle 1", "tier": "Guidance",
     "pass": "Educators communicate AI-use expectations per assignment.",
     "cues": [["per assignment","assignment level","each assignment","for each task"],
              ["expectation","ai use","policy","communicate","clarify"]],
     "labels": ["per-assignment AI expectations"],
     "rev": "Educators shall clearly communicate expectations regarding AI use for each assignment or assessment."},

    {"id": "INTEG4", "module": "INTEG", "term": "AI detection not sole discipline basis",
     "hook": "CDE Principle 2", "tier": "Enacted",
     "pass": "AI detection tool output alone is insufficient basis for academic discipline.",
     "cues": [["detection","ai detection","detection software","ai detector"],
              ["sole basis","sole evidence","alone","not sufficient","not the only"],
              ["discipline","disciplinary","sanction","consequence"]],
     "labels": ["a prohibition on sole reliance","on AI detection tools for discipline"],
     "rev": "AI detection software shall not serve as the sole basis for academic discipline. A student shall not be disciplined for AI-generated content without corroborating evidence beyond the detection tool's output."},

    # ── SAFE ─────────────────────────────────────────────────────────────────
    {"id": "SAFE1", "module": "SAFE", "term": "Approved AI tool list maintained",
     "hook": "CDE Principles 3,4; AB 2225", "tier": "Enacted",
     "pass": "An approved AI tool list is maintained; unapproved tools are prohibited for instruction.",
     "cues": [["approved","approved tool","approved list","approved ai"],
              ["maintain","list","registry","catalog"]],
     "labels": ["an approved tool list","its maintenance"],
     "rev": "The District shall maintain an approved AI tool list. Only tools approved through the District's procurement process may be used for instruction or administrative purposes involving student data."},

    {"id": "SAFE2", "module": "SAFE", "term": "Prohibited AI uses defined",
     "hook": "CDE Principles 3,12; SB 243", "tier": "Enacted",
     "pass": "AI tools may not facilitate self-harm, bullying, harassment, or illegal activity.",
     "cues": [["self-harm","self harm","harm","bullying","harassment","illegal","abuse"],
              ["prohibited","may not","shall not","forbidden","not permitted"]],
     "labels": ["prohibited AI use categories"],
     "rev": "AI tools shall not be used to generate content that facilitates self-harm, bullying, harassment, or illegal activity, or to circumvent content filters or safety controls."},

    {"id": "SAFE3", "module": "SAFE", "term": "AI safety incident response procedure",
     "hook": "CDE Principle 19", "tier": "Enacted",
     "pass": "A clear risk-response procedure exists for AI-related safety incidents.",
     "cues": [["incident response","risk response","safety incident","safety protocol","emergency"],
              ["ai","ai-related","ai system","ai tool"]],
     "labels": ["an AI safety incident response procedure"],
     "rev": "The Superintendent shall establish a risk-response procedure for AI-related safety incidents. Staff shall report AI-generated harmful content through established incident-reporting protocols."},

    {"id": "SAFE4", "module": "SAFE", "term": "Companion/social AI well-being evaluation",
     "hook": "SB 243; CDE Principle 4", "tier": "Statutory",
     "pass": "Companion or social AI tools are evaluated for student well-being impact before deployment.",
     "cues": [["companion","social ai","companion ai","social emotional"],
              ["well-being","wellbeing","mental health"],["evaluat","assess","review","prior to"]],
     "labels": ["companion/social AI evaluation","for student well-being impact"],
     "rev": "The District shall evaluate companion or social AI tools for potential impacts on student mental health and well-being prior to deployment, consistent with SB 243."},

    # ── EQUITY ───────────────────────────────────────────────────────────────
    {"id": "EQUITY1", "module": "EQUITY", "term": "Bias evaluation before deployment",
     "hook": "CDE Principles 23,24; Title VI; Ed Code 200", "tier": "Statutory",
     "pass": "AI tools are evaluated for bias against protected classes before deployment.",
     "cues": [["bias","bias evaluation","bias assessment","bias audit","fairness"],
              ["before","prior to","before deployment","before adoption"],["protected","race","disability","english learner","gender","ethnicity"]],
     "labels": ["bias evaluation","before deployment","covering protected classes"],
     "rev": "Prior to deploying any AI tool, the District shall evaluate the tool for potential bias against students based on race, ethnicity, national origin, sex, disability, English learner status, or other protected characteristics."},

    {"id": "EQUITY2", "module": "EQUITY", "term": "Equitable access across student populations",
     "hook": "CDE Principle 24", "tier": "Enacted",
     "pass": "Equitable access to approved AI tools is ensured across all student populations.",
     "cues": [["equitable","equity","equal access","all students","across all"],
              ["ai tool","technology","access"],["school","population","group","subgroup"]],
     "labels": ["equitable access","across all student populations"],
     "rev": "The District shall ensure equitable access to beneficial AI tools across all schools and student groups."},

    {"id": "EQUITY3", "module": "EQUITY", "term": "Disparate impact monitoring",
     "hook": "CDE Principle 23; Title VI", "tier": "Enacted",
     "pass": "AI recommendations are monitored for disparate impact by race, disability, EL status.",
     "cues": [["disparate impact","disparity","disproportionate"],["monitor","review","audit","track"],
              ["race","disability","english learner","subgroup","protected"]],
     "labels": ["disparate impact monitoring","by protected class"],
     "rev": "The District shall monitor AI-generated recommendations for disparate impact on students by race, disability, English learner status, and other protected characteristics."},

    {"id": "EQUITY4", "module": "EQUITY", "term": "IEP/504 accommodations maintained",
     "hook": "IDEA; Section 504; ADA", "tier": "Statutory",
     "pass": "Disability accommodations are maintained regardless of AI system design.",
     "cues": [["iep","504","disability","accommodation","special education"],
              ["maintain","not undermine","preserved","not limit","regardless"]],
     "labels": ["IEP/504 accommodation maintenance","regardless of AI system"],
     "rev": "IEP and 504 accommodations shall be maintained and not undermined by AI system design or implementation."},

    # ── VENDOR ───────────────────────────────────────────────────────────────
    {"id": "VENDOR1", "module": "VENDOR", "term": "Formal AI vetting process",
     "hook": "CDE Principles 12,13,14; Ed Code 49073.1", "tier": "Enacted",
     "pass": "A formal AI tool vetting process exists before any classroom deployment.",
     "cues": [["vetting","vet","evaluation","review process","procurement process","approval process"],
              ["before","prior to","before deployment","before classroom"],["ai","ai tool","system","vendor"]],
     "labels": ["a formal vetting process","before classroom deployment"],
     "rev": "Before deploying any AI tool, the District shall conduct a formal evaluation including privacy review, bias assessment, and evidence-of-effectiveness review."},

    {"id": "VENDOR2", "module": "VENDOR", "term": "Contract data ownership and deletion rights",
     "hook": "AB 1584; SOPIPA; Ed Code 49073.1", "tier": "Statutory",
     "pass": "Vendor contracts include data ownership, deletion, and audit rights.",
     "cues": [["data ownership","student data","education record"],
              ["deletion","destroy","delete upon","contract termination"],["audit","audit right","inspect","access"]],
     "labels": ["data ownership terms","deletion upon termination","audit rights"],
     "rev": "Vendor contracts shall include provisions addressing student data ownership, deletion upon contract termination, and district audit rights."},

    {"id": "VENDOR3", "module": "VENDOR", "term": "Evidence base for instructional AI",
     "hook": "CDE Principle 14; ESSA", "tier": "Enacted",
     "pass": "AI tools used for instruction have an evidence base for educational effectiveness.",
     "cues": [["evidence","evidence-based","peer-reviewed","research","essa","effectiveness"],
              ["instructional","instruction","classroom","learning","educational"]],
     "labels": ["an evidence base requirement","for instructional AI tools"],
     "rev": "AI tools used for academic instruction shall have peer-reviewed evidence of educational effectiveness, or shall be piloted under monitored conditions consistent with ESSA evidence standards."},

    {"id": "VENDOR4", "module": "VENDOR", "term": "Approved vendor registry",
     "hook": "CDE Principle 12", "tier": "Enacted",
     "pass": "An approved vendor registry is centrally maintained and publicly accessible.",
     "cues": [["vendor registry","approved vendor","vendor list"],["centrally","public","publicly","accessible"]],
     "labels": ["a centrally maintained vendor registry","publicly accessible"],
     "rev": "The District shall maintain a centrally-managed, publicly-accessible registry of approved AI tools including vendor, purpose, data elements accessed, privacy certification status, and contract renewal date."},

    {"id": "VENDOR5", "module": "VENDOR", "term": "CA student privacy law compliance verified",
     "hook": "SOPIPA; AB 1584; Ed Code 49073.1", "tier": "Statutory",
     "pass": "Vendor compliance with CA student privacy law is verified before contract execution.",
     "cues": [["sopipa","ab 1584","ed code 49073","student privacy","privacy law"],
              ["verif","confirm","certif","comply","compliant"]],
     "labels": ["CA student privacy law verification","before contract"],
     "rev": "The District shall verify vendor compliance with SOPIPA, AB 1584, and Ed Code 49073.1 before executing any AI vendor contract."},

    # ── INST ─────────────────────────────────────────────────────────────────
    {"id": "INST1", "module": "INST", "term": "Educator assignment-level AI discretion",
     "hook": "CDE Principles 5,6", "tier": "Enacted",
     "pass": "Educators may authorize or restrict AI use at the assignment level.",
     "cues": [["educator discretion","teacher discretion","per assignment","assignment level","each assignment"],
              ["authorize","permit","restrict","prohibit","allow"]],
     "labels": ["educator assignment-level discretion"],
     "rev": "Educators retain full discretion to authorize, limit, or prohibit the use of AI tools for any specific assignment or assessment."},

    {"id": "INST2", "module": "INST", "term": "AI supports, not replaces, educator judgment",
     "hook": "CDE Principles 15,16", "tier": "Guidance",
     "pass": "AI tools are positioned as supports for — not replacements of — educator judgment.",
     "cues": [["support","assist","enhance","augment"],["not replace","not a replacement","professional judgment","educator judgment","teacher judgment"]],
     "labels": ["AI as a support tool","not a replacement for educator judgment"],
     "rev": "AI tools shall be used to support educator effectiveness — for planning, differentiation, feedback, and efficiency — not to replace professional judgment."},

    # ── LIT ──────────────────────────────────────────────────────────────────
    {"id": "LIT1", "module": "LIT", "term": "AI literacy as learning objective",
     "hook": "CDE Principle 17; Ed Code 33548", "tier": "Enacted",
     "pass": "AI literacy is included as a learning objective across grade levels.",
     "cues": [["ai literacy","artificial intelligence literacy","literacy objective"],
              ["learning objective","curriculum","standard","competency"]],
     "labels": ["AI literacy as a learning objective"],
     "rev": "The District shall ensure that all students develop foundational AI literacy appropriate to their grade level, treated as a core 21st-century competency."},

    {"id": "LIT2", "module": "LIT", "term": "Students learn how AI works",
     "hook": "CDE Principle 17", "tier": "Guidance",
     "pass": "Students learn how AI systems work, including training data and bias.",
     "cues": [["how ai works","training data","how ai is built","ai systems work","how it works"],
              ["bias","limitation","hallucination","error","inaccuracy"]],
     "labels": ["instruction on how AI works","including bias and limitations"],
     "rev": "AI literacy instruction shall include how AI systems are built and trained, the potential for bias, error, and hallucination, and how to critically evaluate AI-generated content."},

    # ── PD ───────────────────────────────────────────────────────────────────
    {"id": "PD1", "module": "PD", "term": "PD required before AI tool deployment",
     "hook": "CDE Principle 26", "tier": "Enacted",
     "pass": "Professional development is provided before any new AI tool is deployed to staff.",
     "cues": [["professional development","training","pd","before deployment","prior to deployment"],
              ["new tool","new ai","ai tool","before any","before deploying"]],
     "labels": ["PD before AI tool deployment"],
     "rev": "No AI tool shall be deployed for staff or student use without accompanying professional development covering the tool's purpose, privacy obligations, and ethical use."},

    {"id": "PD2", "module": "PD", "term": "PD covers ethics, bias, safety",
     "hook": "CDE Principle 26", "tier": "Enacted",
     "pass": "PD covers ethical use, bias awareness, and student safety considerations.",
     "cues": [["ethics","ethical use","responsible use"],["bias","bias awareness"],
              ["student safety","safety","student protection"]],
     "labels": ["ethics coverage","bias awareness","student safety"],
     "rev": "Professional development shall cover ethical and responsible use of AI, bias awareness, student privacy and data security obligations, and student safety protocols."},

    {"id": "PD3", "module": "PD", "term": "PD is ongoing, not one-time",
     "hook": "CDE Principle 26", "tier": "Guidance",
     "pass": "PD is ongoing — not a one-time event.",
     "cues": [["ongoing","continuous","annual","recurring","not one-time","repeated"]],
     "labels": ["ongoing PD (not one-time)"],
     "rev": "Professional development on AI shall be ongoing and updated as tools, laws, and best practices evolve — not a one-time event."},

    {"id": "PD4", "module": "PD", "term": "Classified staff receive AI training",
     "hook": "CDE Principle 26", "tier": "Guidance",
     "pass": "Classified staff receive AI training appropriate to their roles.",
     "cues": [["classified","classified staff","all staff","paraprofessional"],
              ["training","pd","professional development"]],
     "labels": ["classified staff coverage","in AI training"],
     "rev": "Classified staff, certificated educators, and administrators shall each receive role-appropriate AI training. The District shall document completion and evaluate PD effectiveness annually."},
]


def build_rubric() -> list[dict]:
    out = []
    for c in CRITERIA:
        tier_data = TIERS[c["tier"]]
        item = {
            "id": c["id"],
            "module": c["module"],
            "module_name": MODULES[c["module"]],
            "term": c["term"],
            "hook": c["hook"],
            "ca_tier": tier_data["tier"],
            "ag_test_tier": tier_data["tier"],   # shared key so engine works unchanged
            "pass_semantics": tier_data["pass_semantics"],
            "must_pass": tier_data["must_pass"],
            "context_only": False,
            "pass_condition": c["pass"],
            "cues": c["cues"],
            "gap_labels": c["labels"],
            "revision": c["rev"],
        }
        out.append(item)
    return out


if __name__ == "__main__":
    import json
    r = build_rubric()
    measured = [x for x in r if not x["context_only"]]
    print(f"CA rubric: {len(r)} criteria, {len(measured)} measurable")
    by_tier = {}
    for x in r:
        by_tier.setdefault(x["ca_tier"], 0)
        by_tier[x["ca_tier"]] += 1
    for t, n in sorted(by_tier.items()):
        print(f"  {t}: {n}")
