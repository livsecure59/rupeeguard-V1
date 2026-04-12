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
        df.index = df.index + 1
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
        s_beta = 15 if beta <= 0.9 else (8 if beta <= 1.1 else (4 if beta <= 1.2 else 0))
        c3y = float(row['3Y CAGR'])
        s_3y = 15 if c3y >= 18 else (8 if c3y >= 15 else (4 if c3y >= 12 else 0))
        c5y = float(row.get('5Y CAGR', row['3Y CAGR']))
        s_5y = 15 if c5y >= 15 else (8 if c5y >= 12 else (4 if c5y >= 10 else 0))
        return round(s_alpha + s_beta + s_sharpe + s_3y + s_5y, 1)
    except: return 0.0

if not master_df.empty:
    master_df['Calculated Score'] = master_df.apply(get_strict_score, axis=1)

# --- 4. TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Portfolio Review", "🗂️ Master Database", "⚖️ Weightage", "🔢 Scoring Logic", "📝 Assumptions"])

with tab5:
    st.subheader("Core Investment Assumptions")
    st.markdown("1. **Alpha (30%)**: Primary driver. 2. **Sharpe (25%)**: Efficiency > 0.5. 3. **Beta (15%)**: Reward for stability. 4. **3Y/5Y CAGR (15% each)**: Momentum/Consistency.")

with tab4:
    st.subheader("Numerical Scoring Logic")
    logic_data = {"Parameter": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"], "Max Points": [30, 25, 15, 15, 15], "Hurdle": ["> 0.0", "> 0.5", "< 1.2", "> 12%", "> 10%"]}
    st.table(pd.DataFrame(logic_data))

with tab3:
    st.subheader("Weightage Distribution")
    st.table(pd.DataFrame({"Metric": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"], "Weight": ["30%", "25%", "15%", "15%", "15%"]}))

with tab2:
    st.subheader("Full Database Audit")
    st.dataframe(master_df, use_container_width=True)

with tab1:
    uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")
    if uploaded_file:
        with st.spinner("Consolidating portfolio holdings..."):
            # Dictionary to store unique holdings by ISIN: {isin: total_value}
            consolidated_holdings = {}
            
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    words = page.extract_words()
                    target_x = next(((w['x0'] + w['x1'])/2 for w in words if "VALU" in w['text'].upper()), None)
                    
                    for w in words:
                        if re.search(r"IN[A-Z0-9]{10}", w['text']):
                            isin = w['text']
                            y_level = (w['top'] + w['bottom'])/2
                            
                            # Look for the largest currency number on the same row or row below
                            row_nums = [n for n in words if abs(((n['top']+n['bottom'])/2) - y_level) < 12]
                            val = 0
                            for n in row_nums:
                                clean = n['text'].replace(',', '')
                                if re.match(r"^\d+\.\d{2}$", clean):
                                    num_val = float(clean)
                                    # Preference: Number aligned with 'VALU' header
                                    if target_x and abs(((n['x0']+n['x1'])/2) - target_x) < 70:
                                        val = num_val
                                        break
                                    elif num_val > val: val = num_val
                            
                            if isin in consolidated_holdings:
                                consolidated_holdings[isin] = max(consolidated_holdings[isin], val)
                            else:
                                consolidated_holdings[isin] = val

            results = []
            total_portfolio_val = 0
            for isin, value in consolidated_holdings.items():
                match = master_df[master_df['ISIN'] == isin]
                if not match.empty:
                    res = match.iloc[0]
                    results.append({"Fund": res['Fund Name'], "Score": res['Calculated Score'], "Value": value})
                    total_portfolio_val += value

        if results:
            st.subheader(f"Portfolio Summary (Total MF Value: ₹{total_portfolio_val:,.2f})")
            df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            df['% Weight'] = df['Value'].apply(lambda x: round((x/total_portfolio_val)*100, 1) if total_portfolio_val > 0 else 0)
            
            # Show Table
            display_df = df.copy()
            display_df['Value'] = display_df['Value'].map('₹{:,.2f}'.format)
            st.table(display_df[['Fund', 'Score', 'Value', '% Weight']])
            
            # Action Cards
            c1, c2, c3 = st.columns(3)
            c1.header("🚀 BUY")
            c2.header("👀 WATCH")
            c3.header("💀 SELL")
            for _, item in df.iterrows():
                card = f"**{item['Fund']}**\n\nScore: **{item['Score']}** | Weight: **{item['% Weight']}%**"
                if item['Score'] >= 90: c1.success(card)
                elif item['Score'] < 30: c3.error(f"{card}\n\n🚨 Action: SELL")
                elif 30 <= item['Score'] <= 50: c2.warning(f"{card}\n\n⚠️ Action: WATCH")
                else: st.info(f"✅ RETAIN: {item['Fund']} (Score: {item['Score']})")
