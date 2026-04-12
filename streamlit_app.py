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
        
        # Start index at 1
        df.index = df.index + 1
        return df
    except Exception as e:
        st.error(f"⚠️ Database Connection Error: {e}")
        return pd.DataFrame()

master_df = load_master_data()

# --- 3. SCORING ENGINE ---
def get_strict_score(row):
    try:
        # Alpha: 30% weight (Max 30 pts)
        s_alpha = min(30, max(0, float(row['Alpha']) * 10)) if float(row['Alpha']) > 0 else 0
        # Sharpe: 25% weight (Max 25 pts)
        sharpe = float(row['Sharpe'])
        s_sharpe = min(25, max(0, (sharpe - 0.5) * 31.25)) if sharpe > 0.5 else 0
        # Beta: 15% weight (Max 15 pts)
        beta = float(row['Beta'])
        if beta <= 0.9: s_beta = 15
        elif beta <= 1.1: s_beta = 8
        elif beta <= 1.2: s_beta = 4
        else: s_beta = 0
        # 3Y CAGR: 15% weight (Max 15 pts)
        c3y = float(row['3Y CAGR'])
        s_3y = 15 if c3y >= 18 else (8 if c3y >= 15 else (4 if c3y >= 12 else 0))
        # 5Y CAGR: 15% weight (Max 15 pts)
        c5y = float(row.get('5Y CAGR', row['3Y CAGR']))
        s_5y = 15 if c5y >= 15 else (8 if c5y >= 12 else (4 if c5y >= 10 else 0))
        return round(s_alpha + s_beta + s_sharpe + s_3y + s_5y, 1)
    except: return 0.0

if not master_df.empty:
    master_df['Calculated Score'] = master_df.apply(get_strict_score, axis=1)

# --- 4. TABS INTERFACE ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Portfolio Review", 
    "🗂️ Master Database", 
    "⚖️ Weightage", 
    "🔢 Scoring Logic",
    "📝 Assumptions"
])

with tab5:
    st.subheader("Core Investment Assumptions")
    st.write("The scoring engine operates on these five fundamental assumptions:")
    st.markdown("""
    1. **Alpha (30 Points):** We assume excess return over the benchmark is the primary driver of value. Every 1% of positive Alpha contributes 10 points. Negative Alpha is assumed to be a failure and scores 0.
    2. **Sharpe Ratio (25 Points):** We assume a fund must earn its returns efficiently. We ignore the first 0.5 points of the Sharpe Ratio as a 'baseline.' Any efficiency above 0.5 is rewarded linearly up to a cap of 1.3.
    3. **Beta (15 Points):** We assume lower volatility relative to the market is a virtue. We use a tier-based penalty system:
        * Optimal (≤ 0.9): Full 15 points.
        * Market Standard (0.91 - 1.1): 8 points.
        * High Risk (1.11 - 1.2): 4 points.
        * Failure (> 1.2): 0 points.
    4. **3Y CAGR (15 Points):** We assume medium-term momentum is a trailing indicator of health. Full points are awarded only for returns above 18%.
    5. **5Y CAGR (15 Points):** We assume long-term consistency is the final check. We award full points for returns above 15% over a 5-year horizon.
    """)

with tab4:
    st.subheader("Numerical Scoring Logic")
    logic_data = {
        "Parameter": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"],
        "Max Points": [30, 25, 15, 15, 15],
        "Zero-Point Hurdle": ["≤ 0.0", "≤ 0.5", "> 1.2", "< 12%", "< 10%"],
        "Full-Point Target": ["> 3.0", "> 1.3", "≤ 0.9", "> 18%", "> 15%"]
    }
    st.table(pd.DataFrame(logic_data))

with tab3:
    st.subheader("Differential Weightage Distribution")
    st.table(pd.DataFrame({
        "Metric": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"], 
        "Weight": ["30%", "25%", "15%", "15%", "15%"]
    }))

with tab2:
    st.subheader("Full Database Audit")
    st.dataframe(master_df, use_container_width=True)

with tab1:
    uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")
    if uploaded_file:
        with st.spinner("Extracting ISINs and Valuations..."):
            with pdfplumber.open(uploaded_file) as pdf:
                results, total_val = [], 0
                for page in pdf.pages:
                    words = page.extract_words()
                    target_x = next(((w['x0'] + w['x1'])/2 for w in words if "VALU" in w['text'].upper()), None)
                    for w in words:
                        if re.search(r"IN[A-Z0-9]{10}", w['text']):
                            isin, y = w['text'], (w['top'] + w['bottom'])/2
                            val = 0
                            # Value Extraction
                            row_nums = [n for n in words if abs(((n['top']+n['bottom'])/2) - y) < 8]
                            for n in row_nums:
                                clean = n['text'].replace(',', '')
                                if re.match(r"^\d+\.\d{2}$", clean):
                                    num_val = float(clean)
                                    if target_x and abs(((n['x0']+n['x1'])/2) - target_x) < 60:
                                        val = num_val
                                        break
                                    elif num_val > val: val = num_val
                            match = master_df[master_df['ISIN'] == isin]
                            if not match.empty:
                                res = match.iloc[0]
                                results.append({"Fund": res['Fund Name'], "Score": res['Calculated Score'], "Value": val})
                                total_val += val

        if results:
            st.subheader(f"Portfolio Summary (Total MF Value: ₹{total_val:,.2f})")
            df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            df['% Weight'] = df['Value'].apply(lambda x: round((x/total_val)*100, 1) if total_val > 0 else 0)
            
            display_df = df.copy()
            display_df['Value'] = display_df['Value'].map('₹{:,.2f}'.format)
            st.table(display_df[['Fund', 'Score', 'Value', '% Weight']])
            
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
