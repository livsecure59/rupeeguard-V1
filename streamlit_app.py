import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
SHEET_ID = "1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To"
MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/gviz/tq?tqx=out:csv&sheet=MF%20Assisted%20Sheet"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Full Portfolio Review")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv(MASTER_SHEET_URL)
        df.columns = df.columns.str.strip()
        if 'ISIN' in df.columns:
            df['ISIN'] = df['ISIN'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Data Connection Error: {e}")
        return pd.DataFrame()

master_df = load_master_data()

# --- 3. THE "STRICT" SCORING ENGINE ---
def get_strict_score(row):
    # Alpha Hurdle: 0 points for negative Alpha
    s_alpha = max(0, row['Alpha'] * 6.6) if row['Alpha'] > 0 else 0
    
    # Beta Hurdle: 0 points for high risk (>1.2)
    if row['Beta'] <= 0.9: s_beta = 20
    elif row['Beta'] <= 1.1: s_beta = 10
    elif row['Beta'] <= 1.2: s_beta = 5
    else: s_beta = 0
    
    # Sharpe Hurdle: 0 points for poor efficiency (<0.5)
    s_sharpe = max(0, (row['Sharpe'] - 0.5) * 25) if row['Sharpe'] > 0.5 else 0
    s_sharpe = min(20, s_sharpe)
    
    # CAGR Hurdles: High performance required in bull market
    s_3y = 20 if row['3Y CAGR'] >= 18 else (10 if row['3Y CAGR'] >= 15 else (5 if row['3Y CAGR'] >= 12 else 0))
    val_5y = row.get('5Y CAGR', row['3Y CAGR'])
    s_5y = 20 if val_5y >= 15 else (10 if val_5y >= 12 else (5 if val_5y >= 10 else 0))
    
    return s_alpha + s_beta + s_sharpe + s_3y + s_5y

# --- 4. UI ---
with st.sidebar:
    st.header("⚙️ Settings")
    ltcg_input = st.number_input("Remaining LTCG (₹)", value=125000)
    if st.button("🔄 Force Refresh Data"):
        st.cache_data.clear()
        st.rerun()

uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

if uploaded_file:
    with st.spinner("Analyzing every fund via ISIN..."):
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
                    "Fund Name": row['Fund Name'],
                    "ISIN": isin,
                    "Score": round(score, 1),
                    "Alpha": row['Alpha']
                })

    if results:
        # Show a summary table first so you can see EVERY score
        st.subheader("📊 Scanned Portfolio Summary")
        summary_df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.dataframe(summary_df, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Advisor Action Plan")
        
        col1, col2, col3 = st.columns(3)
        col1.header("🚀 BUY (90+)")
        col2.header("👀 WATCH (30-50)")
        col3.header("💀 SELL (<30)")

        for item in results:
            s = item['Score']
            card = f"**{item['Fund Name']}**\n\nScore: **{s}** | Alpha: {item['Alpha']}"
            
            if s >= 90: col1.success(card)
            elif s < 30: col3.error(f"{card}\n\n🚨 Action: SELL")
            elif 30 <= s <= 50: col2.warning(f"{card}\n\n⚠️ Action: WATCH")
            else:
                # This shows the "Retain" funds in a neutral gray area below
                with st.expander(f"✅ RETAIN: {item['Fund Name']} (Score: {s})"):
                    st.write(f"This fund is healthy. Score of {s} falls within the 51-89 range.")
    else:
        st.info("No funds from your Master Sheet were detected in this PDF. Please check if the ISINs in your sheet match the PDF.")
