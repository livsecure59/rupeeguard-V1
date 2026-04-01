import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
SHEET_ID = "1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To"
MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/gviz/tq?tqx=out:csv&sheet=MF%20Assisted%20Sheet"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Tax-Smart Advisor")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv(MASTER_SHEET_URL)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

master_df = load_master_data()

# --- 3. ADVANCED CLEANING (Anti-Noise) ---
def get_clean_id(name):
    """Reduces names to their bare essentials (e.g., 'HDFC Prudence' -> 'hdfcprudence')"""
    if not isinstance(name, str): return ""
    # Remove person names, links, and noise
    if "Click Here" in name or "MUKHERJEE" in name or len(name) < 10: return None
    
    noise = r"(\bFund\b|\bGrowth\b|\bDirect\b|\bPlan\b|\bIDCW\b|\bRegular\b|Option|LTD|INF\w+)"
    cleaned = re.sub(noise, "", name, flags=re.IGNORECASE)
    return re.sub(r'[^a-zA-Z]', '', cleaned).lower().strip()

# --- 4. SCORING & SELL LOGIC ---
def get_advice(fund_name, ltcg_remaining):
    clean_pdf = get_clean_id(fund_name)
    if not clean_pdf: return None # Skip junk text
    
    # Try to find a match
    match = master_df[master_df['Fund Name'].apply(lambda x: clean_pdf in get_clean_id(str(x)) or get_clean_id(str(x)) in clean_pdf)]
    
    if match.empty:
        # Default fallback for unlisted funds (Monitor at 50)
        return "B", 50.0, "⚠️ MONITOR", "Nomenclature mismatch or Fund not in Master List."

    row = match.iloc[0]
    s_alpha = min(20, max(0, (row['Alpha'] + 1) * 6.6)) 
    s_beta = 20 if row['Beta'] < 1.0 else (10 if row['Beta'] < 1.2 else 5)
    s_sharpe = min(20, max(0, row['Sharpe'] * 16))
    s_3y = 20 if row['3Y CAGR'] > 15 else (10 if row['3Y CAGR'] > 10 else 5)
    s_5y = 20 if row.get('5Y CAGR', row['3Y CAGR']) > 12 else (10 if row.get('5Y CAGR', row['3Y CAGR']) > 8 else 5)
    
    score = s_alpha + s_beta + s_sharpe + s_3y + s_5y
    
    if score >= 80:
        return "A", score, "✅ HOLD", "Top-tier core holding."
    elif score >= 35:
        return "B", score, "⚖️ RETAIN", "Satisfactory metrics. No action required."
    else:
        # SELL LOGIC (Triggered below 35)
        tax_impact = "Tax-Free" if ltcg_remaining > 20000 else "High Tax"
        return "C", score, f"🚨 SELL ({tax_impact})", f"Underperformer. Available CGT: ₹{ltcg_remaining:,}."

# --- 5. UI ---
with st.sidebar:
    st.header("⚙️ Settings")
    ltcg_input = st.number_input("Remaining LTCG Limit (₹)", value=125000)

uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    
    # Extracting lines that look like fund names
    potential_funds = list(set(re.findall(r"([A-Z][A-Za-z\s&]{10,})", text)))

    st.subheader("📋 Advisor Action Plan")
    cols = st.columns(3)
    idx = 0
    for fund in potential_funds:
        res = get_advice(fund, ltcg_input)
        if not res: continue # Skip junk
        
        grade, score, action, reason = res
        with cols[idx % 3]:
            if grade == "A": st.success(f"**{fund}**\n\nScore: {score:.1f}\n\n**{action}**\n\n{reason}")
            elif grade == "B": st.warning(f"**{fund}**\n\nScore: {score:.1f}\n\n**{action}**\n\n{reason}")
            else: st.error(f"**{fund}**\n\nScore: {score:.1f}\n\n**{action}**\n\n{reason}")
        idx += 1
