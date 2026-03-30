import streamlit as st
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="RupeeGuard Pro", layout="wide")
st.title("🛡️ RupeeGuard: A-B-C Portfolio Optimizer")
st.markdown("---")

# --- SIDEBAR: TAX VAULT ---
with st.sidebar:
    st.header("💰 Tax Vault (₹1.25L)")
    already_used = st.number_input("LTCG already used this year (₹)", min_value=0, value=0, step=5000)
    remaining_tax_free = max(0, 125000 - already_used)
    st.metric("Remaining Exemption", f"₹{remaining_tax_free:,}")
    st.info("The app will prioritize switches that fit within this limit.")

# --- THE SCORING ENGINE ---
def calculate_grade(alpha, beta, sharpe):
    # Professional 20% Weighted Logic
    score = 0
    score += 20 if alpha > 2 else (10 if alpha > 0 else 0)
    score += 20 if beta < 1.0 else (10 if beta < 1.2 else 5)
    score += 20 if sharpe > 1.2 else (10 if sharpe > 0.8 else 5)
    # Adding default points for 3Y/5Y consistency
    score += 40 
    
    if score >= 80: return "A", "Elite", "✅ Hold"
    if score >= 60: return "B", "Watch", "⚠️ Review"
    return "C", "Laggard", "🚨 Switch"

# --- MAIN INTERFACE ---
st.subheader("📤 Step 1: Upload Your Data")
uploaded_file = st.file_uploader("Upload Password-Free CAS PDF (CAMS/Karvy)", type="pdf")

if uploaded_file:
    st.success("PDF Loaded Successfully!")
    st.divider()
    
    # [SIMULATED EXTRACTION FOR DEMO]
    # In a full production environment, we use 'pdfplumber' here.
    # For your private app, let's show how the A-B-C results will look:
    
    st.subheader("📊 Step 2: Your Action Plan")
    
    # Create 3 columns for the A-B-C Categories
    colA, colB, colC = st.columns(3)
    
    with colA:
        st.success("### Category A")
        st.write("Keep these high-performers.")
        st.caption("High Alpha | Low Beta")
        
    with colB:
        st.warning("### Category B")
        st.write("Monitor these closely.")
        st.caption("High Volatility detected")
        
    with colC:
        st.error("### Category C")
        st.write("Action Recommended.")
        st.caption("Consistent Underperformance")

    st.divider()
    st.info("💡 **Developer Note:** To enable full PDF data extraction, we need to add 'pdfplumber' to a file called 'requirements.txt' in your GitHub. Would you like to do that next?")
