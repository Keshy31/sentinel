"""
Project Sentinel - Configuration Constants

This module contains all configuration values, thresholds, and constants
used throughout the application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# API Configuration
# =============================================================================
FRED_API_KEY = os.getenv("FRED_API_KEY")

# =============================================================================
# File Paths
# =============================================================================
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
SA_FISCAL_JSON_PATH = DATA_DIR / "sa_fiscal.json"

# =============================================================================
# FRED Series IDs (US Economic Data)
# =============================================================================
FRED_SERIES = {
    "total_debt": "GFDEBTN",                # Federal Debt: Total Public Debt (Quarterly)
    "interest_payments": "A091RC1Q027SBEA", # Federal Gov Interest Payments (Quarterly)
    "tax_receipts": "W006RC1Q027SBEA",      # Federal Gov Tax Receipts (Quarterly)
    "gdp": "GDP",                           # Gross Domestic Product (Quarterly)
}

# =============================================================================
# Yahoo Finance Tickers
# =============================================================================
YFINANCE_TICKERS = {
    "us_10y_yield": "^TNX",    # 10-Year Treasury Yield
    "usd_zar": "ZAR=X",        # USD/ZAR Exchange Rate
}

# =============================================================================
# Thresholds for Alerts (Doom Loop Detection)
# =============================================================================
THRESHOLDS = {
    # Interest/Revenue Ratio thresholds
    "interest_rev_warning": 0.18,    # 18% - Yellow warning
    "interest_rev_critical": 0.20,   # 20% - Red critical (Doom Loop)
    
    # US 10Y Yield thresholds
    "us_10y_warning": 4.5,           # 4.5% - Elevated
    "us_10y_vigilante": 5.0,         # 5.0% - Bond Vigilante Attack
    
    # USD/ZAR thresholds
    "usd_zar_warning": 18.0,         # Elevated
    "usd_zar_critical": 19.0,        # Critical - Flash warning
}

# =============================================================================
# Dashboard Settings
# =============================================================================
REFRESH_INTERVAL_SECONDS = 60  # How often to refresh data
CHART_HISTORY_MONTHS = 6       # Months of history for sparkline charts

