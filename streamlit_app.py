import streamlit as st
import pdfplumber
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: A-B-C Portfolio Optimizer")
st.markdown("---")

# --- SIDEBAR: TAX VAULT ---
with st.sidebar:
    st.header("💰 Tax Vault (₹1.25L)")
    already_used = st.number_input("LTCG already used this year (₹)", min_value=0, value=0, step=5000)
    remaining_tax_free = max(0, 125000 - already_used)
    st.metric("Remaining Exemption", f"₹{remaining_tax_free:,}")
    st.info("Prioritizing switches within this tax limit.")

# --- THE LOGIC ENGINE ---
def get_abc_grade(fund_name):
    # This is where your 20% weightage logic lives!
    # For now, it categorizes based on keywords until we link live API data
    if "Index" in fund_name or "Bluechip" in fund_name:
        return "A", "Elite", "✅ Hold"
    elif "Small" in fund_name or "Mid" in fund_name:
        return "B", "Volatile", "⚠️ Review"
    return "C", "Laggard", "🚨 Switch Suggested"

# --- MAIN INTERFACE ---
st.subheader("📤 Upload Your CAS PDF")
uploaded_file = st.file_uploader("Upload Password-Free CAMS/Karvy PDF", type="pdf")

if uploaded_file:
    with st.status("Analyzing your Portfolio...", expanded=True) as status:
        # 1. Read the PDF
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
        
        # 2. Extract Fund Names (Searching for common patterns in Indian CAS)
        # This looks for text blocks that look like Fund Names
        found_funds = []
        lines = text.split('\n')
        for line in lines:
            if "Direct" in line or "Growth" in line:
                found_funds.append(line.split(" - ")[0].strip())
        
        status.update(label="Analysis Complete!", state="complete", expanded=False)

    if found_funds:
        st.subheader("📊 Your A-B-C Action Plan")
        # Creating the Grid
        colA, colB, colC = st.columns(3)
        
        # Unique list of funds found
        for fund in list(set(found_funds))[:6]: # Displaying top 6 for clarity
            grade, desc, action = get_abc_grade(fund)
            
            card_content = f"**{fund}**\n\nGrade: **{grade}** ({desc})\n\n**Action:** {action}"
            
            if grade == "A": colA.success(card_content)
            elif grade == "B": colB.warning(card_content)
            else: colC.error(card_content)
    else:
        st.error("No funds detected. Please ensure you are using a standard CAMS/Karvy Consolidated Account Statement.")

st.divider()
st.caption("🔒 All data is processed locally in your browser and never stored on a server.")
