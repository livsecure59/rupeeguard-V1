import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
SHEET_ID = "1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To"
MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/gviz/tq?tqx=out:csv&sheet=MF%20Assisted%20Sheet"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🚨 RupeeGuard: ISIN-Matched Exception Report")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv(MASTER_SHEET_URL)
        df.columns = df.columns.str.strip()
        # Ensure ISINs are strings and stripped of spaces
        if 'ISIN' in df.columns:
            df['ISIN'] = df['ISIN'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

master_df = load_master_data()

# --- 3. THE PRECISION ENGINE ---
def get_action_by_isin(pdf_text):
    # Regex to find any 12-character ISIN starting with 'IN'
    found_isins = re.findall(r"\b(IN[A-Z0-9]{10})\b", pdf_text)
    unique_isins = list(set(found_isins))
    
    results = []
    for isin in unique_isins:
        # Direct match in your Google Sheet
        match = master_df[master_df['ISIN'] == isin]
        if not match.empty:
            row = match.iloc[0]
            
            # Scoring Logic (20% weight per parameter)
            s_alpha = min(20, max(0, (row['Alpha'] + 1) * 6.6)) 
            s_beta = 20 if row['Beta'] < 1.0 else (10 if row['Beta'] < 1.2 else 5)
            s_sharpe = min(20, max(0, row['Sharpe'] * 16))
            s_3y = 20 if row['3Y CAGR'] > 15 else (10 if row['3Y CAGR'] > 10 else 5)
            s_5y = 20 if row.get('5Y CAGR', row['3Y CAGR']) > 12 else (10 if row.get('5Y CAGR', row['3Y CAGR']) > 8 else 5)
            
            score = s_alpha + s_beta + s_sharpe + s_3y + s_5y
            results.append({"fund": row['Fund Name'], "score": score, "isin": isin})
            
    return results

# --- 4. UI ---
with st.sidebar:
    ltcg_input = st.number_input("Remaining LTCG (₹)", value=125000)
    st.info("🟢 BUY: 90+ | 🟡 WATCH: 30-40 | 🔴 SELL: <25")
    st.write("---")
    if st.button("Clear Cache"):
        st.cache_data.clear()

uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        # Extract all text from the PDF
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + " "
    
    scored_funds = get_action_by_isin(full_text)
    
    col1, col2, col3 = st.columns(3)
    col1.header("🚀 BUY (90+)")
    col2.header("👀 WATCH (30-40)")
    col3.header("💀 SELL (<25)")

    found_any = False
    for item in scored_funds:
        score = item['score']
        card = f"**{item['fund']}**\n\nISIN: `{item['isin']}`\n\nScore: **{score:.1f}**"
        
        # ACTION-ONLY FILTERING
        if score >= 90:
            col1.success(card)
            found_any = True
        elif score < 25:
            tax = "Tax-Free" if ltcg_input > 20000 else "Tax-Check"
            col3.error(f"{card}\n\n🚨 Action: SELL ({tax})")
            found_any = True
        elif 30 <= score <= 40:
            col2.warning(f"{card}\n\n⚠️ Action: WATCH")
            found_any = True

    if not found_any:
        st.info("✅ No urgent actions required. All identified funds are in the 'Healthy' range (Score 41-89).")
