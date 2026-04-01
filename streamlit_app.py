import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
SHEET_ID = "1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To"
MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/gviz/tq?tqx=out:csv&sheet=MF%20Assisted%20Sheet"

# SEBI Approved/Common AMC Whitelist - Expanded
AMC_WHITELIST = [
    "HDFC", "ICICI", "SBI", "NIPPON", "KOTAK", "AXIS", "UTI", "ADITYA BIRLA", "ABSL", 
    "MIRAE", "DSP", "IDFC", "BANDHAN", "TATA", "HSBC", "FRANKLIN", "CANARA", "ROBECO", 
    "INVESCO", "L&T", "MOTILAL", "OSWAL", "PARAG PARIKH", "PPFAS", "QUANT", "PGIM", 
    "BARODA", "BNP", "MAHINDRA", "MANULIFE", "WHITEAK", "EDELWEISS", "NJ", "NAVI", "GROWW",
    "JM", "TAURUS", "TRUST", "OLD BRIDGE", "SAMCO", "HELIOS", "UNION"
]

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Professional Portfolio Advisor")

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

# --- 3. WHITELIST FILTER & CLEANER ---
def is_valid_fund(name):
    if not name or len(name) < 10: return False
    name_up = name.upper()
    # Check if any AMC name from the whitelist exists as a standalone word
    return any(re.search(rf"\b{amc}\b", name_up) for amc in AMC_WHITELIST)

def get_clean_tokens(name):
    if not name: return set()
    text = re.sub(r'[^a-zA-Z\s]', '', name)
    noise = {'fund', 'growth', 'direct', 'plan', 'idcw', 'regular', 'option', 'pru', 'mutual', 'financial'}
    return {word.lower() for word in text.split() if len(word) > 2 and word.lower() not in noise}

# --- 4. SCORING & SELL ENGINE ---
def get_advice(fund_name, ltcg_remaining):
    if not is_valid_fund(fund_name): return None
    
    pdf_tokens = get_clean_tokens(fund_name)
    best_match = None
    max_overlap = 0
    
    for _, row in master_df.iterrows():
        db_tokens = get_clean_tokens(str(row['Fund Name']))
        overlap = len(pdf_tokens.intersection(db_tokens))
        if overlap > max_overlap:
            max_overlap = overlap
            best_match = row
            
    if max_overlap < 2:
        return "B", 50.0, "⚖️ RETAIN", "Fund recognized but not in Master Data. Retaining."

    # Calculation logic
    s_alpha = min(20, max(0, (best_match['Alpha'] + 1) * 6.6)) 
    s_beta = 20 if best_match['Beta'] < 1.0 else (10 if best_match['Beta'] < 1.2 else 5)
    s_sharpe = min(20, max(0, best_match['Sharpe'] * 16))
    s_3y = 20 if best_match['3Y CAGR'] > 15 else (10 if best_match['3Y CAGR'] > 10 else 5)
    s_5y = 20 if best_match.get('5Y CAGR', best_match['3Y CAGR']) > 12 else (10 if best_match.get('5Y CAGR', best_match['3Y CAGR']) > 8 else 5)
    
    score = s_alpha + s_beta + s_sharpe + s_3y + s_5y
    
    if score >= 80:
        return "A", score, "✅ HOLD", "Core performance holding."
    elif score >= 35:
        return "B", score, "⚖️ RETAIN", "Satisfactory metrics. No action needed."
    else:
        # SELL ADVICE (Below 35)
        tax = "Tax-Free" if ltcg_remaining > 20000 else "Tax-Check"
        return "C", score, f"🚨 SELL ({tax})", f"Underperformer. Available CGT: ₹{ltcg_remaining:,}."

# --- 5. UI ---
with st.sidebar:
    st.header("⚙️ Advisor Settings")
    ltcg_input = st.number_input("Remaining LTCG Limit (₹)", value=125000)

uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    
    # Extract lines and filter via Whitelist
    potential_lines = list(set(re.findall(r"([A-Z][A-Za-z\s&]{10,})", text)))

    st.subheader("📋 Advisor Action Plan")
    cols = st.columns(3)
    display_count = 0
    
    for line in potential_lines:
        res = get_advice(line, ltcg_input)
        if not res: continue
        
        grade, score, action, reason = res
        with cols[display_count % 3]:
            if grade == "A": st.success(f"**{line}**\n\nScore: {score:.1f}\n\n**{action}**\n\n{reason}")
            elif grade == "B": st.warning(f"**{line}**\n\nScore: {score:.1f}\n\n**{action}**\n\n{reason}")
            else: st.error(f"**{line}**\n\nScore: {score:.1f}\n\n**{action}**\n\n{reason}")
        display_count += 1
