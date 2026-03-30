import streamlit as st

# --- THE SCORING BRAIN ---
def get_abc_grade(alpha, ret3y, ret5y, beta, sharpe):
    # Each parameter is scored out of 20 (Total 100)
    score = 0
    score += 20 if alpha > 2 else (10 if alpha > 0 else 0)
    score += 20 if ret3y > 15 else (10 if ret3y > 10 else 5)
    score += 20 if ret5y > 12 else (10 if ret5y > 8 else 5)
    score += 20 if beta < 1.0 else (10 if beta < 1.2 else 5)
    score += 20 if sharpe > 1.2 else (10 if sharpe > 0.8 else 5)
    
    if score >= 80: return "A", "Elite Performance", "✅ Hold"
    if score >= 50: return "B", "Average/Volatile", "⚠️ Watch"
    return "C", "Underperformer", "🚨 Switch Suggested"

# --- THE APP INTERFACE ---
st.title("🛡️ RupeeGuard: A-B-C Portfolio Optimizer")

# Summary Section
st.subheader("Your Action Plan")
col1, col2, col3 = st.columns(3)
col1.metric("Category A", "4 Funds", "Healthy")
col2.metric("Category B", "2 Funds", "-1 Watch", delta_color="off")
col3.metric("Category C", "1 Fund", "Action Needed", delta_color="inverse")

# Mock Recommendation Table
st.markdown("---")
st.write("### Fund Analysis Breakdown")

# Example of how the A-B-C categorization looks
funds = [
    {"Name": "Bluechip Fund X", "Alpha": 3.1, "3Y": 18, "5Y": 14, "Beta": 0.8, "Sharpe": 1.4},
    {"Name": "Small Cap Fund Y", "Alpha": -1.2, "3Y": 9, "5Y": 7, "Beta": 1.4, "Sharpe": 0.5}
]

for f in funds:
    grade, desc, action = get_abc_grade(f['Alpha'], f['3Y'], f['5Y'], f['Beta'], f['Sharpe'])
    with st.expander(f"Grade {grade}: {f['Name']} ({action})"):
        st.write(f"**Analysis:** {desc}")
        st.write(f"* Weightage Breakdown: Alpha(20%), 3Y(20%), 5Y(20%), Beta(20%), Sharpe(20%)")
        if grade == "C":
            st.error(f"Switch recommended to save approx ₹24,000/year in lost Alpha.")
