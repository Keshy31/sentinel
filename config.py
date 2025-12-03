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
DB_PATH = PROJECT_ROOT / "sentinel.db"

# =============================================================================
# Country Configurations
# =============================================================================
COUNTRIES = {
    "US": {
        "name": "United States",
        "source_type": "FRED_API",
        "currency_symbol": "$",
        "flag": "🇺🇸",
        "metrics": {
            "total_debt": "GFDEBTN",                # Federal Debt: Total Public Debt
            "interest_payments": "A091RC1Q027SBEA", # Federal Gov Interest Payments
            "tax_receipts": "W006RC1Q027SBEA",      # Federal Gov Tax Receipts
            "gdp": "GDP",                           # Gross Domestic Product
            "gdp_growth": "A191RL1Q225SBEA",        # Real GDP Growth
            "cpi": "CPIAUCSL",                      # Consumer Price Index
            "yield_10y": "^TNX",                    # 10Y Treasury Yield
            "inflation_yoy": "CPIAUCSL",            # Using CPI to calc YoY
            "breakeven_5y": "T5YIE",                # 5-Year Breakeven Inflation Rate
            "term_premium_10y": "ACMTP10",          # 10-Year Term Premium
            "gold": "GC=F"                          # Gold Futures
        },
        "yield_curve": {
            "3M": "^IRX",
            "5Y": "^FVX",
            "10Y": "^TNX",
            "30Y": "^TYX"
        },
        "thresholds": {
            "debt_gdp_warning": 100.0,
            "debt_gdp_critical": 120.0,
            "interest_rev_warning": 0.18,
            "interest_rev_critical": 0.20,
            "yield_10y_vigilante": 5.0
        }
    },
    "SA": {
        "name": "South Africa",
        "source_type": "MANUAL_JSON",
        "currency_symbol": "R",
        "flag": "🇿🇦",
        "json_keys": {
            "total_debt": "debt_zar_billions",
            "interest_payments": "annual_interest_expense_zar_billions",
            "tax_receipts": "annual_revenue_zar_billions",
            "gdp": "gdp_zar_billions",
            "gdp_growth": "gdp_growth_forecast_pct",
            "yield_10y_static": "bond_yield_10y_static"
        },
        "metrics": {
             "yield_10y": "ZAR=X",       # Live Market Data
             "usd_zar": "ZAR=X"
        },
        "yield_curve": {
            "10Y": "ZAR=X"              # Limited yield curve data for SA on Yahoo
        },
        "thresholds": {
            "debt_gdp_warning": 70.0,
            "debt_gdp_critical": 90.0,
            "interest_rev_warning": 0.18,
            "interest_rev_critical": 0.20,
            "currency_risk_critical": 19.0
        }
    },
    "JP": {
        "name": "Japan",
        "source_type": "FRED_API",
        "currency_symbol": "¥",
        "flag": "🇯🇵",
        "metrics": {
            "yield_10y": "IRLTLT01JPM156N",     # FRED Monthly Long-Term Govt Bond Yield
            "gdp": "JPN_GDP_EST",               # Placeholder / Not fetched yet
            "total_debt": "JPN_DEBT_EST"        # Placeholder
        },
        "yield_curve": {},
        "thresholds": {
            "debt_gdp_warning": 200.0,
            "debt_gdp_critical": 250.0,
            "interest_rev_warning": 0.18,
            "interest_rev_critical": 0.20
        }
    },
    "UK": {
        "name": "United Kingdom",
        "source_type": "FRED_API",
        "currency_symbol": "£",
        "flag": "🇬🇧",
        "metrics": {
            "yield_10y": "IRLTLT01GBM156N",     # FRED Monthly Long-Term Govt Bond Yield
            "gdp": "GBR_GDP_EST",
            "total_debt": "GBR_DEBT_EST"
        },
        "yield_curve": {},
        "thresholds": {
            "debt_gdp_warning": 90.0,
            "debt_gdp_critical": 110.0,
            "interest_rev_warning": 0.18,
            "interest_rev_critical": 0.20
        }
    },
    "DE": {
        "name": "Germany",
        "source_type": "FRED_API",
        "currency_symbol": "€",
        "flag": "🇩🇪",
        "metrics": {
            "yield_10y": "IRLTLT01DEM156N",     # FRED Monthly Long-Term Govt Bond Yield
            "gdp": "DEU_GDP_EST",
            "total_debt": "DEU_DEBT_EST"
        },
        "yield_curve": {},
        "thresholds": {
            "debt_gdp_warning": 60.0,
            "debt_gdp_critical": 80.0,
            "interest_rev_warning": 0.18,
            "interest_rev_critical": 0.20
        }
    }
}

# =============================================================================
# Global Series (Net Liquidity & Macros)
# =============================================================================
GLOBAL_SERIES = {
    "fed_assets": "WALCL",                  # Total Assets
    "tga": "WTREGEN",                       # Treasury General Account
    "reverse_repo": "RRPONTSYD",            # Overnight Reverse Repurchase Agreements
    "sp500": "^GSPC"                        # S&P 500
}

# RSS Feeds for News Ticker
RSS_FEEDS = [
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", # CNBC Finance
    "https://finance.yahoo.com/news/rssindex", # Yahoo Finance
    "http://feeds.marketwatch.com/marketwatch/topstories/" # MarketWatch
]

# Legacy mapping for data_loader compatibility
FRED_SERIES = {
    "fed_assets": "WALCL",
    "tga": "WTREGEN",
    "reverse_repo": "RRPONTSYD",
    "cpi": "CPIAUCSL"
}
YFINANCE_TICKERS = {
    "us_10y_yield": "^TNX",
    "us_3m_yield": "^IRX",
    "sp500": "^GSPC",
    "usd_zar": "ZAR=X"
}

# =============================================================================
# Dashboard Settings
# =============================================================================
REFRESH_INTERVAL_SECONDS = 60  # How often to refresh data
CHART_HISTORY_MONTHS = 6       # Months of history for sparkline charts

# =============================================================================
# Cache Settings
# =============================================================================
CACHE_EXPIRY_MACRO = 86400     # 24 hours in seconds
CACHE_EXPIRY_MARKET = 900      # 15 minutes in seconds
