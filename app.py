import streamlit as st
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime

# Check whether reportlab is available
try:
    import reportlab
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ---------------------------------------------------------
# Helper functions for scoring
# ---------------------------------------------------------

def yes_no_score(answer: str, yes_value: int = 100, no_value: int = 0) -> float:
    """Map a Yes/No answer to a numeric score."""
    return yes_value if answer == "Yes" else no_value


def frequency_score(freq: str) -> float:
    """
    Map reporting / simulation frequency to a maturity score.
    Higher frequency => higher score.
    """
    mapping = {
        "Ad hoc / not defined": 20,
        "Annually": 40,
        "Quarterly": 70,
        "Monthly": 90,
        "Weekly or more often": 100,
    }
    return mapping.get(freq, 0)


def backup_frequency_score(freq: str) -> float:
    """Score backup frequency."""
    mapping = {
        "No regular backups": 0,
        "Monthly": 40,
        "Weekly": 70,
        "Daily or more often": 100,
    }
    return mapping.get(freq, 0)


def sector_inherent_risk_score(sectors) -> float:
    """
    Compute an inherent risk score based on sectors of activity.
    Higher inherent risk -> lower score.
    We convert risk_factor in [0,1] to score = (1 - risk_factor)*100.
    """
    if not sectors:
        # No sensitive sector selected -> assume low inherent risk
        return 100.0

    # Risk factor per sector (1 = very high risk)
    risk_map = {
        "Water and Energy (electricity, gas, oil, water)": 0.9,
        "Financial institution (bank, insurance, microfinance, collection, etc.)": 0.9,
        "Sports betting / gambling": 0.8,
        "Telecommunications / new technologies": 0.85,
        "Healthcare / medical / provident fund": 0.9,
        "Commerce / agro-industry": 0.7,
        "Other": 0.6,
    }

    factors = [risk_map.get(s, 0.6) for s in sectors]
    avg_factor = sum(factors) / len(factors)
    return max(0, (1 - avg_factor) * 100)


def data_sensitivity_score(selected_types) -> float:
    """
    More categories of sensitive data => higher exposure => lower score.
    We keep it simple: score = (1 - n_types / max_types)*100.
    """
    max_types = 6  # number of options
    n = len(selected_types)
    exposure = min(1.0, n / max_types)
    return max(0, (1 - exposure) * 100)


def coverage_awareness_score(options) -> float:
    """
    Interpret broader requested coverage as a proxy for awareness and maturity.
    More options selected => higher score.
    """
    max_opts = 7  # number of options
    n = len(options)
    return (n / max_opts) * 100 if max_opts > 0 else 0


# Section weights (sum to 1.0)
SECTION_WEIGHTS = {
    "B": 0.10,  # Data & sensitive information
    "C": 0.20,  # Organisation & security policies
    "D": 0.20,  # Infrastructure & IT controls
    "E": 0.15,  # Incident response & history
    "F": 0.05,  # Sector activities & exposures
    "G": 0.05,  # Coverage requested (risk awareness)
    "H": 0.10,  # Third-party & supplier security
    "I": 0.05,  # Security indicators & KPIs
    "J": 0.05,  # Tests & audits
    "K": 0.03,  # Awareness & security culture
    "L": 0.02,  # Mobile devices & BYOD
}


# ---------------------------------------------------------
# Scoring logic
# ---------------------------------------------------------

def calculate_section_scores(responses: dict) -> dict:
    """
    Given all questionnaire responses, compute a score per section B–L.
    Each section score is in [0, 100].
    """
    scores = {}

    # ----- Section B: Data and sensitive information -----
    b_score = data_sensitivity_score(responses["B_types"])
    scores["B"] = b_score

    # ----- Section C: Organisation and security policies -----
    c_items = []
    c_items.append(yes_no_score(responses["C_infosec_policy"]))      # formal infosec policy
    c_items.append(yes_no_score(responses["C_privacy_policy"]))      # up-to-date privacy policy
    c_items.append(yes_no_score(responses["C_training"]))            # regular cyber training
    c_items.append(yes_no_score(responses["C_encryption"]))          # electronic data encrypted
    c_items.append(yes_no_score(responses["C_access_revocation"]))   # prompt access revocation
    c_items.append(yes_no_score(responses["C_pentesting"]))          # periodic penetration/vuln tests
    c_items.append(yes_no_score(responses["C_patch_management"]))    # quick remediation of vulnerabilities
    scores["C"] = sum(c_items) / len(c_items)

    # ----- Section D: Infrastructure & IT controls -----
    d_items = []
    d_items.append(yes_no_score(responses["D_firewall_ids"]))        # firewalls & IDS/IPS
    d_items.append(yes_no_score(responses["D_malware_protection"]))  # malware protection
    d_items.append(yes_no_score(responses["D_mfa"]))                 # multi-factor auth
    d_items.append(yes_no_score(responses["D_endpoint_security"]))   # endpoint protection
    d_items.append(backup_frequency_score(responses["D_backup_freq"]))  # backup frequency
    scores["D"] = sum(d_items) / len(d_items)

    # ----- Section E: Incident response & history -----
    e_items = []
    e_items.append(yes_no_score(responses["E_ir_plan"]))  # incident response plan
    # Incidents in last 5 years (No is better)
    e_items.append(yes_no_score(responses["E_incidents_5y"], yes_value=100, no_value=40))
    # Events that could lead to a claim (No is better)
    e_items.append(yes_no_score(responses["E_potential_claims"], yes_value=100, no_value=30))
    scores["E"] = sum(e_items) / len(e_items)

    # ----- Section F: Activities & professional exposures -----
    scores["F"] = sector_inherent_risk_score(responses["F_sectors"])

    # ----- Section G: Coverage requested -----
    scores["G"] = coverage_awareness_score(responses["G_options"])

    # ----- Section H: Supplier & third-party security -----
    h_items = []
    h_items.append(yes_no_score(responses["H_supplier_access"], yes_value=70, no_value=100))
    h_items.append(yes_no_score(responses["H_thirdparty_policy"]))
    h_items.append(yes_no_score(responses["H_contract_clauses"]))
    h_items.append(yes_no_score(responses["H_update_policy"]))
    scores["H"] = sum(h_items) / len(h_items)

    # ----- Section I: Security indicators & monitoring -----
    i_items = []
    i_items.append(yes_no_score(responses["I_dashboards"]))
    i_items.append(frequency_score(responses["I_reporting_freq"]))
    scores["I"] = sum(i_items) / len(i_items)

    # ----- Section J: Tests & audits -----
    j_items = []
    j_items.append(yes_no_score(responses["J_external_audit"]))
    j_items.append(yes_no_score(responses["J_results_to_management"]))
    scores["J"] = sum(j_items) / len(j_items)

    # ----- Section K: Awareness & security culture -----
    k_items = []
    k_items.append(yes_no_score(responses["K_risky_behaviour_policy"]))
    k_items.append(yes_no_score(responses["K_phishing_sims"]))
    k_items.append(frequency_score(responses["K_phishing_freq"]))
    scores["K"] = sum(k_items) / len(k_items)

    # ----- Section L: Mobile devices & BYOD -----
    l_items = []
    l_items.append(yes_no_score(responses["L_byod_policy"]))
    l_items.append(yes_no_score(responses["L_personal_device_security"]))
    scores["L"] = sum(l_items) / len(l_items)

    return scores


def calculate_overall_score(section_scores: dict) -> float:
    """
    Weighted average of section scores according to SECTION_WEIGHTS.
    """
    total = 0.0
    for sec, weight in SECTION_WEIGHTS.items():
        total += section_scores.get(sec, 0) * weight
    return total


def risk_label(score: float) -> str:
    """Simple interpretation of the overall score."""
    if score >= 80:
        return "Strong cyber security posture"
    elif score >= 60:
        return "Moderate cyber security posture"
    elif score >= 40:
        return "Weak cyber security posture"
    else:
        return "High cyber risk / very weak posture"


# ---------------------------------------------------------
# PDF generation helpers
# ---------------------------------------------------------

def _wrap_text(text: str, max_chars: int = 90):
    """Simple word-wrap to avoid overflowing PDF lines."""
    words = str(text).split()
    lines = []
    line = ""
    for w in words:
        if len(line) + len(w) + 1 <= max_chars:
            line = f"{line} {w}".strip()
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def generate_pdf(all_answers: dict, section_scores: dict, overall: float, label: str) -> BytesIO:
    """
    Generate a PDF report with overall score, section scores and questionnaire answers.
    Returns a BytesIO buffer containing the PDF.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Fixed timestamp for this report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    def draw_header_footer():
        """Draw Cybastion/Riskare header and footer with date & confidentiality."""
        # Header
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height - 40, "Cybastion")
        c.drawRightString(width - 40, height - 40, "Riskare")

        # Footer
        footer_y = 30
        c.setFont("Helvetica", 8)
        c.drawString(40, footer_y, f"Generated on {timestamp}")
        c.drawRightString(width - 40, footer_y, "Confidential – for internal use only")

    # First page header/footer
    draw_header_footer()

    # Title
    y = height - 80
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "Cyber Security Assessment Report")

    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Overall Score: {overall:.1f} / 100 ({label})")
    y -= 20

    # Section scores
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Section Scores")
    y -= 18

    c.setFont("Helvetica", 10)
    for sec in sorted(section_scores.keys()):
        c.drawString(50, y, f"Section {sec}: {section_scores[sec]:.1f} / 100")
        y -= 14

        if y < 80:
            c.showPage()
            draw_header_footer()
            y = height - 80
            c.setFont("Helvetica", 10)

    # Questionnaire responses
    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Questionnaire Responses")
    y -= 18

    c.setFont("Helvetica", 9)
    for key, value in all_answers.items():
        if isinstance(value, list):
            display_value = ", ".join(value) if value else "None"
        else:
            display_value = value if value not in ("", None) else "None"

        text_line = f"{key}: {display_value}"

        for line in _wrap_text(text_line, max_chars=95):
            c.drawString(50, y, line)
            y -= 12

            if y < 60:
                c.showPage()
                draw_header_footer()
                y = height - 80
                c.setFont("Helvetica", 9)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------

def main():
    st.set_page_config(page_title="Cyber Security Scoring", layout="centered")

    # ---------- Custom CSS ----------
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 960px;
            padding-top: 2rem;
            margin: 0 auto;
        }

        /* Big primary button */
        .stButton > button {
            background: linear-gradient(90deg, #1f77b4, #4dabf7);
            color: white;
            padding: 0.8rem 1.8rem;
            border-radius: 999px;
            border: none;
            font-size: 1.1rem;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(31, 119, 180, 0.35);
        }
        .stButton > button:hover {
            filter: brightness(1.05);
            box-shadow: 0 6px 16px rgba(31, 119, 180, 0.45);
        }

        /* Score card */
        .score-card {
            border-radius: 16px;
            padding: 1.5rem 1.75rem;
            margin-top: 1.5rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
            border-left: 6px solid transparent;
        }
        .score-card-title {
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            opacity: 0.7;
            margin-bottom: 0.25rem;
        }
        .score-card-value {
            font-size: 2.4rem;
            font-weight: 700;
            line-height: 1.1;
        }
        .score-card-label {
            margin-top: 0.5rem;
            font-size: 1rem;
        }
        .score-subtext {
            margin-top: 0.75rem;
            font-size: 0.9rem;
            opacity: 0.88;
        }
        .score-good {
            background: #e6f4ea;
            border-left-color: #1e8e3e;
        }
        .score-medium {
            background: #fff8e1;
            border-left-color: #fbbc04;
        }
        .score-low {
            background: #fce8e6;
            border-left-color: #d93025;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------- HEADER WITH "LOGOS" AND TITLE ----------
    header_cols = st.columns([1, 2, 1])

    with header_cols[0]:
        # Placeholder for Cybastion logo
        st.markdown(
            "<div style='margin-top: 0.4rem; font-weight: 700; font-size: 1.1rem;'>Cybastion</div>",
            unsafe_allow_html=True,
        )

    with header_cols[2]:
        # Placeholder for Riskare logo
        st.markdown(
            "<div style='text-align: right; margin-top: 0.4rem; font-weight: 700; font-size: 1.1rem;'>Riskare</div>",
            unsafe_allow_html=True,
        )

    # Centered main title
    st.markdown(
        "<h1 style='text-align: center; margin-top: 0.4rem; margin-bottom: 0.6rem;'>Cyber Security Scoring App</h1>",
        unsafe_allow_html=True,
    )

    # ---------- ABOUT THIS ASSESSMENT BOX ----------
    st.markdown(
        """
        <div style="
            margin: 0.5rem 0 1.5rem 0;
            padding: 0.85rem 1.1rem;
            border-radius: 12px;
            background: #f5f5f7;
            border: 1px solid #e5e7eb;
            font-size: 0.95rem;
        ">
            <strong>About this assessment</strong><br/>
            This cyber security scoring app provides an general view of your organisation's cyber security posture,
            based on governance, technical controls, incident preparedness and user awareness.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write(
        """
- **Questionnaire**: Complete the questions about your organisation.  
- **Cyber Security Score Calculation**: Click the button to compute your cyber security score.  
- **Export PDF Report**: Download a PDF summary of your responses and score.
        """
    )

    # ---------- SECTION 1: QUESTIONNAIRE ----------
    st.markdown("## 1. Questionnaire")

    # A. General Information (not scored)
    st.header("A. General Information")
    a_company_name = st.text_input("Legal entity name")
    a_address = st.text_input("Registered office address")
    a_websites = st.text_input("Website(s) / Domain(s)")
    a_activity = st.text_area("Description of activity")
    a_employees = st.text_input("Number of employees")
    a_revenue = st.text_input("Annual turnover (last financial year, currency)")
    a_years = st.text_input("Years in operation")
    a_contact = st.text_area(
        "Primary cybersecurity contact (Name, Role, Email, Phone)"
    )

    # B. Data & sensitive information
    st.header("B. Data and Sensitive Information")
    b_types = st.multiselect(
        "What types of sensitive information do you store or process? (select all that apply)",
        options=[
            "Payment cards / debit / Mobile Money information",
            "Medical records",
            "Financial accounts",
            "Official ID documents or other identity information",
            "Intellectual property",
            "Other sensitive data",
        ],
    )

    # C. Organisation and security policies
    st.header("C. Organisation and Security Policies")
    c_infosec_policy = st.radio(
        "Do you have a formal information security policy?",
        options=["Yes", "No"],
        horizontal=True,
    )
    c_privacy_policy = st.radio(
        "Do you have an up-to-date privacy policy?",
        options=["Yes", "No"],
        horizontal=True,
    )
    c_training = st.radio(
        "Do employees receive regular cybersecurity awareness training?",
        options=["Yes", "No"],
        horizontal=True,
    )
    c_encryption = st.radio(
        "Are electronic data encrypted (at rest and/or in transit)?",
        options=["Yes", "No"],
        horizontal=True,
    )
    c_encryption_details = st.text_input(
        "If yes, specify media/systems where encryption is used"
    )
    c_access_revocation = st.radio(
        "Are user access rights removed promptly when staff leave or change roles?",
        options=["Yes", "No"],
        horizontal=True,
    )
    c_pentesting = st.radio(
        "Do you perform periodic penetration tests or vulnerability assessments?",
        options=["Yes", "No"],
        horizontal=True,
    )
    c_patch_management = st.radio(
        "Are identified vulnerabilities corrected quickly (patch management process)?",
        options=["Yes", "No"],
        horizontal=True,
    )

    # D. Infrastructure and IT controls
    st.header("D. Infrastructure and IT Controls")
    d_firewall_ids = st.radio(
        "Do you have firewalls and intrusion detection/prevention systems in place?",
        options=["Yes", "No"],
        horizontal=True,
    )
    d_malware_protection = st.radio(
        "Do you have malware protection for remote access, email, and mobile devices?",
        options=["Yes", "No"],
        horizontal=True,
    )
    d_mfa = st.radio(
        "Do you use multi-factor authentication (MFA) for critical systems?",
        options=["Yes", "No"],
        horizontal=True,
    )
    d_endpoint_security = st.radio(
        "Is endpoint protection deployed across the network?",
        options=["Yes", "No"],
        horizontal=True,
    )
    d_backup_freq = st.selectbox(
        "What is the frequency of your data backups?",
        options=[
            "No regular backups",
            "Monthly",
            "Weekly",
            "Daily or more often",
        ],
    )
    d_backup_location = st.text_input(
        "Where are backups stored? (on-site / off-site / cloud, etc.)"
    )

    # E. Incident response and history
    st.header("E. Incident Response and History")
    e_ir_plan = st.radio(
        "Do you have a formal incident response plan?",
        options=["Yes", "No"],
        horizontal=True,
    )
    e_incidents_5y = st.radio(
        "Have you experienced any cyber incidents in the last 5 years?",
        options=["Yes", "No"],
        horizontal=True,
    )
    e_incident_details = st.text_area(
        "If yes, briefly describe the incidents"
    )
    e_potential_claims = st.radio(
        "Are you aware of any events that could lead to a cyber insurance claim?",
        options=["Yes", "No"],
        horizontal=True,
    )
    e_claim_details = st.text_area(
        "If yes, briefly describe these events"
    )

    # F. Activities and professional exposures
    st.header("F. Activities and Professional Exposures")
    f_sectors = st.multiselect(
        "Which of the following sectors best describe your organisation? (select all that apply)",
        options=[
            "Water and Energy (electricity, gas, oil, water)",
            "Financial institution (bank, insurance, microfinance, collection, etc.)",
            "Sports betting / gambling",
            "Telecommunications / new technologies",
            "Healthcare / medical / provident fund",
            "Commerce / agro-industry",
            "Other",
        ],
    )
    f_other = st.text_input("If 'Other', please specify")

    # G. Requested coverage details
    st.header("G. Requested Coverage Details")
    g_amount = st.text_input(
        "Desired insured amount and deductible (not directly scored)"
    )
    g_options = st.multiselect(
        "Which coverage options are you interested in? (select all that apply)",
        options=[
            "Business interruption",
            "Data restoration",
            "Ransomware / cyber extortion",
            "Social engineering fraud",
            "Regulatory fines",
            "Reputational harm",
            "Media liability",
        ],
    )

    # H. Supplier and third-party security
    st.header("H. Supplier and Third-Party Security")
    h_supplier_access = st.radio(
        "Do suppliers or third parties have access to your systems or sensitive data?",
        options=["Yes", "No"],
        horizontal=True,
    )
    h_thirdparty_policy = st.radio(
        "Do you have a security policy for third parties?",
        options=["Yes", "No"],
        horizontal=True,
    )
    h_contract_clauses = st.radio(
        "Do your contracts include cybersecurity clauses with suppliers?",
        options=["Yes", "No"],
        horizontal=True,
    )
    h_update_policy = st.radio(
        "Do you have a policy for keeping software up to date?",
        options=["Yes", "No"],
        horizontal=True,
    )
    h_software_list = st.text_area(
        "List key software used in your organisation"
    )

    # I. Security indicators and monitoring
    st.header("I. Security Indicators and Monitoring")
    i_dashboards = st.radio(
        "Do you use dashboards or KPIs to monitor cyber security?",
        options=["Yes", "No"],
        horizontal=True,
    )
    i_reporting_freq = st.selectbox(
        "How often are security reports provided to management?",
        options=[
            "Ad hoc / not defined",
            "Annually",
            "Quarterly",
            "Monthly",
            "Weekly or more often",
        ],
    )

    # J. Tests and audits
    st.header("J. Tests and Audits")
    j_external_audit = st.radio(
        "Have you had an external security audit performed?",
        options=["Yes", "No"],
        horizontal=True,
    )
    j_last_audit_date = st.text_input(
        "If yes, date of the last audit"
    )
    j_results_to_management = st.radio(
        "Were the audit results shared with senior management?",
        options=["Yes", "No"],
        horizontal=True,
    )

    # K. Awareness and security culture
    st.header("K. Awareness and Security Culture")
    k_risky_behaviour_policy = st.radio(
        "Do you have a policy for managing risky user behaviour (e.g., clear rules on acceptable use)?",
        options=["Yes", "No"],
        horizontal=True,
    )
    k_phishing_sims = st.radio(
        "Do you conduct phishing simulations?",
        options=["Yes", "No"],
        horizontal=True,
    )
    k_phishing_freq = st.selectbox(
        "If yes, how often are phishing simulations carried out?",
        options=[
            "Ad hoc / not defined",
            "Annually",
            "Quarterly",
            "Monthly",
            "Weekly or more often",
        ],
    )

    # L. Mobile devices and BYOD
    st.header("L. Mobile Devices and BYOD")
    l_byod_policy = st.radio(
        "Do you have a Bring Your Own Device (BYOD) policy?",
        options=["Yes", "No"],
        horizontal=True,
    )
    l_personal_device_security = st.radio(
        "Are personal devices required to use security controls (e.g., MDM, encryption, PIN/biometrics)?",
        options=["Yes", "No"],
        horizontal=True,
    )

    # ---------- Separator before Section 2 ----------
    st.markdown(
        """
        <div style="margin-top: 3rem; border-top: 3px solid #e5e7eb; padding-top: 1.5rem;"></div>
        """,
        unsafe_allow_html=True,
    )

    # ---------- SECTION 2: SCORE CALCULATION ----------
    st.markdown("## 2. Score Calculation")
    st.write("Click the button below to calculate your cyber security score based on the answers above.")

    btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
    with btn_col2:
        submitted = st.button(
            "Calculate Cyber Security Score",
            use_container_width=True,
        )

    if submitted:
        # responses used for scoring (B–L)
        responses_for_scoring = {
            "B_types": b_types,
            "C_infosec_policy": c_infosec_policy,
            "C_privacy_policy": c_privacy_policy,
            "C_training": c_training,
            "C_encryption": c_encryption,
            "C_access_revocation": c_access_revocation,
            "C_pentesting": c_pentesting,
            "C_patch_management": c_patch_management,
            "D_firewall_ids": d_firewall_ids,
            "D_malware_protection": d_malware_protection,
            "D_mfa": d_mfa,
            "D_endpoint_security": d_endpoint_security,
            "D_backup_freq": d_backup_freq,
            "E_ir_plan": e_ir_plan,
            "E_incidents_5y": e_incidents_5y,
            "E_potential_claims": e_potential_claims,
            "F_sectors": f_sectors,
            "G_options": g_options,
            "H_supplier_access": h_supplier_access,
            "H_thirdparty_policy": h_thirdparty_policy,
            "H_contract_clauses": h_contract_clauses,
            "H_update_policy": h_update_policy,
            "I_dashboards": i_dashboards,
            "I_reporting_freq": i_reporting_freq,
            "J_external_audit": j_external_audit,
            "J_results_to_management": j_results_to_management,
            "K_risky_behaviour_policy": k_risky_behaviour_policy,
            "K_phishing_sims": k_phishing_sims,
            "K_phishing_freq": k_phishing_freq,
            "L_byod_policy": l_byod_policy,
            "L_personal_device_security": l_personal_device_security,
        }

        # all answers (A–L) for the PDF
        all_answers = {
            "A_company_name": a_company_name,
            "A_address": a_address,
            "A_websites": a_websites,
            "A_activity": a_activity,
            "A_employees": a_employees,
            "A_revenue": a_revenue,
            "A_years": a_years,
            "A_primary_contact": a_contact,
            "B_types": b_types,
            "C_infosec_policy": c_infosec_policy,
            "C_privacy_policy": c_privacy_policy,
            "C_training": c_training,
            "C_encryption": c_encryption,
            "C_encryption_details": c_encryption_details,
            "C_access_revocation": c_access_revocation,
            "C_pentesting": c_pentesting,
            "C_patch_management": c_patch_management,
            "D_firewall_ids": d_firewall_ids,
            "D_malware_protection": d_malware_protection,
            "D_mfa": d_mfa,
            "D_endpoint_security": d_endpoint_security,
            "D_backup_freq": d_backup_freq,
            "D_backup_location": d_backup_location,
            "E_ir_plan": e_ir_plan,
            "E_incidents_5y": e_incidents_5y,
            "E_incident_details": e_incident_details,
            "E_potential_claims": e_potential_claims,
            "E_claim_details": e_claim_details,
            "F_sectors": f_sectors,
            "F_other": f_other,
            "G_amount": g_amount,
            "G_options": g_options,
            "H_supplier_access": h_supplier_access,
            "H_thirdparty_policy": h_thirdparty_policy,
            "H_contract_clauses": h_contract_clauses,
            "H_update_policy": h_update_policy,
            "H_software_list": h_software_list,
            "I_dashboards": i_dashboards,
            "I_reporting_freq": i_reporting_freq,
            "J_external_audit": j_external_audit,
            "J_last_audit_date": j_last_audit_date,
            "J_results_to_management": j_results_to_management,
            "K_risky_behaviour_policy": k_risky_behaviour_policy,
            "K_phishing_sims": k_phishing_sims,
            "K_phishing_freq": k_phishing_freq,
            "L_byod_policy": l_byod_policy,
            "L_personal_device_security": l_personal_device_security,
        }

        section_scores = calculate_section_scores(responses_for_scoring)
        overall = calculate_overall_score(section_scores)
        label = risk_label(overall)

        if overall >= 80:
            score_class = "score-good"
            subtext = "This indicates a strong cyber security posture with good controls in place."
        elif overall >= 60:
            score_class = "score-medium"
            subtext = "Your cyber security posture is moderate. There are controls in place, but there is room for improvement."
        else:
            score_class = "score-low"
            subtext = "Your organisation appears to have a weak cyber security posture and may be exposed to significant risks."

        st.markdown("## Result")
        st.progress(min(1.0, overall / 100.0))

        st.markdown(
            f"""
            <div class="score-card {score_class}">
                <div class="score-card-title">Overall Cyber Security Score</div>
                <div class="score-card-value">{overall:.1f} / 100</div>
                <div class="score-card-label"><strong>{label}</strong></div>
                <div class="score-subtext">{subtext}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ---------- SECTION 3: EXPORT PDF ----------
        st.markdown(
            """
            <div style="margin-top: 2.5rem; border-top: 2px solid #e5e7eb; padding-top: 1rem;"></div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("## 3. Export PDF Report")

        if not REPORTLAB_AVAILABLE:
            st.warning(
                "PDF export requires the `reportlab` package. "
                "Please install it with `pip install reportlab` and rerun the app."
            )
        else:
            pdf_buffer = generate_pdf(all_answers, section_scores, overall, label)
            st.download_button(
                label="Download PDF report",
                data=pdf_buffer,
                file_name="cyber_security_assessment.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
