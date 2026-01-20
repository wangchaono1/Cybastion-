import math
import streamlit as st
import streamlit.components.v1 as components  # needed for the updated results section

# =========================================================
# Cybastion × RiskCare
# Binding Cyber Insurance Pricing App - Basic Version
# =========================================================

# Fixed pricing parameters
P_MIN = 0.10   # 10% - fixed
P_MAX = 0.20   # 20% - fixed
X0 = 60.0      # Inflection point
K = 0.08       # Curve steepness

def premium_rate(X: float) -> float:
    """
    Binding premium rate using a fixed sigmoid pricing curve.
    """
    X = max(0.0, min(100.0, float(X)))
    return P_MIN + (P_MAX - P_MIN) / (1 + math.exp(K * (X - X0)))

def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "Cybastion2025":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.markdown(
            """
            <style>
            .login-container {
                max-width: 500px;
                margin: 100px auto;
                padding: 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            .login-title {
                color: white;
                text-align: center;
                font-size: 28px;
                font-weight: 600;
                margin-bottom: 30px;
            }
            </style>
            <div class="login-container">
                <div class="login-title">🔐 Secure Access Required</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.text_input(
            "Please enter your access password:", 
            type="password", 
            on_change=password_entered, 
            key="password",
            label_visibility="visible"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.markdown(
            """
            <style>
            .login-container {
                max-width: 500px;
                margin: 100px auto;
                padding: 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            .login-title {
                color: white;
                text-align: center;
                font-size: 28px;
                font-weight: 600;
                margin-bottom: 30px;
            }
            </style>
            <div class="login-container">
                <div class="login-title">🔐 Secure Access Required</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.text_input(
            "Please enter your access password:", 
            type="password", 
            on_change=password_entered, 
            key="password",
            label_visibility="visible"
        )
        st.error("❌ Incorrect password. Please try again.")
        return False
    else:
        # Password correct
        return True

# -----------------------------
# Streamlit Configuration
# -----------------------------
st.set_page_config(
    page_title="Cybastion × RiskCare | Cyber Insurance Quote",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for enhanced styling
st.markdown(
    """
    <style>
    /* Main background gradient */
    .stApp {
        background: linear-gradient(to bottom, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Header styling */
    .header-container {
        padding: 30px 40px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 30px;
    }
    
    .brand-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }
    
    .brand-left {
        font-size: 16px;
        font-weight: 700;
        color: #000000;
    }
    
    .brand-right {
        font-size: 16px;
        font-weight: 700;
        color: #000000;
    }
    
    .app-title {
        font-size: 36px;
        font-weight: 700;
        color: #2c3e50;
        text-align: center;
    }
    
    /* Card styling */
    .info-card {
        background: white;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 20px;
    }
    
    /* Metric containers */
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    
    .stMetric label {
        color: white !important;
        font-weight: 600;
    }
    
    .stMetric .metric-value {
        color: white !important;
        font-size: 28px !important;
        font-weight: 700 !important;
    }
    
    /* Slider styling */
    .stSlider {
        padding: 10px 0;
    }
    
    /* Number input styling */
    .stNumberInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e9ecef;
        padding: 10px;
    }
    
    /* Results section */
    .results-header {
        font-size: 26px;
        font-weight: 700;
        color: #2c3e50;
        text-align: center;
        margin: 30px 0 20px 0;
        padding: 15px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Notice box */
    .notice-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #2196f3;
        margin: 20px 0;
    }
    
    .notice-title {
        font-size: 18px;
        font-weight: 700;
        color: #1565c0;
        margin-bottom: 10px;
    }
    
    .notice-text {
        color: #424242;
        line-height: 1.6;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 20px;
        color: #6c757d;
        font-size: 14px;
        margin-top: 40px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Check password before showing main app
if not check_password():
    st.stop()

# -----------------------------
# Main Application UI
# -----------------------------

# Header with brands and app title
st.markdown(
    """
    <div class="header-container">
        <div class="brand-row">
            <div class="brand-left">Cybastion</div>
            <div class="brand-right">RiskCare</div>
        </div>
        <div class="app-title">Cyber Insurance Pricing App</div>
    </div>
    """,
    unsafe_allow_html=True
)

# Introduction card
st.markdown(
    """
    <div class="info-card">
        <p style="font-size: 16px; line-height: 1.8; color: #495057; margin: 0;">
        This application generates <strong>cyber insurance quotes</strong> based on a nonlinear,
        score-driven actuarial pricing model.
        Premium rates are determined by the insured organization's Cybersecurity Score.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Input section
#st.markdown("<div class='info-card'>", unsafe_allow_html=True)
st.markdown("### 📊 Policy Parameters")

#X = st.slider(
#    "Cybersecurity Score (0–100 Points)",
#    min_value=0.0,
#    max_value=100.0,
#    value=65.0,
#    step=0.1,
#    help="Higher scores indicate better cybersecurity posture and result in lower premium rates"
#)

X = st.number_input(
    "Cybersecurity Score (0–100 Points)",
    min_value=0.0,
    max_value=100.0,
    value=65.0,
    step=0.1,
    format="%.1f",
    help="Higher scores indicate better cybersecurity posture and result in lower premium rates"
)

Z = st.number_input(
    "Total Coverage Amount (US Dollars)",
    min_value=0.0,
    value=1_000_000.0,
    step=50_000.0,
    format="%.2f",
    help="The maximum amount the policy will pay in the event of a covered cyber incident"
)
st.markdown("</div>", unsafe_allow_html=True)

# Calculation
Y = premium_rate(X)
premium_amount = Z * Y

# =============================
# UPDATED: Premium Quote Results (auto-fit numbers)
# =============================
st.markdown("<div class='results-header'>Premium Quote Results</div>", unsafe_allow_html=True)

rate_str = f"{Y*100:.2f}%"
coverage_str = f"${Z:,.2f}"
premium_str = f"${premium_amount:,.2f}"

components.html(
    f"""
    <style>
      .metric-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-top: 8px;
      }}
      .metric-card {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 18px 16px;
        color: white;
        box-sizing: border-box;
        overflow: hidden;
      }}
      .metric-label {{
        font-size: 14px;
        font-weight: 700;
        opacity: 0.95;
        margin-bottom: 10px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      .metric-value {{
        font-weight: 800;
        font-size: 30px;           /* start big, JS will shrink if needed */
        line-height: 1.1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-variant-numeric: tabular-nums;
      }}
      .metric-help {{
        margin-top: 10px;
        font-size: 12px;
        opacity: 0.9;
        line-height: 1.3;
      }}

      /* Responsive stacking on small screens */
      @media (max-width: 740px) {{
        .metric-grid {{ grid-template-columns: 1fr; }}
      }}
    </style>

    <div class="metric-grid" id="metricGrid">
      <div class="metric-card">
        <div class="metric-label">Premium Rate (%)</div>
        <div class="metric-value fitme">{rate_str}</div>
        <div class="metric-help">Percentage of coverage amount</div>
      </div>

      <div class="metric-card">
        <div class="metric-label">Coverage Amount (US Dollars)</div>
        <div class="metric-value fitme">{coverage_str}</div>
        <div class="metric-help">Maximum policy payout</div>
      </div>

      <div class="metric-card">
        <div class="metric-label">Total Premium (US Dollars)</div>
        <div class="metric-value fitme">{premium_str}</div>
        <div class="metric-help">Annual premium due</div>
      </div>
    </div>

    <script>
      function fitText(el, minPx, maxPx) {{
        el.style.fontSize = maxPx + "px";
        const parent = el.parentElement;
        if (!parent) return;

        const maxWidth = parent.clientWidth - 8;

        let size = maxPx;
        while (el.scrollWidth > maxWidth && size > minPx) {{
          size -= 1;
          el.style.fontSize = size + "px";
        }}
      }}

      function runFit() {{
        const els = document.querySelectorAll('.fitme');
        els.forEach(el => fitText(el, 14, 30));
      }}

      setTimeout(runFit, 0);
      setTimeout(runFit, 50);
      setTimeout(runFit, 200);

      window.addEventListener('resize', () => {{
        setTimeout(runFit, 50);
      }});
    </script>
    """,
    height=410,          # increased height so all 3 cards show
    scrolling=False
)

# Binding quote notice
st.markdown(
    """
    <div class="notice-box">
        <div class="notice-title">Premium Quote Notice</div>
        <div class="notice-text">
            The premium displayed above constitutes a <strong>cyber insurance quote</strong>, subject only to:
            <ul style="margin-top: 10px;">
                <li>Policy terms and conditions</li>
                <li>Standard exclusions</li>
                <li>Verification that no material misrepresentation exists in the provided cybersecurity information</li>
            </ul>
            No discretionary pricing adjustments apply beyond the model defined herein.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Footer
st.markdown(
    """
    <div class="footer">
        © 2026 Cybastion × RiskCare — Cyber Insurance Pricing App - Basic Version
    </div>
    """,
    unsafe_allow_html=True
)
