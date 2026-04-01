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
    "INVESCO", "MOTILAL", "PARAG PARIKH", "PPFAS", "QUANT", "PGIM", "JM", "UNION", "MAHINDRA"
]

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🚨 RupeeGuard: Action-Required Report")

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
    line_up = str(line).upper()
    if any(x in line_up for x in ["BANK LIMITED", "SUBSCRIPTION", "DP ID", "CLIENT ID", "PORTFOLIO", "EFFECT FROM"]):
        return False
    return any(re.search(rf"\b{amc}\b", line_up) for amc in AMC_WHITELIST)

def get_clean_tokens(name):
    text = re.sub(r'[^a-zA-Z\s]', '', str(name))
    noise = {'fund', 'growth', 'direct', 'plan', 'idcw', 'regular', 'option', 'mutual', 'ltd', 'pru'}
    return {word.lower() for word in text.split() if len(word) > 2 and word.lower() not in noise}

# --- 4. SCORING ---
def get_score(fund_name):
    pdf_tokens = get_clean_tokens(fund_name)
    best_match, max_overlap = None, 0
    for _, row in master_df.iterrows():
        overlap = len(pdf_tokens.intersection(get_clean_tokens(row['Fund Name'])))
        if overlap > max_overlap:
            max_overlap, best_match = overlap, row
    
    if max_overlap < 2 or best_match is None: return None

    # Scoring Math (Your 5-parameter 20% weights)
    s_alpha = min(20, max(0, (best_match['Alpha'] + 1) * 6.6)) 
    s_beta = 20 if best_match['Beta'] < 1.0 else (10 if best_match['Beta'] < 1.2 else 5)
    s_sharpe = min(20, max(0, best_match['Sharpe'] * 16))
    s_3y = 20 if best_match['3Y CAGR'] > 15 else (10 if best_match['3Y CAGR'] > 10 else 5)
    s_5y = 20 if best_match.get('5Y CAGR', best_match['3Y CAGR']) > 12 else (10 if best_match.get('5Y CAGR', best_match['3Y CAGR']) > 8 else 5)
    
    return s_alpha + s_beta + s_sharpe + s_3y + s_5y

# --- 5. UI ---
with st.sidebar:
    ltcg_input = st.number_input("Remaining LTCG (₹)", value=125000)
    debug_mode = st.checkbox("Diagnostic Mode (Show All Scores)", value=False)
    st.write("---")
    st.write("**Thresholds:**")
    st.write("🟢 BUY: 90+ | 🟡 WATCH: 30-40 | 🔴 SELL: <25")

uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    
    potential_lines = list(set(re.findall(r"([A-Z][A-Za-z\s&]{10,})", text)))
    
    col1, col2, col3 = st.columns(3)
    col1.header("🚀 BUY")
    col2.header("👀 WATCH")
    col3.header("💀 SELL")

    scanned_count = 0
    for line in potential_lines:
        if not is_mutual_fund(line): continue
        score = get_score(line)
        if score is None: continue
        
        scanned_count += 1
        card = f"**{line}**\n\nScore: **{score:.1f}**"
        
        # Display Logic
        if score >= 90: col1.success(card)
        elif score < 25: col3.error(f"{card}\n\n🚨 Action: SELL")
        elif 30 <= score <= 40: col2.warning(f"{card}\n\n⚠️ Action: WATCH")
        elif debug_mode: 
            # Show "Retain" funds only if Debug Mode is ON
            st.sidebar.write(f"ℹ️ Retained: {line} ({score:.1f})")

    st.sidebar.metric("Funds Identified", scanned_count)
