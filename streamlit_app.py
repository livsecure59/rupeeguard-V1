import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
SHEET_ID = "1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To"
MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/gviz/tq?tqx=out:csv&sheet=MF%20Assisted%20Sheet"

AMC_WHITELIST = [
    "HDFC", "ICICI", "SBI", "NIPPON", "KOTAK", "AXIS", "UTI", "ADITYA BIRLA", "ABSL", 
    "MIRAE", "DSP", "BANDHAN", "TATA", "HSBC", "FRANKLIN", "CANARA", "ROBECO", 
    "INVESCO", "MOTILAL", "PARAG PARIKH", "PPFAS", "QUANT", "PGIM", "JM", "UNION"
]

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🚨 RupeeGuard: Action-Required Report")
st.markdown("---")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv(MASTER_SHEET_URL)
        df.columns = df.columns.str.strip()
        return df
    except: return pd.DataFrame()

master_df = load_master_data()

# --- 3. FILTERS ---
def is_mutual_fund(line):
    line_up = line.upper()
    # Rejects Bank DP info, AMC addresses, or short noise
    if any(x in line_up for x in ["BANK LIMITED", "SUBSCRIPTION", "DP ID", "CLIENT ID", "PORTFOLIO"]):
        return False
    return any(re.search(rf"\b{amc}\b", line_up) for amc in AMC_WHITELIST)

def get_clean_tokens(name):
    text = re.sub(r'[^a-zA-Z\s]', '', str(name))
    noise = {'fund', 'growth', 'direct', 'plan', 'idcw', 'regular', 'option', 'mutual', 'ltd'}
    return {word.lower() for word in text.split() if len(word) > 2 and word.lower() not in noise}

# --- 4. EXCEPTION LOGIC ---
def get_action_advice(fund_name, ltcg_remaining):
    if not is_mutual_fund(fund_name): return None
    
    pdf_tokens = get_clean_tokens(fund_name)
    best_match, max_overlap = None, 0
    
    for _, row in master_df.iterrows():
        overlap = len(pdf_tokens.intersection(get_clean_tokens(row['Fund Name'])))
        if overlap > max_overlap:
            max_overlap, best_match = overlap, row
            
    if max_overlap < 2: return None # Ignore if not in your master list

    # Scoring Math
    s_alpha = min(20, max(0, (best_match['Alpha'] + 1) * 6.6)) 
    s_beta = 20 if best_match['Beta'] < 1.0 else (10 if best_match['Beta'] < 1.2 else 5)
    s_sharpe = min(20, max(0, best_match['Sharpe'] * 16))
    s_3y = 20 if best_match['3Y CAGR'] > 15 else (10 if best_match['3Y CAGR'] > 10 else 5)
    s_5y = 20 if best_match.get('5Y CAGR', best_match['3Y CAGR']) > 12 else (10 if best_match.get('5Y CAGR', best_match['3Y CAGR']) > 8 else 5)
    
    score = s_alpha + s_beta + s_sharpe + s_3y + s_5y
    
    # ACTION-ONLY THRESHOLDS
    if score >= 90:
        return "BUY", score, "🟢 TOP PICK", "Exceptional risk-adjusted performance."
    elif score < 25:
        tax = "Tax-Free" if ltcg_remaining > 25000 else "Tax-Check"
        return "SELL", score, f"🔴 SELL ({tax})", "Critical underperformance. Switch recommended."
    elif 30 <= score <= 40:
        return "WATCH", score, "🟡 WATCHLIST", "Slipping metrics. Monitor closely."
    
    return None # SILENTLY IGNORE EVERYTHING ELSE

# --- 5. UI ---
with st.sidebar:
    ltcg_input = st.number_input("Remaining LTCG (₹)", value=125000)

uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    
    potential_lines = list(set(re.findall(r"([A-Z][A-Za-z\s&]{10,})", text)))
    
    col1, col2, col3 = st.columns(3)
    col1.header("🚀 BUY (90+)")
    col2.header("👀 WATCH (30-40)")
    col3.header("💀 SELL (<25)")

    for line in potential_lines:
        res = get_action_advice(line, ltcg_input)
        if not res: continue
        
        type, score, label, reason = res
        card = f"**{line}**\n\nScore: **{score:.1f}**\n\n{reason}"
        
        if type == "BUY": col1.success(card)
        elif type == "WATCH": col2.warning(card)
        elif type == "SELL": col3.error(card)
