import streamlit as st
import pandas as pd
import pdfplumber
import re
import requests
import io

# --- 1. CONFIGURATION ---
SHEET_ID = "1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To"
MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Professional Advisor Portal")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        response = requests.get(MASTER_SHEET_URL, timeout=10)
        response.raise_for_status() 
        df = pd.read_csv(io.StringIO(response.text))
        df.columns = df.columns.str.strip()
        num_cols = ['Alpha', 'Beta', 'Sharpe', '3Y CAGR', '5Y CAGR']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        if 'ISIN' in df.columns:
            df['ISIN'] = df['ISIN'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"⚠️ Database Connection Error: {e}")
        return pd.DataFrame()

master_df = load_master_data()

# --- 3. SCORING ENGINE ---
def get_strict_score(row):
    try:
        # Alpha (30pts): 10 pts per 1% Alpha
        s_alpha = min(30, max(0, float(row['Alpha']) * 10)) if float(row['Alpha']) > 0 else 0
        # Sharpe (25pts): Linear reward above 0.5 baseline
        sharpe = float(row['Sharpe'])
        s_sharpe = min(25, max(0, (sharpe - 0.5) * 31.25)) if sharpe > 0.5 else 0
        # Beta (15pts): Tiered reward for stability
        beta = float(row['Beta'])
        if beta <= 0.9: s_beta = 15
        elif beta <= 1.1: s_beta = 8
        elif beta <= 1.2: s_beta = 4
        else: s_beta = 0
        # CAGR (15pts each): Momentum and Consistency
        c3y = float(row['3Y CAGR'])
        s_3y = 15 if c3y >= 18 else (8 if c3y >= 15 else (4 if c3y >= 12 else 0))
        c5y = float(row.get('5Y CAGR', row['3Y CAGR']))
        s_5y = 15 if c5y >= 15 else (8 if c5y >= 12 else (4 if c5y >= 10 else 0))
        return round(s_alpha + s_beta + s_sharpe + s_3y + s_5y, 1)
    except: return 0.0

if not master_df.empty:
    master_df['Calculated Score'] = master_df.apply(get_strict_score, axis=1)

# --- 4. TABS INTERFACE ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Portfolio Review", 
    "🗂️ Master Database", 
    "⚖️ Weightage", 
    "🔢 Scoring Logic",
    "📝 Assumptions"
])

# --- TAB 5: ASSUMPTIONS ---
with tab5:
    st.subheader("Core Investment Assumptions")
    st.markdown("""
    This advisory portal operates on the following institutional-grade assumptions:
    
    1. **Filtering Mechanism:** Analysis is strictly restricted to funds indexed in the Master Database. **Debt funds, liquid funds, and unindexed equity funds** are automatically filtered out as 'Non-Actionable' for this specific equity strategy.
    
    2. **Alpha (30 Points):** Excess return over the benchmark is the primary driver of value. Every 1% of positive Alpha contributes 10 points. Negative Alpha is treated as a strategic failure and scores 0.
    
    3. **Sharpe Ratio (25 Points):** We assume a fund must earn its returns efficiently. A baseline of 0.5 is required; efficiency above this is rewarded linearly up to 1.3.
    
    4. **Beta (15 Points):** Lower volatility relative to the market is a virtue. We use a step-down tier:
        * **≤ 0.9 (Optimal):** 15 pts
        * **0.91 - 1.1 (Standard):** 8 pts
        * **1.11 - 1.2 (High Risk):** 4 pts
        * **> 1.2 (Failure):** 0 pts
    
    5. **CAGR Hurdles (15 Points Each):** We assume 18% (3Y) and 15% (5Y) are the benchmarks for high-conviction growth. Funds falling below 12% or 10% respectively receive 0 points for consistency.
    """)

# --- TAB 4: SCORING LOGIC ---
with tab4:
    st.subheader("Numerical Scoring Logic")
    logic_data = {
        "Parameter": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"],
        "Max Points": [30, 25, 15, 15, 15],
        "Zero-Point Hurdle": ["≤ 0.0", "≤ 0.5", "> 1.2", "< 12%", "< 10%"],
        "Full-Point Target": ["> 3.0", "> 1.3", "≤ 0.9", "> 18%", "> 15%"]
    }
    st.table(pd.DataFrame(logic_data))

# --- TAB 3: WEIGHTAGE ---
with tab3:
    st.subheader("Weightage Distribution")
    st.table(pd.DataFrame({
        "Metric": ["Alpha", "Sharpe Ratio", "Beta", "3Y CAGR", "5Y CAGR"], 
        "Weight": ["30%", "25%", "15%", "15%", "15%"]
    }))

# --- TAB 2: MASTER DATABASE ---
with tab2:
    st.subheader("Full Database Audit")
    # Reset index for display
    display_master = master_df.copy()
    display_master.index = range(1, len(display_master) + 1)
    st.dataframe(display_master, use_container_width=True)

# --- TAB 1: REVIEW ---
with tab1:
    uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")
    if uploaded_file:
        with st.spinner("Isolating Actionable Equity Funds..."):
            holdings = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    words = page.extract_words()
                    target_x = next(((w['x0'] + w['x1'])/2 for w in words if "VALU" in w['text'].upper()), None)
                    for w in words:
                        if re.search(r"IN[A-Z0-9]{10}", w['text']):
                            isin = w['text']
                            match = master_df[master_df['ISIN'] == isin]
                            if not match.empty:
                                y_mid = (w['top'] + w['bottom']) / 2
                                row_values = [n for n in words if abs(((n['top']+n['bottom'])/2) - y_mid) < 15]
                                fund_val = 0
                                for n in row_values:
                                    clean = n['text'].replace(',', '')
                                    if re.match(r"^\d+\.\d{2}$", clean):
                                        num = float(clean)
                                        if target_x and abs(((n['x0']+n['x1'])/2) - target_x) < 80:
                                            fund_val = num
                                            break
                                        elif num > fund_val: fund_val = num
                                res = match.iloc[0]
                                holdings.append({"Fund": res['Fund Name'], "Score": res['Calculated Score'], "Value": fund_val, "ISIN": isin})

            if holdings:
                pdf_df = pd.DataFrame(holdings)
                pdf_df = pdf_df.groupby(['Fund', 'ISIN', 'Score'], as_index=False)['Value'].sum()
                pdf_df = pdf_df
