def get_abc_grade(fund_name, alpha=None, beta=None, sharpe=None):
    # 1. Noise Filter (Still needed to keep the UI clean)
    noise_keywords = ["Growth Option", "Scheme Code", "ISIN", "Folio", "PAN", "Nominee", "19. ", "21. "]
    if any(word in fund_name for word in noise_keywords) or len(fund_name) < 12:
        return None, None, None

    # 2. Advisor-Led Logic (Quality & Risk-Adjusted Returns)
    # Since we are currently extracting from PDF, we will default to 'B' 
    # and only move to 'A' or 'C' based on performance metrics.
    
    # Placeholder: In the next step, we will link these to real API values
    # For now, we treat all legitimate advisor-selected funds as 'Stable'
    
    if "Liquid" in fund_name or "Overnight" in fund_name:
        return "A", "Low Risk/Cash", "✅ Hold (Liquidity)"
    
    # If the fund is a Large/Mid/Multi Cap, we label as B (Core) 
    # until the Performance Scraper confirms an 'A' grade.
    return "B", "Core Portfolio", "⚠️ Monitor Performance"
