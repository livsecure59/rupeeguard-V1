import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
# Your verified Google Sheet CSV link
MASTER_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTshkPAn-oB-6_E9DAt_C0fE2k9qF77eB2C-79F8U0T-0F6V-6-C-0-B-6/pub?output=csv"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Absolute Scoring Engine")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv(MASTER_SHEET_URL)
        # Clean column names to ensure math doesn't fail
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error connecting to Google Sheet: {e}")
        return pd.DataFrame()

master_df = load_master_data()

# --- 3. THE "ABSOLUTE" SCORING LOGIC ---
def calculate_absolute_grade(fund_name):
    # Fuzzy match: Look for the fund name within your master list
    match = master_df[master_df['Fund Name'].apply(lambda x: str(x).lower() in fund_name.lower() or fund_name.lower() in str(x).lower())]
    
    if match.empty:
        return "B", "Unknown", "🔍 Manual Review Required", 50.0
    
    row = match.iloc[0]
    
    # 20% Weight for each of 5 Parameters (Total 100)
    # Alpha: Targeting +2.0 as a healthy baseline
    s_alpha = min(20, max(0, (row['Alpha'] + 1) * 6.6)) 
    
    # Beta: Reward stability (Lower is often safer for retail)
    s_beta = 20 if row['Beta'] < 1.0 else (10 if row['Beta'] < 1.2 else 5)
    
    # Sharpe: Reward risk-adjusted efficiency
    s_sharpe = min(20, max(0, row['Sharpe'] * 16))
    
    # Returns: Absolute performance benchmarks
    s_3y = 20 if row['3Y CAGR'] > 15 else (10 if row['3Y CAGR'] > 10 else 5)
    s_5y = 20 if row.get('5Y CAGR', 0) > 12 else (10 if row.get('5Y CAGR', 0) > 8 else 5)
    
    total_score = s_alpha + s_beta + s_sharpe + s_3y + s_5y
    
    if total_score >= 75: return "A", "Elite", "✅ Hold", total_score
    if total_score >= 50: return "B", "Average", "⚠️ Monitor", total_score
    return "C", "Laggard", "🚨 Switch Suggested", total_score

# --- 4. THE UI & PDF PARSER ---
uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

if uploaded_file:
    with st.spinner("Analyzing against Advisor Master Data..."):
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        
        # Regex to find Fund Names (looking for keywords like Growth/IDCW/Direct)
        pattern = r"([A-Z][A-Za-z\s&]+(?:Growth|IDCW|Direct|Plan|Fund))"
        found_funds = list(set(re.findall(pattern, text)))

    if not found_funds:
        st.warning("No funds detected. Ensure this is a standard CAS PDF.")
    else:
        st.subheader("📋 Performance-Based Action Plan")
        colA, colB, colC = st.columns(3)
        
        with colA: st.markdown("### ⭐ Category A")
        with colB: st.markdown("### ⚖️ Category B")
        with colC: st.markdown("### ⚠️ Category C")

        for fund in found_funds:
            grade, label, action, score = calculate_absolute_grade(fund)
            card_content = f"**{fund}**\n\nScore: **{score:.1f}/100**\n\n**Action:** {action}"
            
            if grade == "A": colA.success(card_content)
            elif grade == "B": colB.warning(card_content)
            else: colC.error(card_content)

st.sidebar.info("Data source: Linked Google Sheet (Master Data)")
