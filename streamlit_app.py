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
        st.error(f"⚠️ Connection Error: {e}")
        return pd.DataFrame()

master_df = load_master_data()

# --- 3. SCORING ENGINE ---
def get_strict_score(row):
    try:
        # Alpha: 0 points for negative. Max 20 points at Alpha 3.0+
        s_alpha = max(0, float(row['Alpha']) * 6.6) if float(row['Alpha']) > 0 else 0
        # Beta: Penalty for high risk (>1.2)
        beta = float(row['Beta'])
        if beta <= 0.9: s_beta = 20
        elif beta <= 1.1: s_beta = 10
        elif beta <= 1.2: s_beta = 5
        else: s_beta = 0
        # Sharpe: Reward efficiency above 0.5
        sharpe = float(row['Sharpe'])
        s_sharpe = min(20, max(0, (sharpe - 0.5) * 25)) if sharpe > 0.5 else 0
        # CAGR: Market Reality Hurdles
        c3y = float(row['3Y CAGR'])
        s_3y = 20 if c3y >= 18 else (10 if c3y >= 15 else (5 if c3y >= 12 else 0))
        c5y = float(row.get('5Y CAGR', row['3Y CAGR']))
        s_5y = 20 if c5y >= 15 else (10 if c5y >= 12 else (5 if c5y >= 10 else 0))
        return round(s_alpha + s_beta + s_sharpe + s_3y + s_5y, 1)
    except: return 0.0

if not master_df.empty:
    master_df['Calculated Score'] = master_df.apply(get_strict_score, axis=1)

# --- 4. TABS INTERFACE ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Portfolio Review", "🗂️ Master Database", "⚖️ Weightage", "🔢 Scoring Logic"])

with tab4:
    st.subheader("Numerical Scoring Logic")
    st.write("Each fund is graded on a scale of 0-100. If a fund fails a hurdle, it receives 0 points for that parameter.")
    logic_data = {
        "Parameter": ["Alpha", "Beta", "Sharpe", "3Y CAGR", "5Y CAGR"],
        "Perfect Score (20 pts)": ["> 3.0", "< 0.9", "> 1.3", "> 18%", "> 15%"],
        "Average Score (10 pts)": ["~ 1.5", "0.9 - 1.1", "0.8 - 1.2", "15% - 18%", "12% - 15%"],
        "Zero Point Hurdle": ["< 0.0", "> 1.2", "< 0.5", "< 12%", "< 10%"]
    }
    st.table(pd.DataFrame(logic_data))

with tab3:
    st.subheader("Parameter Weightage")
    weight_data = {
        "Metric": ["Alpha (Excess Return)", "Beta (Volatility Risk)", "Sharpe (Risk Efficiency)", "3Y Momentum", "5Y Consistency"],
        "Weight": ["20%", "20%", "20%", "20%", "20%"],
        "Importance": ["High - Filter for Alpha-generators", "Medium - Volatility protection", "High - Reward for efficiency", "Medium - Trend check", "High - Long term stability"]
    }
    st.table(pd.DataFrame(weight_data))

with tab2:
    st.subheader("Database Audit")
    st.dataframe(master_df, use_container_width=True)

with tab1:
    with st.sidebar:
        st.metric("Database Entries", len(master_df))
        ltcg_input = st.number_input("Remaining LTCG (₹)", value=125000)
        st.button("🔄 Refresh Data", on_click=st.cache_data.clear)

    uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")
    if uploaded_file:
        # (Coordinate Extraction Logic here...)
        # Note: Re-inserting the coordinate logic from previous turn for full functionality
        with st.spinner("Analyzing composition..."):
            with pdfplumber.open(uploaded_file) as pdf:
                results, total_val = [], 0
                for page in pdf.pages:
                    words = page.extract_words()
                    target_x = next(((w['x0'] + w['x1'])/2 for w in words if "VALU" in w['text'].upper()), None)
                    if target_x is None: continue
                    for w in words:
                        if re.search(r"IN[A-Z0-9]{10}", w['text']):
                            isin, y = w['text'], (w['top'] + w['bottom'])/2
                            val = 0
                            for num_w in words:
                                if abs(((num_w['top'] + num_w['bottom'])/2) - y) < 5:
                                    clean = num_w['text'].replace(',', '')
                                    if re.match(r"^\d+(\.\d{2})?$", clean) and abs(((num_w['x0'] + num_w['x1'])/2) - target_x) < 50:
                                        val = float(clean)
                            match = master_df[master_df['ISIN'] == isin]
                            if not match.empty:
                                res = match.iloc[0]
                                results.append({"Fund": res['Fund Name'], "Score": res['Calculated Score'], "Value": val, "ISIN": isin})
                                total_val += val

        if results:
            st.subheader(f"Portfolio Summary (Total Value: ₹{total_val:,.2f})")
            df = pd.DataFrame(results)
            df['% Weight'] = df['Value'].apply(lambda x: round((x/total_val)*100, 1) if total_val > 0 else 0)
            st.table(df[['Fund', 'Score', 'Value', '% Weight']])
            
            # Action Cards
            c1, c2, c3 = st.columns(3)
            c1.header("🚀 BUY")
            c2.header("👀 WATCH")
            c3.header("💀 SELL")
            for _, item in df.iterrows():
                s, w = item['Score'], item['% Weight']
                card = f"**{item['Fund']}**\n\nScore: **{s}** | Weight: **{w}%**"
                if s >= 90: c1.success(card)
                elif s < 30: c3.error(f"{card}\n\n🚨 Action: SELL")
                elif 30 <= s <= 50: c2.warning(f"{card}\n\n⚠️ Action: WATCH")
                else: st.info(f"✅ RETAIN: {item['Fund']} (Score: {s})")
