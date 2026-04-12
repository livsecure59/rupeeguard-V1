import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
MASTER_SHEET_URL = "https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/gviz/tq?tqx=out:csv&sheet=MF%20Assisted%20Sheet"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Pro Advisor (Header-Mapping Mode)")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv(MASTER_SHEET_URL)
        df.columns = df.columns.str.strip()
        if 'ISIN' in df.columns:
            df['ISIN'] = df['ISIN'].astype(str).str.strip()
        return df
    except: return pd.DataFrame()

master_df = load_master_data()

# --- 3. SCORING ENGINE ---
def get_strict_score(row):
    s_alpha = max(0, row['Alpha'] * 6.6) if row['Alpha'] > 0 else 0
    s_beta = 20 if row['Beta'] <= 0.9 else (10 if row['Beta'] <= 1.1 else (5 if row['Beta'] <= 1.2 else 0))
    s_sharpe = min(20, max(0, (row['Sharpe'] - 0.5) * 25)) if row['Sharpe'] > 0.5 else 0
    s_3y = 20 if row['3Y CAGR'] >= 18 else (10 if row['3Y CAGR'] >= 15 else (5 if row['3Y CAGR'] >= 12 else 0))
    v5 = row.get('5Y CAGR', row['3Y CAGR'])
    s_5y = 20 if v5 >= 15 else (10 if v5 >= 12 else (5 if v5 >= 10 else 0))
    return round(s_alpha + s_beta + s_sharpe + s_3y + s_5y, 1)

if not master_df.empty:
    master_df['Calculated Score'] = master_df.apply(get_strict_score, axis=1)
    top_recommendations = master_df.sort_values(by='Calculated Score', ascending=False).head(3)

# --- 4. PDF ENGINE (Coordinate Based) ---
def extract_portfolio_with_coords(pdf_file):
    results = []
    total_val = 0
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            
            # 1. Find the horizontal position of the "VALU" header
            valu_x_center = None
            for w in words:
                if "VALU" in w['text'].upper():
                    valu_x_center = (w['x0'] + w['x1']) / 2
                    break
            
            if valu_x_center is None: continue
            
            # 2. Extract lines to find ISINs
            lines = page.extract_text().split('\n')
            page_text_objs = page.extract_words()
            
            # We look for ISINs and then find the number closest to valu_x_center on the same vertical level
            for obj in page_text_objs:
                isin_match = re.search(r"IN[A-Z0-9]{10}", obj['text'])
                if isin_match:
                    isin = isin_match.group(0)
                    y_level = (obj['top'] + obj['bottom']) / 2
                    
                    # Find numbers on this same Y level (allow 5pt tolerance) 
                    # that are horizontally aligned with the VALU header
                    current_fund_value = 0
                    for val_obj in page_text_objs:
                        # Check vertical alignment (same line)
                        if abs(((val_obj['top'] + val_obj['bottom']) / 2) - y_level) < 5:
                            # Check if it's a number
                            clean_val = val_obj['text'].replace(',', '')
                            if re.match(r"^\d+(\.\d{2})?$", clean_val):
                                # Check horizontal alignment with VALU header
                                if abs(((val_obj['x0'] + val_obj['x1']) / 2) - valu_x_center) < 40:
                                    current_fund_value = float(clean_val)
                                    break
                    
                    match = master_df[master_df['ISIN'] == isin]
                    if not match.empty:
                        row = match.iloc[0]
                        results.append({
                            "Fund": row['Fund Name'],
                            "Score": row['Calculated Score'],
                            "Value": current_fund_value,
                            "ISIN": isin
                        })
                        total_val += current_fund_value
                        
    return results, total_val

# --- 5. UI ---
tab1, tab2 = st.tabs(["📊 Portfolio Review", "🗂️ Master Database"])

with tab2:
    st.dataframe(master_df, use_container_width=True)

with tab1:
    uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

    if uploaded_file:
        with st.spinner("Mapping column coordinates..."):
            results, total_portfolio_value = extract_portfolio_with_coords(uploaded_file)

        if results:
            for item in results:
                item['% Weight'] = round((item['Value'] / total_portfolio_value) * 100, 1) if total_portfolio_value > 0 else 0

            st.subheader(f"Portfolio Summary (Total Value: ₹{total_portfolio_value:,.2f})")
            res_df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            st.table(res_df[['Fund', 'Score', 'Value', '% Weight']])
            
            c1, c2, c3 = st.columns(3)
            c1.header("🚀 BUY (90+)")
            c2.header("👀 WATCH (30-50)")
            c3.header("💀 SELL (<30)")

            has_sell = False
            for item in results:
                s = item['Score']
                card = f"**{item['Fund']}**\n\nScore: **{s}** | Weight: **{item['% Weight']}%**"
                if s >= 90: c1.success(card)
                elif s < 30: 
                    c3.error(f"{card}\n\n🚨 Action: SELL")
                    has_sell = True
                elif 30 <= s <= 50: c2.warning(f"{card}\n\n⚠️ Action: WATCH")
                else: st.info(f"✅ RETAIN: {item['Fund']} (Score: {s})")

            if has_sell:
                st.markdown("---")
                st.subheader("💡 Reinvestment Strategy")
                cols = st.columns(3)
                for i, (_, rec) in enumerate(top_recommendations.iterrows()):
                    with cols[i]:
                        st.success(f"**{rec['Fund Name']}**\n\nScore: **{rec['Calculated Score']}**")
