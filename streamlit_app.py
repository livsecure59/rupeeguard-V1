import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
MASTER_SHEET_URL = "https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/gviz/tq?tqx=out:csv&sheet=MF%20Assisted%20Sheet"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Admin & Portfolio Review")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv(MASTER_SHEET_URL)
        df.columns = df.columns.str.strip()
        if 'ISIN' in df.columns:
            df['ISIN'] = df['ISIN'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

master_df = load_master_data()

# --- 3. STRICT SCORING LOGIC ---
def get_strict_score(row):
    s_alpha = max(0, row['Alpha'] * 6.6) if row['Alpha'] > 0 else 0
    if row['Beta'] <= 0.9: s_beta = 20
    elif row['Beta'] <= 1.1: s_beta = 10
    elif row['Beta'] <= 1.2: s_beta = 5
    else: s_beta = 0
    s_sharpe = max(0, (row['Sharpe'] - 0.5) * 25) if row['Sharpe'] > 0.5 else 0
    s_sharpe = min(20, s_sharpe)
    s_3y = 20 if row['3Y CAGR'] >= 18 else (10 if row['3Y CAGR'] >= 15 else (5 if row['3Y CAGR'] >= 12 else 0))
    v5 = row.get('5Y CAGR', row['3Y CAGR'])
    s_5y = 20 if v5 >= 15 else (10 if v5 >= 12 else (5 if v5 >= 10 else 0))
    return round(s_alpha + s_beta + s_sharpe + s_3y + s_5y, 1)

# --- 4. TABS INTERFACE ---
tab1, tab2 = st.tabs(["📊 Portfolio Review", "🗂️ Master Database (Admin)"])

with tab2:
    st.subheader("Entire Master Research Sheet")
    if not master_df.empty:
        admin_df = master_df.copy()
        admin_df['Calculated Score'] = admin_df.apply(get_strict_score, axis=1)
        st.dataframe(admin_df, use_container_width=True)
    else:
        st.error("Master Sheet is empty or not connecting.")

with tab1:
    with st.sidebar:
        ltcg_input = st.number_input("Remaining LTCG (₹)", value=125000)
        if st.button("🔄 Force Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

    if uploaded_file:
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = " ".join([page.extract_text() or "" for page in pdf.pages])
        
        found_isins = list(set(re.findall(r"\b(IN[A-Z0-9]{10})\b", full_text)))
        results = []
        
        for isin in found_isins:
            match = master_df[master_df['ISIN'] == isin]
            if not match.empty:
                row = match.iloc[0]
                score = get_strict_score(row)
                results.append({
                    "Fund": row['Fund Name'], "Score": score, 
                    "Alpha": row['Alpha'], "ISIN": isin
                })

        if results:
            st.subheader("🔍 Scanned from PDF")
            res_df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            st.table(res_df) 
            
            c1, c2, c3 = st.columns(3)
            c1.header("🚀 BUY (90+)")
            c2.header("👀 WATCH (30-50)")
            c3.header("💀 SELL (<30)")

            for item in results:
                s = item['Score']
                card = f"**{item['Fund']}**\n\nScore: **{s}** | Alpha: {item['Alpha']}"
                if s >= 90: c1.success(card)
                elif s < 30: c3.error(f"{card}\n\n🚨 Action: SELL")
                elif 30 <= s <= 50: c2.warning(f"{card}\n\n⚠️ Action: WATCH")
                else: st.info(f"✅ RETAIN: {item['Fund']} (Score: {s})")
