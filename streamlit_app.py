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

with tab1:
    uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")
    if uploaded_file:
        with st.spinner("Filtering for Actionable Funds..."):
            holdings = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    words = page.extract_words()
                    target_x = next(((w['x0'] + w['x1'])/2 for w in words if "VALU" in w['text'].upper()), None)
                    
                    for w in words:
                        if re.search(r"IN[A-Z0-9]{10}", w['text']):
                            isin = w['text']
                            
                            # Whitelist check against Master Sheet
                            match = master_df[master_df['ISIN'] == isin]
                            if not match.empty:
                                y_mid = (w['top'] + w['bottom']) / 2
                                row_values = [n for n in words if abs(((n['top']+n['bottom'])/2) - y_mid) < 15]
                                fund_val = 0
                                for n in row_values:
                                    clean = n['text'].replace(',', '')
                                    if re.match(r"^\d+\.\d{2}$", clean):
                                        num = float(clean)
                                        if target_x and abs(((n['x0']+n['x1'])/2) - target_x) < 80:
                                            fund_val = num
                                            break
                                        elif num > fund_val: fund_val = num
                                
                                res = match.iloc[0]
                                holdings.append({
                                    "Fund": res['Fund Name'], 
                                    "Score": res['Calculated Score'], 
                                    "Value": fund_val, 
                                    "ISIN": isin
                                })

            if holdings:
                pdf_df = pd.DataFrame(holdings)
                # Consolidate duplicate ISINs
                pdf_df = pdf_df.groupby(['Fund', 'ISIN', 'Score'], as_index=False)['Value'].sum()
                pdf_df = pdf_df.sort_values(by="Score", ascending=False)
                
                # Global total for Weightage calculation only
                actual_total = pdf_df['Value'].sum()
                pdf_df['% Weight'] = pdf_df['Value'].apply(lambda x: round((x/actual_total)*100, 2) if actual_total > 0 else 0)
                
                # Reset index to start from 1
                pdf_df.index = range(1, len(pdf_df) + 1)

                st.subheader(f"Equity Portfolio Summary (Actionable Funds: {len(pdf_df)})")

                def color_rows(row):
                    if row.Score >= 90: return ['background-color: #d4edda'] * len(row)
                    elif row.Score < 30: return ['background-color: #f8d7da'] * len(row)
                    elif 30 <= row.Score <= 50: return ['background-color: #fff3cd'] * len(row)
                    else: return [''] * len(row)

                styled_df = pdf_df[['Fund', 'Score', 'Value', '% Weight']].style.apply(color_rows, axis=1).format({'Value': '₹{:,.2f}'})
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.warning("No actionable equity funds from your Master Sheet found. (Debt/Unindexed funds filtered out).")

# --- OTHER TABS ---
with tab2:
    master_df.index = range(1, len(master_df) + 1)
    st.dataframe(master_df, use_container_width=True)

with tab3:
    st.table(pd.DataFrame({"Metric": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"], "Weight": ["30%", "25%", "15%", "15%", "15%"]}))

with tab4:
    st.table(pd.DataFrame({"Parameter": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"], "Max Points": [30, 25, 15, 15, 15], "Hurdle": ["> 0.0", "> 0.5", "< 1.2", "> 12%", "> 10%"]}))

with tab5:
    st.write("Assumptions: Analysis excludes debt and unindexed funds. Actionable funds are those mapped to your master equity database.")
