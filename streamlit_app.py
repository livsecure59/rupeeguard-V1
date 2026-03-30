import streamlit as st
import pdfplumber

# --- APP CONFIG ---
st.set_page_config(page_title="RupeeGuard Advisor Pro", layout="wide")
st.title("🛡️ RupeeGuard: Advisor Portfolio Optimizer")

# --- SIDEBAR ---
with st.sidebar:
    st.header("💰 Tax Vault (₹1.25L)")
    already_used = st.number_input("LTCG used this year (₹)", min_value=0, value=0, step=5000)
    remaining = max(0, 125000 - already_used)
    st.metric("Tax Exemption Left", f"₹{remaining:,}")

# --- ADVISOR LOGIC ---
def get_abc_grade(name):
    # Professional Noise Filter
    noise = ["ISIN", "Folio", "PAN", "Nominee", "Growth Option", "19.", "21."]
    if any(x in name for x in noise) or len(name) < 12:
        return None, None, None

    # Logic: Default to 'B' (Core) for advisor-led selections.
    # Grade 'A' is reserved for Liquid/Overnight or confirmed Alpha-leaders.
    if any(x in name for x in ["Liquid", "Overnight", "Cash"]):
        return "A", "Liquidity", "✅ Hold"
    
    # Standard Equity/Hybrid funds selected by an advisor
    return "B", "Core Asset", "⚠️ Monitor Quality"

# --- MAIN UI ---
uploaded_file = st.file_uploader("Upload CAS PDF (Password-Free)", type="pdf")

if uploaded_file:
    with st.spinner("Extracting portfolio details..."):
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        
        found_funds = []
        for line in text.split('\n'):
            if any(x in line for x in ["Growth", "Direct", "Regular", "Dividend"]):
                # Clean the line to get just the scheme name
                clean_name = line.split(" - ")[0].split("  ")[0].strip()
                found_funds.append(clean_name)

    if found_funds:
        st.subheader("📋 Portfolio Action Plan")
        colA, colB, colC = st.columns(3)
        
        for fund in sorted(list(set(found_funds))):
            grade, desc, action = get_abc_grade(fund)
            if grade:
                content = f"**{fund}**\n\nGrade: **{grade}** ({desc})\n\n**Action:** {action}"
                if grade == "A": colA.success(content)
                elif grade == "B": colB.warning(content)
                else: colC.error(content)
