# --- UPDATED SCORING ENGINE WITH DIFFERENTIAL WEIGHTS ---
def get_strict_score(row):
    try:
        # 1. ALPHA (Weight: 30%) - 10 pts per 1% Alpha, Max 30
        s_alpha = min(30, max(0, float(row['Alpha']) * 10)) if float(row['Alpha']) > 0 else 0
        
        # 2. SHARPE (Weight: 25%) - Reward efficiency > 0.5
        sharpe = float(row['Sharpe'])
        s_sharpe = min(25, max(0, (sharpe - 0.5) * 31.25)) if sharpe > 0.5 else 0
        
        # 3. BETA (Weight: 15%) - Stability Reward
        beta = float(row['Beta'])
        if beta <= 0.9: s_beta = 15
        elif beta <= 1.1: s_beta = 8
        elif beta <= 1.2: s_beta = 4
        else: s_beta = 0
        
        # 4. 3Y CAGR (Weight: 15%) - Momentum
        c3y = float(row['3Y CAGR'])
        s_3y = 15 if c3y >= 18 else (8 if c3y >= 15 else (4 if c3y >= 12 else 0))
        
        # 5. 5Y CAGR (Weight: 15%) - Consistency
        c5y = float(row.get('5Y CAGR', row['3Y CAGR']))
        s_5y = 15 if c5y >= 15 else (8 if c5y >= 12 else (4 if c5y >= 10 else 0))
        
        return round(s_alpha + s_beta + s_sharpe + s_3y + s_5y, 1)
    except: return 0.0

# --- UPDATED TAB 3 (WEIGHTAGE) ---
with tab3:
    st.subheader("Differential Parameter Weightage")
    weight_data = {
        "Metric": ["Alpha", "Sharpe", "Beta", "3Y CAGR", "5Y CAGR"],
        "Points": [30, 25, 15, 15, 15],
        "Weightage": ["30%", "25%", "15%", "15%", "15%"],
        "Role": ["Core Outperformance", "Risk Efficiency", "Volatility Limit", "Medium Momentum", "Long-term Stability"]
    }
    st.table(pd.DataFrame(weight_data))
