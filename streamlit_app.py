import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
MASTER_SHEET_URL = "https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/gviz/tq?tqx=out:csv&sheet=MF%20Assisted%20Sheet"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Pro Advisor (Fixed Scoring)")

# --- 2. DATA LOADER (With Numeric Enforcement) ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv(MASTER_SHEET_URL)
        df.columns = df.columns.str.strip()
        
        # Force these columns to be numbers, turning errors into 0
        num_cols = ['Alpha', 'Beta', 'Sharpe', '3Y CAGR', '5Y CAGR']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        if 'ISIN' in df.columns:
            df['ISIN'] = df['ISIN'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

master_df = load_master_data()

# --- 3. SCORING ENGINE (More Robust) ---
def get_strict_score(row):
    try:
        # Alpha: 20% weight (0 points if negative)
        s_alpha = max(0, float(row['Alpha']) * 6.6) if float(row['Alpha']) > 0 else 0
        
        # Beta: 20% weight
        beta = float(row['Beta'])
        if beta <= 0.9: s_beta = 20
        elif beta <= 1.1: s_beta = 10
        elif beta <= 1.2: s_beta = 5
        else: s_beta = 0
        
        # Sharpe: 20% weight
        sharpe = float(row['Sharpe'])
        s_sharpe = min(20, max(0, (sharpe - 0.5) * 25)) if sharpe > 0.5 else 0
        
        # 3Y CAGR: 20% weight
        c3y = float(row['3Y CAGR'])
        s_3y = 20 if c3y >= 18 else (10 if c3y >= 15 else (5 if c3y >= 12 else 0))
        
        # 5Y CAGR: 20% weight
        c5y = float(row.get('5Y CAGR', row['3Y CAGR']))
        s_5y = 20 if c5y >= 15 else (10 if c5y >= 12 else (5 if c5y >= 10 else 0))
        
        return round(s_alpha + s_beta + s_sharpe + s_3y + s_5y, 1)
    except:
        return 0.0

# Pre-calculate scores for all items
if not master_df.empty:
    master_df['Calculated Score'] = master_df.apply(get_strict_score, axis=1)
    top_recommendations = master_df.sort_values(by='Calculated Score', ascending=False).head(3)

# --- 4. PDF ENGINE (Coordinate Mapping) ---
def extract_data(pdf_file):
    results, total_val = [], 0
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            # Find VALU header x-position
            target_x = next(((w['x0'] + w['x1'])/2 for w in words if "VALU" in w['text'].upper()), None)
            if target_x is None: continue
            
            # Map ISINs to their Y-levels
            for w in words:
                if re.search(r"IN[A-Z0-9]{10}", w['text']):
                    isin = w['text']
                    y = (w['top'] + w['bottom'])/2
                    # Find value on same row
                    val = 0
                    for num_w in words:
                        if abs(((num_w['top'] + num_w['bottom'])/2) - y) < 5:
                            clean = num_w['text'].replace(',', '')
                            if re.match(r"^\d+(\.\d{2})?$", clean):
                                if abs(((num_w['x0'] + num_w['x1'])/2) - target_x) < 50:
                                    val = float(clean)
                    
                    match = master_df[master_df['ISIN'] == isin]
                    if not match.empty:
                        res = match.iloc[0]
                        results.append({"Fund": res['Fund Name'], "Score": res['Calculated Score'], "Value": val, "ISIN": isin})
                        total_val += val
    return results, total_val

# --- 5. UI ---
tab1, tab2 = st.tabs(["📊 Portfolio Review", "🗂️ Master Database"])

with tab2:
    st.subheader("Master Sheet Audit")
    st.dataframe(master_df[['Fund Name', 'ISIN', 'Calculated Score', 'Alpha', 'Beta', 'Sharpe']])

with tab1:
    uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")
    if uploaded_file:
        data, total = extract_data(uploaded_file)
        if data:
            st.subheader(f"Portfolio Summary (Total: ₹{total:,.2f})")
            df = pd.DataFrame(data)
            df['% Weight'] = df['Value'].apply(lambda x: round((x/total)*100, 1) if total > 0 else 0)
            st.table(df[['Fund', 'Score', 'Value', '% Weight']])
            
            c1, c2, c3 = st.columns(3)
            c1.header("🚀 BUY (90+)")
            c2.header("👀 WATCH (30-50)")
            c3.header("💀 SELL (<30)")
            
            for _, item in df.iterrows():
                s, w = item['Score'], item['% Weight']
                card = f"**{item['Fund']}**\n\nScore: **{s}** | Weight: **{w}%**"
                if s >= 90: c1.success(card)
                elif s < 30: c3.error(f"{card}\n\n🚨 Action: SELL")
                elif 30 <= s <= 50: c2.warning(f"{card}\n\n⚠️ Action: WATCH")
                else: st.info(f"✅ RETAIN: {item['Fund']} (Score: {s})")
