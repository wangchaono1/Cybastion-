import streamlit as st
from io import BytesIO
from datetime import datetime
import math

# Try to import reportlab for PDF generation
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Try to import plotly for radar charts
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


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


# UPDATED SECTION WEIGHTS - More meaningful distribution
SECTION_WEIGHTS = {
    "B": 0.08,  # Data & sensitive information (reduced - this is about exposure, not control)
    "C": 0.25,  # Organisation & security policies (INCREASED - foundational)
    "D": 0.20,  # Infrastructure & IT controls (INCREASED - critical technical controls)
    "E": 0.15,  # Incident response & history (maintained - important)
    "F": 0.03,  # Sector activities & exposures (reduced - inherent risk, not posture)
    "G": 0.02,  # Coverage requested (reduced - reflects awareness, not actual controls)
    "H": 0.10,  # Third-party & supplier security (maintained - supply chain critical)
    "I": 0.05,  # Security indicators & KPIs (maintained)
    "J": 0.05,  # Tests & audits (maintained)
    "K": 0.05,  # Awareness & security culture (INCREASED - human factor is critical)
    "L": 0.02,  # Mobile devices & BYOD (maintained - specific but important)
}

# Verify weights sum to 1.0
assert abs(sum(SECTION_WEIGHTS.values()) - 1.0) < 0.001, "Weights must sum to 1.0"


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
    e_items.append(yes_no_score(responses["E_incidents_5y"], yes_value=40, no_value=100))
    # Events that could lead to a claim (No is better)
    e_items.append(yes_no_score(responses["E_potential_claims"], yes_value=30, no_value=100))
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
# Visualization functions
# ---------------------------------------------------------

def create_radar_chart(section_scores: dict) -> go.Figure:
    """Create a radar/spider chart showing performance across sections."""
    if not PLOTLY_AVAILABLE:
        return None
    
    # Prepare data for radar chart
    categories = []
    values = []
    
    section_names = {
        "B": "Data & Sensitive Info",
        "C": "Policies & Governance",
        "D": "Infrastructure & IT",
        "E": "Incident Response",
        "F": "Sector Risk Profile",
        "G": "Coverage Awareness",
        "H": "Third-Party Security",
        "I": "Monitoring & KPIs",
        "J": "Tests & Audits",
        "K": "Security Culture",
        "L": "Mobile & BYOD"
    }
    
    for sec in ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]:
        categories.append(section_names[sec])
        values.append(section_scores.get(sec, 0))
    
    # Close the radar chart by repeating first value
    categories.append(categories[0])
    values.append(values[0])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Your Score',
        line=dict(color='#1f77b4', width=2),
        fillcolor='rgba(31, 119, 180, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10),
                gridcolor='rgba(0,0,0,0.1)'
            ),
            angularaxis=dict(
                tickfont=dict(size=11)
            )
        ),
        showlegend=False,
        height=500,
        margin=dict(l=80, r=80, t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def create_section_bar_chart(section_scores: dict) -> go.Figure:
    """Create a horizontal bar chart showing section scores with weights."""
    if not PLOTLY_AVAILABLE:
        return None
    
    section_names = {
        "B": "Data & Sensitive Info",
        "C": "Policies & Governance",
        "D": "Infrastructure & IT",
        "E": "Incident Response",
        "F": "Sector Risk Profile",
        "G": "Coverage Awareness",
        "H": "Third-Party Security",
        "I": "Monitoring & KPIs",
        "J": "Tests & Audits",
        "K": "Security Culture",
        "L": "Mobile & BYOD"
    }
    
    sections = ["C", "D", "E", "H", "B", "I", "J", "K", "F", "G", "L"]  # Sorted by weight
    names = [section_names[s] for s in sections]
    scores = [section_scores.get(s, 0) for s in sections]
    weights = [SECTION_WEIGHTS[s] * 100 for s in sections]
    
    # Color based on score
    colors = []
    for score in scores:
        if score >= 80:
            colors.append('#1e8e3e')  # green
        elif score >= 60:
            colors.append('#fbbc04')  # yellow
        else:
            colors.append('#d93025')  # red
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=names,
        x=scores,
        orientation='h',
        marker=dict(color=colors),
        text=[f"{s:.0f}% (weight: {w:.0f}%)" for s, w in zip(scores, weights)],
        textposition='auto',
        textfont=dict(size=10, color='white')
    ))
    
    fig.update_layout(
        xaxis=dict(
            title="Score",
            range=[0, 100],
            gridcolor='rgba(0,0,0,0.1)'
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=11)
        ),
        height=500,
        margin=dict(l=180, r=40, t=40, b=60),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(245,245,247,0.5)',
        font=dict(size=11)
    )
    
    return fig


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
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    def draw_header_footer():
        """Draw Cybastion/Riskare header and footer with date & confidentiality."""
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height - 40, "Cybastion")
        c.drawRightString(width - 40, height - 40, "Riskare")

        footer_y = 30
        c.setFont("Helvetica", 8)
        c.drawString(40, footer_y, f"Generated on {timestamp}")
        c.drawRightString(width - 40, footer_y, "Confidential – for internal use only")

    draw_header_footer()

    y = height - 80
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "Cyber Security Assessment Report")

    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Overall Score: {overall:.1f} / 100 ({label})")
    y -= 20

    # Section scores with weights
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Section Scores (with weights)")
    y -= 18

    c.setFont("Helvetica", 10)
    section_names = {
        "B": "Data & Sensitive Info",
        "C": "Policies & Governance",
        "D": "Infrastructure & IT",
        "E": "Incident Response",
        "F": "Sector Risk Profile",
        "G": "Coverage Awareness",
        "H": "Third-Party Security",
        "I": "Monitoring & KPIs",
        "J": "Tests & Audits",
        "K": "Security Culture",
        "L": "Mobile & BYOD"
    }
    
    for sec in sorted(section_scores.keys()):
        weight_pct = SECTION_WEIGHTS[sec] * 100
        c.drawString(50, y, f"Section {sec} - {section_names[sec]}: {section_scores[sec]:.1f}/100 (weight: {weight_pct:.0f}%)")
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
    st.set_page_config(page_title="Cyber Security Scoring", layout="wide")

    # Initialize session state for form persistence
    if "initialized" not in st.session_state:
        st.session_state.initialized = True

    # ---------- SIMPLE ACCESS CODE GATE ----------
    ACCESS_CODE = "Cybastion2025"

    st.markdown(
        "<h2 style='text-align:center; margin-top:0;'>Secure Access</h2>",
        unsafe_allow_html=True,
    )

    user_code = st.text_input(
        "Enter the access code to continue:",
        type="password",
        help="This assessment is restricted to authorised clients only.",
    )

    if user_code != ACCESS_CODE:
        st.warning("Please enter the correct access code to access the assessment.")
        st.stop()

    # ---------- Custom CSS ----------
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1400px;
            padding-top: 2rem;
            margin: 0 auto;
        }

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
        st.markdown(
            "<div style='margin-top: 0.4rem; font-weight: 700; font-size: 1.1rem;'>Cybastion</div>",
            unsafe_allow_html=True,
        )

    with header_cols[2]:
        st.markdown(
            "<div style='text-align: right; margin-top: 0.4rem; font-weight: 700; font-size: 1.1rem;'>Riskare</div>",
            unsafe_allow_html=True,
        )

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
            This cyber security scoring app provides an indicative view of your organisation's cyber security posture,
            based on governance, technical controls, incident preparedness and user awareness.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write(
        """
- **Section 1 – Questionnaire**: Complete the questions about your organisation.  
- **Section 2 – Cyber Security Score Calculation**: Click the button to compute your cyber security score.  
- **Section 3 – Export PDF Report**: Download a PDF summary of your responses and score.
        """
    )

    # ---------- SECTION 1: QUESTIONNAIRE ----------
    st.markdown("## 1. Questionnaire")

    # A. General Information (not scored)
    with st.expander("📋 **Section A: General Information**", expanded=True):
        st.markdown("*Basic information about your organisation (not scored)*")
        
        a_company_name = st.text_input("Legal entity name", key="A_company_name")
        a_address = st.text_input("Registered office address", key="A_address")
        a_websites = st.text_input("Website(s) / Domain(s)", key="A_websites")
        a_activity = st.text_area("Description of activity", key="A_activity")
        a_employees = st.text_input("Number of employees", key="A_employees")
        a_revenue = st.text_input("Annual turnover (last financial year, currency)", key="A_revenue")
        a_years = st.text_input("Years in operation", key="A_years")
        a_contact = st.text_area(
            "Primary cybersecurity contact (Name, Role, Email, Phone)", key="A_contact"
        )

    # B. Data & sensitive information
    with st.expander("🔒 **Section B: Data and Sensitive Information** (Weight: 8%)", expanded=False):
        st.markdown("*Information about the types of sensitive data your organisation handles*")
        
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
            key="B_types"
        )

    # C. Organisation and security policies
    with st.expander("📜 **Section C: Organisation and Security Policies** (Weight: 25%) - CRITICAL", expanded=False):
        st.markdown("*Governance and policy framework - **this section has the highest weight***")
        
        c_infosec_policy = st.radio(
            "Do you have a formal information security policy?",
            options=["Yes", "No"],
            horizontal=True,
            key="C_infosec_policy"
        )
        c_privacy_policy = st.radio(
            "Do you have an up-to-date privacy policy?",
            options=["Yes", "No"],
            horizontal=True,
            key="C_privacy_policy"
        )
        c_training = st.radio(
            "Do employees receive regular cybersecurity awareness training?",
            options=["Yes", "No"],
            horizontal=True,
            key="C_training"
        )
        c_encryption = st.radio(
            "Are electronic data encrypted (at rest and/or in transit)?",
            options=["Yes", "No"],
            horizontal=True,
            key="C_encryption"
        )
        c_encryption_details = st.text_input(
            "If yes, specify media/systems where encryption is used",
            key="C_encryption_details"
        )
        c_access_revocation = st.radio(
            "Are user access rights removed promptly when staff leave or change roles?",
            options=["Yes", "No"],
            horizontal=True,
            key="C_access_revocation"
        )
        c_pentesting = st.radio(
            "Do you perform periodic penetration tests or vulnerability assessments?",
            options=["Yes", "No"],
            horizontal=True,
            key="C_pentesting"
        )
        c_patch_management = st.radio(
            "Are identified vulnerabilities corrected quickly (patch management process)?",
            options=["Yes", "No"],
            horizontal=True,
            key="C_patch_management"
        )

    # D. Infrastructure and IT controls
    with st.expander("🖥️ **Section D: Infrastructure and IT Controls** (Weight: 20%) - CRITICAL", expanded=False):
        st.markdown("*Technical security controls - **second highest weight***")
        
        d_firewall_ids = st.radio(
            "Do you have firewalls and intrusion detection/prevention systems in place?",
            options=["Yes", "No"],
            horizontal=True,
            key="D_firewall_ids"
        )
        d_malware_protection = st.radio(
            "Do you have malware protection for remote access, email, and mobile devices?",
            options=["Yes", "No"],
            horizontal=True,
            key="D_malware_protection"
        )
        d_mfa = st.radio(
            "Do you use multi-factor authentication (MFA) for critical systems?",
            options=["Yes", "No"],
            horizontal=True,
            key="D_mfa"
        )
        d_endpoint_security = st.radio(
            "Is endpoint protection deployed across the network?",
            options=["Yes", "No"],
            horizontal=True,
            key="D_endpoint_security"
        )
        d_backup_freq = st.selectbox(
            "What is the frequency of your data backups?",
            options=[
                "No regular backups",
                "Monthly",
                "Weekly",
                "Daily or more often",
            ],
            key="D_backup_freq"
        )
        d_backup_location = st.text_input(
            "Where are backups stored? (on-site / off-site / cloud, etc.)",
            key="D_backup_location"
        )

    # E. Incident response and history
    with st.expander("🚨 **Section E: Incident Response and History** (Weight: 15%)", expanded=False):
        st.markdown("*Preparedness for and history of security incidents*")
        
        e_ir_plan = st.radio(
            "Do you have a formal incident response plan?",
            options=["Yes", "No"],
            horizontal=True,
            key="E_ir_plan"
        )
        e_incidents_5y = st.radio(
            "Have you experienced any cyber incidents in the last 5 years?",
            options=["Yes", "No"],
            horizontal=True,
            key="E_incidents_5y"
        )
        e_incident_details = st.text_area(
            "If yes, briefly describe the incidents",
            key="E_incident_details"
        )
        e_potential_claims = st.radio(
            "Are you aware of any events that could lead to a cyber insurance claim?",
            options=["Yes", "No"],
            horizontal=True,
            key="E_potential_claims"
        )
        e_claim_details = st.text_area(
            "If yes, briefly describe these events",
            key="E_claim_details"
        )

    # F. Activities and professional exposures
    with st.expander("🏢 **Section F: Activities and Professional Exposures** (Weight: 3%)", expanded=False):
        st.markdown("*Industry sector and inherent risk profile*")
        
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
            key="F_sectors"
        )
        f_other = st.text_input("If 'Other', please specify", key="F_other")

    # G. Requested coverage details
    with st.expander("💼 **Section G: Requested Coverage Details** (Weight: 2%)", expanded=False):
        st.markdown("*Insurance coverage interests (indicates risk awareness)*")
        
        g_amount = st.text_input(
            "Desired insured amount and deductible (not directly scored)",
            key="G_amount"
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
            key="G_options"
        )

    # H. Supplier and third-party security
    with st.expander("🤝 **Section H: Supplier and Third-Party Security** (Weight: 10%)", expanded=False):
        st.markdown("*Supply chain and vendor security management*")
        
        h_supplier_access = st.radio(
            "Do suppliers or third parties have access to your systems or sensitive data?",
            options=["Yes", "No"],
            horizontal=True,
            key="H_supplier_access"
        )
        h_thirdparty_policy = st.radio(
            "Do you have a security policy for third parties?",
            options=["Yes", "No"],
            horizontal=True,
            key="H_thirdparty_policy"
        )
        h_contract_clauses = st.radio(
            "Do your contracts include cybersecurity clauses with suppliers?",
            options=["Yes", "No"],
            horizontal=True,
            key="H_contract_clauses"
        )
        h_update_policy = st.radio(
            "Do you have a policy for keeping software up to date?",
            options=["Yes", "No"],
            horizontal=True,
            key="H_update_policy"
        )
        h_software_list = st.text_area(
            "List key software used in your organisation",
            key="H_software_list"
        )

    # I. Security indicators and monitoring
    with st.expander("📊 **Section I: Security Indicators and Monitoring** (Weight: 5%)", expanded=False):
        st.markdown("*Metrics and reporting for security oversight*")
        
        i_dashboards = st.radio(
            "Do you use dashboards or KPIs to monitor cyber security?",
            options=["Yes", "No"],
            horizontal=True,
            key="I_dashboards"
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
            key="I_reporting_freq"
        )

    # J. Tests and audits
    with st.expander("🔍 **Section J: Tests and Audits** (Weight: 5%)", expanded=False):
        st.markdown("*External validation and assurance activities*")
        
        j_external_audit = st.radio(
            "Have you had an external security audit performed?",
            options=["Yes", "No"],
            horizontal=True,
            key="J_external_audit"
        )
        j_last_audit_date = st.text_input(
            "If yes, date of the last audit",
            key="J_last_audit_date"
        )
        j_results_to_management = st.radio(
            "Were the audit results shared with senior management?",
            options=["Yes", "No"],
            horizontal=True,
            key="J_results_to_management"
        )

    # K. Awareness and security culture
    with st.expander("👥 **Section K: Awareness and Security Culture** (Weight: 5%)", expanded=False):
        st.markdown("*Human factor and security awareness*")
        
        k_risky_behaviour_policy = st.radio(
            "Do you have a policy for managing risky user behaviour (e.g., clear rules on acceptable use)?",
            options=["Yes", "No"],
            horizontal=True,
            key="K_risky_behaviour_policy"
        )
        k_phishing_sims = st.radio(
            "Do you conduct phishing simulations?",
            options=["Yes", "No"],
            horizontal=True,
            key="K_phishing_sims"
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
            key="K_phishing_freq"
        )

    # L. Mobile devices and BYOD
    with st.expander("📱 **Section L: Mobile Devices and BYOD** (Weight: 2%)", expanded=False):
        st.markdown("*Mobile device management and personal device security*")
        
        l_byod_policy = st.radio(
            "Do you have a Bring Your Own Device (BYOD) policy?",
            options=["Yes", "No"],
            horizontal=True,
            key="L_byod_policy"
        )
        l_personal_device_security = st.radio(
            "Are personal devices required to use security controls (e.g., MDM, encryption, PIN/biometrics)?",
            options=["Yes", "No"],
            horizontal=True,
            key="L_personal_device_security"
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
            "B_types": st.session_state.get("B_types", []),
            "C_infosec_policy": st.session_state.get("C_infosec_policy", "No"),
            "C_privacy_policy": st.session_state.get("C_privacy_policy", "No"),
            "C_training": st.session_state.get("C_training", "No"),
            "C_encryption": st.session_state.get("C_encryption", "No"),
            "C_access_revocation": st.session_state.get("C_access_revocation", "No"),
            "C_pentesting": st.session_state.get("C_pentesting", "No"),
            "C_patch_management": st.session_state.get("C_patch_management", "No"),
            "D_firewall_ids": st.session_state.get("D_firewall_ids", "No"),
            "D_malware_protection": st.session_state.get("D_malware_protection", "No"),
            "D_mfa": st.session_state.get("D_mfa", "No"),
            "D_endpoint_security": st.session_state.get("D_endpoint_security", "No"),
            "D_backup_freq": st.session_state.get("D_backup_freq", "No regular backups"),
            "E_ir_plan": st.session_state.get("E_ir_plan", "No"),
            "E_incidents_5y": st.session_state.get("E_incidents_5y", "No"),
            "E_potential_claims": st.session_state.get("E_potential_claims", "No"),
            "F_sectors": st.session_state.get("F_sectors", []),
            "G_options": st.session_state.get("G_options", []),
            "H_supplier_access": st.session_state.get("H_supplier_access", "No"),
            "H_thirdparty_policy": st.session_state.get("H_thirdparty_policy", "No"),
            "H_contract_clauses": st.session_state.get("H_contract_clauses", "No"),
            "H_update_policy": st.session_state.get("H_update_policy", "No"),
            "I_dashboards": st.session_state.get("I_dashboards", "No"),
            "I_reporting_freq": st.session_state.get("I_reporting_freq", "Ad hoc / not defined"),
            "J_external_audit": st.session_state.get("J_external_audit", "No"),
            "J_results_to_management": st.session_state.get("J_results_to_management", "No"),
            "K_risky_behaviour_policy": st.session_state.get("K_risky_behaviour_policy", "No"),
            "K_phishing_sims": st.session_state.get("K_phishing_sims", "No"),
            "K_phishing_freq": st.session_state.get("K_phishing_freq", "Ad hoc / not defined"),
            "L_byod_policy": st.session_state.get("L_byod_policy", "No"),
            "L_personal_device_security": st.session_state.get("L_personal_device_security", "No"),
        }

        # all answers (A–L) for the PDF
        all_answers = {
            "A_company_name": st.session_state.get("A_company_name", ""),
            "A_address": st.session_state.get("A_address", ""),
            "A_websites": st.session_state.get("A_websites", ""),
            "A_activity": st.session_state.get("A_activity", ""),
            "A_employees": st.session_state.get("A_employees", ""),
            "A_revenue": st.session_state.get("A_revenue", ""),
            "A_years": st.session_state.get("A_years", ""),
            "A_primary_contact": st.session_state.get("A_contact", ""),
            "B_types": st.session_state.get("B_types", []),
            "C_infosec_policy": st.session_state.get("C_infosec_policy", ""),
            "C_privacy_policy": st.session_state.get("C_privacy_policy", ""),
            "C_training": st.session_state.get("C_training", ""),
            "C_encryption": st.session_state.get("C_encryption", ""),
            "C_encryption_details": st.session_state.get("C_encryption_details", ""),
            "C_access_revocation": st.session_state.get("C_access_revocation", ""),
            "C_pentesting": st.session_state.get("C_pentesting", ""),
            "C_patch_management": st.session_state.get("C_patch_management", ""),
            "D_firewall_ids": st.session_state.get("D_firewall_ids", ""),
            "D_malware_protection": st.session_state.get("D_malware_protection", ""),
            "D_mfa": st.session_state.get("D_mfa", ""),
            "D_endpoint_security": st.session_state.get("D_endpoint_security", ""),
            "D_backup_freq": st.session_state.get("D_backup_freq", ""),
            "D_backup_location": st.session_state.get("D_backup_location", ""),
            "E_ir_plan": st.session_state.get("E_ir_plan", ""),
            "E_incidents_5y": st.session_state.get("E_incidents_5y", ""),
            "E_incident_details": st.session_state.get("E_incident_details", ""),
            "E_potential_claims": st.session_state.get("E_potential_claims", ""),
            "E_claim_details": st.session_state.get("E_claim_details", ""),
            "F_sectors": st.session_state.get("F_sectors", []),
            "F_other": st.session_state.get("F_other", ""),
            "G_amount": st.session_state.get("G_amount", ""),
            "G_options": st.session_state.get("G_options", []),
            "H_supplier_access": st.session_state.get("H_supplier_access", ""),
            "H_thirdparty_policy": st.session_state.get("H_thirdparty_policy", ""),
            "H_contract_clauses": st.session_state.get("H_contract_clauses", ""),
            "H_update_policy": st.session_state.get("H_update_policy", ""),
            "H_software_list": st.session_state.get("H_software_list", ""),
            "I_dashboards": st.session_state.get("I_dashboards", ""),
            "I_reporting_freq": st.session_state.get("I_reporting_freq", ""),
            "J_external_audit": st.session_state.get("J_external_audit", ""),
            "J_last_audit_date": st.session_state.get("J_last_audit_date", ""),
            "J_results_to_management": st.session_state.get("J_results_to_management", ""),
            "K_risky_behaviour_policy": st.session_state.get("K_risky_behaviour_policy", ""),
            "K_phishing_sims": st.session_state.get("K_phishing_sims", ""),
            "K_phishing_freq": st.session_state.get("K_phishing_freq", ""),
            "L_byod_policy": st.session_state.get("L_byod_policy", ""),
            "L_personal_device_security": st.session_state.get("L_personal_device_security", ""),
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

        # Display visualizations
        st.markdown("### 📊 Score Breakdown")
        
        viz_col1, viz_col2 = st.columns(2)
        
        with viz_col1:
            st.markdown("#### Performance by Section")
            if PLOTLY_AVAILABLE:
                radar_fig = create_radar_chart(section_scores)
                if radar_fig:
                    st.plotly_chart(radar_fig, use_container_width=True)
            else:
                st.info("Install plotly for interactive radar charts: `pip install plotly`")
        
        with viz_col2:
            st.markdown("#### Weighted Section Scores")
            if PLOTLY_AVAILABLE:
                bar_fig = create_section_bar_chart(section_scores)
                if bar_fig:
                    st.plotly_chart(bar_fig, use_container_width=True)
            else:
                st.info("Install plotly for interactive charts: `pip install plotly`")
        
        # Detailed section scores table
        st.markdown("### 📋 Detailed Section Scores")
        
        section_names = {
            "B": "Data & Sensitive Information",
            "C": "Policies & Governance",
            "D": "Infrastructure & IT Controls",
            "E": "Incident Response",
            "F": "Sector Risk Profile",
            "G": "Coverage Awareness",
            "H": "Third-Party Security",
            "I": "Monitoring & KPIs",
            "J": "Tests & Audits",
            "K": "Security Culture",
            "L": "Mobile & BYOD"
        }
        
        # Sort by weight (descending)
        sorted_sections = sorted(section_scores.keys(), 
                               key=lambda x: SECTION_WEIGHTS[x], 
                               reverse=True)
        
        for sec in sorted_sections:
            weight_pct = SECTION_WEIGHTS[sec] * 100
            score = section_scores[sec]
            
            if score >= 80:
                emoji = "✅"
                color = "#1e8e3e"
            elif score >= 60:
                emoji = "⚠️"
                color = "#fbbc04"
            else:
                emoji = "❌"
                color = "#d93025"
            
            st.markdown(
                f"""
                <div style="padding: 0.75rem; margin: 0.5rem 0; background: #f9f9f9; border-radius: 8px; border-left: 4px solid {color};">
                    <strong>{emoji} Section {sec}: {section_names[sec]}</strong><br/>
                    Score: <strong>{score:.1f}/100</strong> | Weight: <strong>{weight_pct:.0f}%</strong> | Contribution: <strong>{score * SECTION_WEIGHTS[sec]:.1f}</strong> points
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # Key insights
        st.markdown("### 💡 Key Insights")
        
        # Find strengths and weaknesses
        strengths = [sec for sec, score in section_scores.items() if score >= 80]
        weaknesses = [sec for sec, score in section_scores.items() if score < 60]
        
        if strengths:
            st.success(f"**Strengths:** Your organisation performs well in: {', '.join([section_names[s] for s in strengths])}")
        
        if weaknesses:
            st.error(f"**Areas for Improvement:** Focus on: {', '.join([section_names[s] for s in weaknesses])}")
        
        # Highlight critical sections
        critical_low = [sec for sec in ["C", "D", "E"] if section_scores[sec] < 70]
        if critical_low:
            st.warning(f"⚠️ **Critical Priority:** Sections {', '.join(critical_low)} are high-weight areas with low scores. Improving these will significantly boost your overall score.")

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
                label="📥 Download PDF Report",
                data=pdf_buffer,
                file_name=f"cyber_security_assessment_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()