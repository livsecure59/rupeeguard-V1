import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- 1. CONFIGURATION ---
# Using your specific Sheet ID for a direct CSV export link
SHEET_ID = "1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To"
MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/gviz/tq?tqx=out:csv&sheet=MF%20Assisted%20Sheet"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Tax-Smart Advisor")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv(MASTER_SHEET_URL)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error connecting to Google Sheet: {e}")
        return pd.DataFrame()

master_df = load_master_data()

# --- 3. CLEANING LOGIC (The "Anti-Manual Check" Engine) ---
def clean_name(name):
    if not isinstance(name, str): return ""
    # Strips noise words to match PDF text to your Excel rows
    noise = r"(\bFund\b|\bGrowth\b|\bDirect\b|\bPlan\b|\bIDCW\b|\bRegular\b|Option|LTD|INF\w+)"
    cleaned = re.sub(noise, "", name, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', cleaned)
    return cleaned.lower().strip()

# --- 4. SCORING & TAX LOGIC ---
def get_advice(fund_name, ltcg_remaining):
    cleaned_pdf_name = clean_name(fund_name)
    # Fuzzy match logic
    match = master_df[master_df['Fund Name'].apply(lambda x: cleaned_pdf_name in clean_name(str(x)) or clean_name(str(x)) in cleaned_pdf_name)]
    
    if match.empty:
        return "B", 50.0, "🔍 Manual Review", "Name not recognized in Master Sheet."

    row = match.iloc[0]
    
    # 20% Weight for each of 5 Parameters
    s_alpha = min(20, max(0, (row['Alpha'] + 1) * 6.6)) 
    s_beta = 20 if row['Beta'] < 1.0 else (10 if row['Beta'] < 1.2 else 5)
    s_sharpe = min(20, max(0, row['Sharpe'] * 16))
    s_3y = 20 if row['3Y CAGR'] > 15 else (10 if row['3Y CAGR'] > 10 else 5)
    s_5y = 20 if row.get('5Y CAGR', row['3Y CAGR']) > 12 else (10 if row.get('5Y CAGR', row['3Y CAGR']) > 8 else 5)
    
    score = s_alpha + s_beta + s_sharpe + s_3y + s_5y
    
    # Practical Advisor Thresholds
    if score >= 80:
        return "A", score, "✅ HOLD", "High-performing core holding."
    elif score >= 40:
        return "B", score, "⚠️ MONITOR", "Average metrics. No immediate action needed."
    else:
        # Switch Logic with CGT awareness
        tax_status = "Tax-Efficient" if ltcg_remaining > 10000 else "High Tax Impact"
        advice_text = f"🚨 SWITCH ({tax_status})"
        reason = f"Poor absolute score (< 40). Remaining CGT Limit: ₹{ltcg_remaining:,}."
        return "C", score, advice_text, reason

# --- 5. UI & PARSER ---
with st.sidebar:
    st.header("⚙️ Settings")
    ltcg_input = st.number_input("Remaining LTCG Limit (₹)", value=125000, step=5000)
    st.write("---")
    st.write("**Scoring Logic:**")
    st.write("A: >80 | B: 40-80 | C: <40")

uploaded_file = st.file_uploader("Upload CAS PDF", type="pdf")

if uploaded_file:
    with st.spinner("Analyzing Portfolio..."):
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        
        # Regex to capture fund names
        found_funds = list(set(re.findall(r"([A-Z][A-Za-z\s&]{5,}(?:Fund|Growth|Direct|Plan|IDCW))", text)))

    if found_funds:
        st.subheader("📋 Performance & Tax Action Plan")
        cols = st.columns(3)
        for i, fund in enumerate(found_funds):
            grade, score, action, reason = get_advice(fund, ltcg_input)
            with cols[i % 3]:
                if grade == "A": st.success(f"**{fund}**\n\nScore: **{score:.1f}**\n\n**{action}**\n\n{reason}")
                elif grade == "B": st.warning(f"**{fund}**\n\nScore: **{score:.1f}**\n\n**{action}**\n\n{reason}")
                else: st.error(f"**{fund}**\n\nScore: **{score:.1f}**\n\n**{action}**\n\n{reason}")
    else:
        st.warning("No funds detected. Verify the PDF format.")
