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
        st.error(f"⚠️ Database Error: {e}")
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
    top_picks = master_df.sort_values(by='Calculated Score', ascending=False).head(3)

# --- 4. TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Portfolio Review", "🗂️ Master Database", "⚖️ Weightage", 
    "🔢 Scoring Logic", "📝 Assumptions", "🔍 CAS Reconciliation"
])

# Use session state to keep data across tabs
if 'recon_data' not in st.session_state: st.session_state.recon_data = []
if 'portfolio_results' not in st.session_state: st.session_state.portfolio_results = []
if 'total_val' not in st.session_state: st.session_state.total_val = 0

with tab1:
    uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")
    if uploaded_file:
        portfolio_map = {}
        recon_accumulator = []
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                words = page.extract_words()
                # Locate 'VALU' header to find the correct column
                target_x = next(((w['x0'] + w['x1'])/2 for w in words if "VALU" in w['text'].upper()), None)
                
                for w in words:
                    # Catch any ISIN-like string (12 chars)
                    if re.search(r"[A-Z0-9]{12}", w['text']):
                        isin = w['text']
                        y = (w['top'] + w['bottom'])/2
                        
                        # Grab numbers on the same line
                        row_nums = []
                        for n in words:
                            if abs(((n['top']+n['bottom'])/2) - y) < 6:
                                clean = n['text'].replace(',', '')
                                if re.match(r"^\d+\.\d{2}$", clean):
                                    # Calculate distance to 'VALU' header
                                    dist = abs(((n['x0']+n['x1'])/2) - target_x) if target_x else 999
                                    row_nums.append({'val': float(clean), 'dist': dist})
                        
                        # Select best value: closest to 'VALU' header, else largest on line
                        best_val = 0
                        if row_nums:
                            row_nums.sort(key=lambda x: x['dist'])
                            best_val = row_nums[0]['val']
                        
                        # Consolidate duplicate ISINs
                        portfolio_map[isin] = portfolio_map.get(isin, 0) + best_val

        # Map to Master Sheet
        final_list = []
        total_sum = 0
        st.session_state.recon_data = []
        
        for isin, val in portfolio_map.items():
            match = master_df[master_df['ISIN'] == isin]
            if not match.empty:
                res = match.iloc[0]
                final_list.append({"Fund": res['Fund Name'], "Score": res['Calculated Score'], "Value": val})
                total_sum += val
                st.session_state.recon_data.append({"ISIN": isin, "Name": res['Fund Name'], "Status": "Matched", "Value": val})
            else:
                st.session_state.recon_data.append({"ISIN": isin, "Name": "Unknown / Debt", "Status": "Filtered", "Value": val})

        if final_list:
            st.subheader(f"Equity Portfolio Summary (Total: ₹{total_sum:,.2f})")
            df = pd.DataFrame(final_list).sort_values(by="Score", ascending=False)
            df.insert(0, 'Sr No.', range(1, len(df) + 1))
            df['% Weight'] = df['Value'].apply(lambda x: round((x/total_sum)*100, 2) if total_sum > 0 else 0)
            
            disp = df.copy()
            disp['Value'] = disp['Value'].map('₹{:,.2f}'.format)
            st.table(disp[['Sr No.', 'Fund', 'Score', 'Value', '% Weight']])
            
            c1, c2, c3 = st.columns(3)
            c1.header("🚀 BUY (90+)")
            c2.header("👀 WATCH (30-50)")
            c3.header("💀 SELL (<30)")
            for _, item in df.iterrows():
                card = f"**{item['Fund']}**\n\nScore: **{item['Score']}** | Weight: **{item['% Weight']}%**"
                if item['Score'] >= 90: c1.success(card)
                elif item['Score'] < 30: c3.error(f"{card}\n\n🚨 SELL")
                elif 30 <= item['Score'] <= 50: c2.warning(f"{card}\n\n⚠️ WATCH")
                else: st.info(f"✅ RETAIN: {item['Fund']}")

with tab6:
    st.subheader("CAS Data Reconciliation")
    st.write("This shows every ISIN detected. Use this to find why funds might be missing.")
    if st.session_state.recon_data:
        st.dataframe(pd.DataFrame(st.session_state.recon_data), use_container_width=True)

with tab5:
    st.subheader("Detailed Investment Assumptions")
    st.markdown("""
    - **Alpha (30%):** Calculated as (Alpha * 10). Max 30 points at 3.0 Alpha.
    - **Sharpe (25%):** Reward efficiency > 0.5. Calculated as (Sharpe - 0.5) * 31.25.
    - **Beta (15%):** Tiered scoring (15 pts for ≤ 0.9, 8 pts for ≤ 1.1, 4 pts for ≤ 1.2).
    - **3Y CAGR (15%):** Hurdle based (15 pts for > 18%, 8 pts for > 15%).
    - **5Y CAGR (15%):** Hurdle based (15 pts for > 15%, 8 pts for > 12%).
    """)

with tab2:
    st.dataframe(master_df, use_container_width=True)

with tab3:
    st.table(pd.DataFrame({"Metric": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"], "Weight": ["30%", "25%", "15%", "15%", "15%"]}))

with tab4:
    st.table(pd.DataFrame({"Param": ["Alpha", "Sharpe", "Beta", "3Y", "5Y"], "Full Pts Target": [">3.0", ">1.3", "<0.9", ">18%", ">15%"], "Zero Hurdle": ["<0", "<0.5", ">1.2", "<12%", "<10%"]}))
