"""
Project Sentinel - Data Loader Module

Handles all data ingestion:
- FRED API: US macroeconomic data (debt, GDP, interest payments, tax receipts)
- YFinance: Live market data (bond yields, exchange rates)
- JSON: South African fiscal data (manual updates)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict

import pandas as pd
import yfinance as yf
from fredapi import Fred

import config
from modules.db_manager import db


def init_db() -> None:
    """Initialize the database."""
    db.init_db()


def get_fred_client() -> Optional[Fred]:
    """
    Initialize FRED API client.
    
    Returns:
        Fred client instance or None if API key not configured
    """
    if not config.FRED_API_KEY or config.FRED_API_KEY == "your_api_key_here":
        print("Warning: FRED_API_KEY not configured. Set it in .env file.")
        return None
    return Fred(api_key=config.FRED_API_KEY)


def is_fresh(timestamp_str: str, max_age_seconds: int) -> bool:
    """Check if a cache entry is fresh."""
    if not timestamp_str:
        return False
    try:
        ts = datetime.fromisoformat(timestamp_str)
        age = (datetime.now() - ts).total_seconds()
        return age < max_age_seconds
    except (ValueError, TypeError):
        return False


def get_cached_or_fetch(
    key: str, 
    fetch_func: callable, 
    expiry_seconds: int, 
    source_name: str,
    errors_list: list
) -> Optional[float]:
    """
    Generic helper to get data from cache or fetch it.
    
    Args:
        key: Metric key for cache
        fetch_func: Function to call if cache miss
        expiry_seconds: Cache validity duration
        source_name: Name of source for error logging
        errors_list: List to append errors to
        
    Returns:
        The metric value (float) or None
    """
    cached = db.get_metric(key)
    
    # If fresh, return it
    if cached and is_fresh(cached['timestamp'], expiry_seconds):
        return cached['value']
        
    # Not fresh or missing, try to fetch
    try:
        val = fetch_func()
        if val is not None:
            db.set_metric(key, val, source_name)
            return val
    except Exception as e:
        errors_list.append(f"{source_name} fetch error: {str(e)}")
    
    # Fetch failed, return stale if available
    if cached:
        # errors_list.append(f"Using stale data for {key}") # Optional: warn about stale data
        return cached['value']
        
    return None


def get_us_metrics() -> dict:
    """
    Fetch all US economic metrics from FRED and YFinance.
    
    Returns:
        Dictionary containing:
        - total_debt: Total public debt (billions)
        - interest_payments: Annual interest expense (billions)
        - tax_receipts: Annual tax revenue (billions)
        - gdp: Gross Domestic Product (billions)
        - yield_10y: Current 10Y Treasury yield (%)
        - last_updated: Timestamp of data fetch
    """
    result = {
        "total_debt": None,
        "interest_payments": None,
        "tax_receipts": None,
        "gdp": None,
        "yield_10y": None,
        "yield_3m": None,
        "gdp_growth": None,
        "inflation_yoy": None,
        "last_updated": datetime.now().isoformat(),
        "errors": []
    }
    
    fred = get_fred_client()
    
    # Helper to fetch specific FRED series
    def fetch_fred_series(series_id):
        if not fred:
            raise Exception("FRED API key missing")
        series = fred.get_series(series_id)
        if series is not None and len(series) > 0:
            latest = series.dropna().iloc[-1]
            val = float(latest)
            if series_id == "GFDEBTN": # Normalize to Billions
                val = val / 1000.0
            return val
        return None

    # Helper to calculate Inflation YoY
    def fetch_inflation_yoy():
        if not fred:
            return None
        # Fetch full series to ensure we have enough history
        # (FRED API is fast enough to fetch all, or we could limit by date, but simple is robust)
        series = fred.get_series(config.FRED_SERIES["cpi"])
        if series is not None and len(series) >= 13:
            series = series.dropna()
            current = series.iloc[-1]
            year_ago = series.iloc[-13]
            return ((current - year_ago) / year_ago) * 100
        return None

    # Process FRED metrics
    for key, series_id in config.FRED_SERIES.items():
        if key == "cpi": continue # Handled separately via inflation calculation
        
        val = get_cached_or_fetch(
            key=key,
            fetch_func=lambda s=series_id: fetch_fred_series(s),
            expiry_seconds=config.CACHE_EXPIRY_MACRO,
            source_name=f"FRED ({series_id})",
            errors_list=result["errors"]
        )
        result[key] = val

    # Process Inflation
    result["inflation_yoy"] = get_cached_or_fetch(
        key="inflation_yoy",
        fetch_func=fetch_inflation_yoy,
        expiry_seconds=config.CACHE_EXPIRY_MACRO,
        source_name="FRED (CPIAUCSL)",
        errors_list=result["errors"]
    )

    # Process US 10Y Yield
    def fetch_us_10y():
        ticker = yf.Ticker(config.YFINANCE_TICKERS["us_10y_yield"])
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None

    result["yield_10y"] = get_cached_or_fetch(
        key="us_10y_yield",
        fetch_func=fetch_us_10y,
        expiry_seconds=config.CACHE_EXPIRY_MARKET,
        source_name="YFinance ^TNX",
        errors_list=result["errors"]
    )

    # Process US 3M Yield (^IRX)
    def fetch_us_3m():
        ticker = yf.Ticker(config.YFINANCE_TICKERS["us_3m_yield"])
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None

    result["yield_3m"] = get_cached_or_fetch(
        key="us_3m_yield",
        fetch_func=fetch_us_3m,
        expiry_seconds=config.CACHE_EXPIRY_MARKET,
        source_name="YFinance ^IRX",
        errors_list=result["errors"]
    )
    
    return result


def get_sa_metrics() -> dict:
    """
    Load South African metrics from JSON file and live USD/ZAR rate.
    
    Returns:
        Dictionary containing metrics.
    """
    result = {
        "debt_zar_billions": None,
        "annual_revenue_zar_billions": None,
        "annual_interest_expense_zar_billions": None,
        "gdp_zar_billions": None,
        "gdp_growth_forecast_pct": None,
        "bond_yield_10y_static": None,
        "usd_zar": None,
        "last_updated": None,
        "errors": []
    }
    
    # Load JSON fiscal data (No caching needed for local file really, but structure implies it's static)
    json_path = config.SA_FISCAL_JSON_PATH
    if json_path.exists():
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            
            result["debt_zar_billions"] = data.get("debt_zar_billions")
            result["annual_revenue_zar_billions"] = data.get("annual_revenue_zar_billions")
            result["annual_interest_expense_zar_billions"] = data.get("annual_interest_expense_zar_billions")
            result["gdp_zar_billions"] = data.get("gdp_zar_billions")
            result["gdp_growth_forecast_pct"] = data.get("gdp_growth_forecast_pct")
            result["bond_yield_10y_static"] = data.get("bond_yield_10y_static")
            result["last_updated"] = data.get("last_updated")
        except Exception as e:
            result["errors"].append(f"JSON load error: {str(e)}")
    else:
        result["errors"].append(f"SA fiscal JSON not found at {json_path}")
    
    # Fetch live USD/ZAR from YFinance (Cached)
    def fetch_usd_zar():
        ticker = yf.Ticker(config.YFINANCE_TICKERS["usd_zar"])
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None

    result["usd_zar"] = get_cached_or_fetch(
        key="usd_zar",
        fetch_func=fetch_usd_zar,
        expiry_seconds=config.CACHE_EXPIRY_MARKET,
        source_name="YFinance ZAR=X",
        errors_list=result["errors"]
    )
    
    return result


def get_live_market_data() -> dict:
    """
    Fetch only the live market data (yields and FX rates).
    """
    result = {
        "us_10y_yield": None,
        "us_3m_yield": None,
        "usd_zar": None,
        "timestamp": datetime.now().isoformat(),
        "errors": []
    }
    
    # Fetch US 10Y Yield
    def fetch_us_10y():
        ticker = yf.Ticker(config.YFINANCE_TICKERS["us_10y_yield"])
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None

    result["us_10y_yield"] = get_cached_or_fetch(
        key="us_10y_yield",
        fetch_func=fetch_us_10y,
        expiry_seconds=config.CACHE_EXPIRY_MARKET,
        source_name="YFinance ^TNX",
        errors_list=result["errors"]
    )

    # Fetch US 3M Yield
    def fetch_us_3m():
        ticker = yf.Ticker(config.YFINANCE_TICKERS["us_3m_yield"])
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None

    result["us_3m_yield"] = get_cached_or_fetch(
        key="us_3m_yield",
        fetch_func=fetch_us_3m,
        expiry_seconds=config.CACHE_EXPIRY_MARKET,
        source_name="YFinance ^IRX",
        errors_list=result["errors"]
    )
    
    # Fetch USD/ZAR
    def fetch_usd_zar():
        ticker = yf.Ticker(config.YFINANCE_TICKERS["usd_zar"])
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None

    result["usd_zar"] = get_cached_or_fetch(
        key="usd_zar",
        fetch_func=fetch_usd_zar,
        expiry_seconds=config.CACHE_EXPIRY_MARKET,
        source_name="YFinance ZAR=X",
        errors_list=result["errors"]
    )
    
    return result


def get_historical_data(ticker_symbol: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """
    Fetch historical price data for charting.
    
    Args:
        ticker_symbol: YFinance ticker (e.g., "^TNX", "ZAR=X")
        period: Time period (e.g., "6mo", "1y", "3mo")
    
    Returns:
        DataFrame with Date index and Close prices, or None on error
    """
    
    # Check cache
    cached = db.get_chart(ticker_symbol)
    if cached and is_fresh(cached['timestamp'], config.CACHE_EXPIRY_MARKET):
        return cached['data']

    # Special handling for US Growth Spread
    if ticker_symbol == "US_GROWTH_SPREAD":
        try:
            # Fetch US 10Y Yield History
            ticker = yf.Ticker(config.YFINANCE_TICKERS["us_10y_yield"])
            hist = ticker.history(period=period)
            
            # Fetch latest GDP Growth (use static scalar for this 6mo view)
            # In a full production app, we would resample quarterly GDP to daily
            gdp_growth_entry = db.get_metric("gdp_growth")
            gdp_growth = gdp_growth_entry['value'] if gdp_growth_entry else 2.0 # Fallback default
            
            if not hist.empty:
                # Calculate Spread: Yield - GDP Growth
                hist["Close"] = hist["Close"] - gdp_growth
                df = hist[["Close"]]
                db.set_chart(ticker_symbol, df)
                return df
            return None
        except Exception as e:
            print(f"Error calculating US Growth Spread: {e}")
            return None
        
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period)
        if not hist.empty:
            df = hist[["Close"]]
            db.set_chart(ticker_symbol, df)
            return df
        return None
    except Exception as e:
        print(f"Error fetching historical data for {ticker_symbol}: {e}")
        # Return stale if available
        if cached:
            return cached['data']
        return None
