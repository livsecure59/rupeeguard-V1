import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
# REPLACE the ID below with your actual Google Sheet ID
SHEET_ID = "YOUR_SHEET_ID_HERE"
MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/export?format=csv"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Absolute Scoring Engine")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        # We use 'on_bad_lines' to ensure one messy row doesn't crash the whole app
        df = pd.read_csv(MASTER_SHEET_URL, on_bad_lines='skip')
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
        st.info("Ensure your Google Sheet is set to 'Anyone with the link can view'.")
        return pd.DataFrame()

master_df = load_master_data()

# --- 3. THE "ABSOLUTE" SCORING LOGIC ---
def calculate_absolute_grade(fund_name):
    if master_df.empty:
        return "B", "Offline", "🚨 Data Connection Failed", 0.0
        
    # Search for fund name match
    match = master_df[master_df['Fund Name'].apply(lambda x: str(x).lower() in fund_name.lower() or fund_name.lower() in str(x).lower())]
    
    if match.empty:
        return "B", "Unknown", "🔍 Manual Review Required", 50.0
    
    row = match.iloc[0]
    
    # 20% Weight for each of 5 Parameters (Total 100)
    s_alpha = min(20, max(0, (float(row.get('Alpha', 0)) + 1) * 6.6)) 
    s_beta = 20 if float(row.get('Beta', 1)) < 1.0 else (10 if float(row.get('Beta', 1)) < 1.2 else 5)
    s_sharpe = min(20, max(0, float(row.get('Sharpe', 0)) * 16))
    s_3y = 20 if float(row.get('3Y CAGR', 0)) > 15 else (10 if float(row.get('3Y CAGR', 0)) > 10 else 5)
    s_5y = 20 if float(row.get('5Y CAGR', 0)) > 12 else (10 if float(row.get('5Y CAGR', 0)) > 8 else 5)
    
    total_score = s_alpha + s_beta + s_sharpe + s_3y + s_5y
    
    if total_score >= 75: return "A", "Elite", "✅ Hold", total_score
    if total_score >= 50: return "B", "Average", "⚠️ Monitor", total_score
    return "C", "Laggard", "🚨 Switch Suggested", total_score

# --- 4. THE UI & PDF PARSER ---
uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

if uploaded_file:
    with st.spinner("Analyzing against Advisor Master Data..."):
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        
        # Regex to find Fund Names
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
