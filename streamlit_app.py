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
        
        # Numeric Enforcement for calculations
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

# --- 3. SCORING ENGINE (DIFFERENTIAL WEIGHTS) ---
def get_strict_score(row):
    try:
        # 1. ALPHA (Weight: 30%)
        s_alpha = min(30, max(0, float(row['Alpha']) * 10)) if float(row['Alpha']) > 0 else 0
        
        # 2. SHARPE (Weight: 25%) - Must be > 0.5
        sharpe = float(row['Sharpe'])
        s_sharpe = min(25, max(0, (sharpe - 0.5) * 31.25)) if sharpe > 0.5 else 0
        
        # 3. BETA (Weight: 15%) - Penalty for > 1.2
        beta = float(row['Beta'])
        if beta <= 0.9: s_beta = 15
        elif beta <= 1.1: s_beta = 8
        elif beta <= 1.2: s_beta = 4
        else: s_beta = 0
        
        # 4. 3Y CAGR (Weight: 15%)
        c3y = float(row['3Y CAGR'])
        s_3y = 15 if c3y >= 18 else (8 if c3y >= 15 else (4 if c3y >= 12 else 0))
        
        # 5. 5Y CAGR (Weight: 15%)
        c5y = float(row.get('5Y CAGR', row['3Y CAGR']))
        s_5y = 15 if c5y >= 15 else (8 if c5y >= 12 else (4 if c5y >= 10 else 0))
        
        return round(s_alpha + s_beta + s_sharpe + s_3y + s_5y, 1)
    except: return 0.0

if not master_df.empty:
    master_df['Calculated Score'] = master_df.apply(get_strict_score, axis=1)
    top_recommendations = master_df.sort_values(by='Calculated Score', ascending=False).head(3)

# --- 4. TABS INTERFACE ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Portfolio Review", "🗂️ Master Database", "⚖️ Weightage", "🔢 Scoring Logic"])

# --- TAB 4: SCORING LOGIC ---
with tab4:
    st.subheader("Numerical Scoring Logic")
    st.write("Each parameter earns points only if it crosses the minimum hurdle.")
    logic_data = {
        "Parameter": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"],
        "Perfect (Full Points)": ["> 3.0", "> 1.3", "< 0.9", "> 18%", "> 15%"],
        "Average (Partial Points)": ["~ 1.5", "0.8 - 1.2", "0.9 - 1.1", "15% - 18%", "12% - 15%"],
        "Failing (Zero Points)": ["< 0.0", "< 0.5", "> 1.2", "< 12%", "< 10%"]
    }
    st.table(pd.DataFrame(logic_data))

# --- TAB 3: WEIGHTAGE ---
with tab3:
    st.subheader("
