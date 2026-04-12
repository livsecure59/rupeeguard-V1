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
        s_alpha = min(30, max(0, float(row['Alpha']) * 10)) if float(row['Alpha']) > 0 else 0
        sharpe = float(row['Sharpe'])
        s_sharpe = min(25, max(0, (sharpe - 0.5) * 31.25)) if sharpe > 0.5 else 0
        beta = float(row['Beta'])
        if beta <= 0.9: s_beta = 15
        elif beta <= 1.1: s_beta = 8
        elif beta <= 1.2: s_beta = 4
        else: s_beta = 0
        c3y = float(row['3Y CAGR'])
        s_3y = 15 if c3y >= 18 else (8 if c3y >= 15 else (4 if c3y >= 12 else 0))
        c5y = float(row.get('5Y CAGR', row['3Y CAGR']))
        s_5y = 15 if c5y >= 15 else (8 if c5y >= 12 else (4 if c5y >= 10 else 0))
        return round(s_alpha + s_beta + s_sharpe + s_3y + s_5y, 1)
    except: return 0.0

if not master_df.empty:
    master_df['Calculated Score'] = master_df.apply(get_strict_score, axis=1)
    top_recommendations = master_df.sort_values(by='Calculated Score', ascending=False).head(3)

# --- 4. TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Portfolio Review", "🗂️ Master Database", "⚖️ Weightage", "🔢 Scoring Logic"])

with tab4:
    st.subheader("Numerical Scoring Logic")
    logic_data = {
        "Parameter": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"],
        "Perfect (Full)": ["> 3.0", "> 1.3", "< 0.9", "> 18%", "> 15%"],
        "Average (Partial)": ["~ 1.5", "0.8-1.2", "0.9-1.1", "15-18%", "12-15%"],
        "Failing (Zero)": ["< 0.0", "< 0.5", "> 1.2", "< 12%", "< 10%"]
    }
    st.table(pd.DataFrame(logic_data))

with tab3:
    st.subheader("Differential Parameter Weightage")
    weight_data = {
        "Metric": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"],
        "Points": [30, 25, 15, 15, 15],
        "Weight": ["30%", "25%", "15%", "15%", "15%"]
    }
    st.table(pd.DataFrame(weight_data))

with tab2:
    st.subheader("Full Database Audit")
    st.dataframe(master_df, use_container_width=True)

with tab1:
    with st.sidebar:
        st.metric("Records", len(master_df))
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")
    if uploaded_file:
        with st.spinner("Analyzing PDF..."):
            with pdfplumber.open(uploaded_file) as pdf:
                results, total_val = [], 0
                for page in pdf.pages:
                    words = page.extract_words()
                    target_x = next(((w['x0'] + w['x1'])/2 for w in words if "VALU" in w['text'].upper()), None)
                    if target_x:
                        for w in words:
                            if re.search(r"IN[A-Z0-9]{10}", w['text']):
                                isin, y = w['text'], (w['top'] + w['bottom'])/2
                                val = 0
                                for n in words:
                                    if abs(((n['top'] + n['bottom'])/2) - y) < 5:
                                        clean = n['text'].replace(',', '')
                                        if re.match(r"^\d+(\.\d{2})?$", clean):
                                            if abs(((n['x0'] + n['x1'])/2) - target_x) < 50:
                                                val = float(clean)
                                                break
                                match = master_df[master_df['ISIN'] == isin]
                                if not match.empty:
                                    res = match.iloc[0]
                                    results.append({"Fund": res['Fund Name'], "Score": res['Calculated Score'], "Value": val})
                                    total_val += val

        if results:
            st.subheader(f"Portfolio Summary (Total: ₹{total_val:,.2f})")
            df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            df['% Weight'] = df['Value'].apply(lambda x: round((x/total_val)*100, 1) if total_val > 0 else 0)
            st.table(df[['Fund', 'Score', 'Value', '% Weight']])
            c1, c2, c3 = st.columns(3)
            c1.header("🚀 BUY")
            c2.header("👀 WATCH")
            c3.header("💀 SELL")
            for _, item in df.iterrows():
                card = f"**{item['Fund']}**\n\nScore: **{item['Score']}** | Weight: **{item['% Weight']}%**"
                if item['Score'] >= 90: c1.success(card)
                elif item['Score'] < 30: c3.error(f"{card}\n\n🚨 SELL")
                elif 30 <= item['Score'] <= 50: c2.warning(f"{card}\n\n⚠️ WATCH")
                else: st.info(f"✅ RETAIN: {item['Fund']} (Score: {item['Score']})")
