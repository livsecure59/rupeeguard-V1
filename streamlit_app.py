import streamlit as st
import pandas as pd
import pdfplumber

# --- 1. THE CONNECTION ---
# PASTE YOUR GOOGLE SHEET CSV URL HERE
MASTER_SHEET_URL = "https://docs.google.com/spreadsheets/d/1HhEYGGuxXAWYTA2bQBg7pZNM5ZXtUo47GoS7X_sw9To/gviz/tq?tqx=out:csv&sheet=MF%20Assisted%20Sheet"

st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: Absolute Scoring Engine")

# --- 2. DATA LOADER ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_csv(MASTER_SHEET_URL)
        df.columns = df.columns.str.strip() # Cleans hidden spaces in headers
        return df
    except Exception as e:
        st.error(f"Waiting for Google Sheet Connection... {e}")
        return pd.DataFrame()

master_df = load_master_data()

# --- 3. THE ABSOLUTE 5-PARAMETER MATH ---
def calculate_absolute_score(fund_name):
    # Search for the fund in your 'Fund Name' column
    match = master_df[master_df['Fund Name'].str.contains(fund_name, case=False, na=False)]
    
    if match.empty:
        return None, 0, "🔍 Not in Master List"

    row = match.iloc[0]
    
    # 20% Weightage per Parameter (Targeting 0-100 total)
    # We use 'min/max' to keep scores within the 20pt limit per category
    s_alpha = min(20, max(0, (row['Alpha'] + 1) * 5))  # Scales -1 to 3+ Alpha
    s_beta = 20 if row['Beta'] < 1.0 else (10 if row['Beta'] < 1.2 else 5)
    s_sharpe = min(20, max(0, row['Sharpe'] * 15))    # Scales 0 to 1.3+ Sharpe
    s_3y = 20 if row['3Y CAGR'] > 15 else (10 if row['3Y CAGR'] > 10 else 5)
    s_5y = 20 if row['5Y CAGR'] > 12 else (10 if row['5Y CAGR'] > 8 else 5)
    
    total_score = s_alpha + s_beta + s_sharpe + s_3y + s_5y
    
    if total_score >= 75: return "A", total_score, "✅ High Conviction"
    if total_score >= 55: return "B", total_score, "⚠️ Monitor / Core"
    return "C", total_score, "🚨 Underperformer"

# --- 4. THE DASHBOARD ---
uploaded_file = st.file_uploader("Upload Your CAS PDF", type="pdf")

if uploaded_file:
    with st.spinner("Reading CAS and matching with Master Data..."):
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        
        # Extract fund names (Standard CAMS/Karvy pattern)
        raw_lines = text.split('\n')
        found_funds = list(set([line.split(" - ")[0].strip() for line in raw_lines if "Growth" in line]))

    if found_funds:
        st.subheader("📋 Advisor-Grade Analysis")
        colA, colB, colC = st.columns(3)
        
        for fund in found_funds:
            grade, score, note = calculate_absolute_score(fund)
            
            if grade: # Only show funds found in your Excel
                card = f"**{fund}**\n\nScore: **{score:.1f}/100**\n\n{note}"
                if grade == "A": colA.success(card)
                elif grade == "B": colB.warning(card)
                else: colC.error(card)
    else:
        st.info("No funds detected. Please ensure the PDF is a standard CAS.")
