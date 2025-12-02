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
from typing import Optional

import pandas as pd
import yfinance as yf
from fredapi import Fred

import config


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
        "last_updated": datetime.now().isoformat(),
        "errors": []
    }
    
    # Fetch FRED data
    fred = get_fred_client()
    if fred:
        try:
            # Get most recent value for each series
            for key, series_id in config.FRED_SERIES.items():
                try:
                    series = fred.get_series(series_id)
                    if series is not None and len(series) > 0:
                        # Get most recent non-NaN value
                        latest = series.dropna().iloc[-1]
                        result[key] = float(latest)
                except Exception as e:
                    result["errors"].append(f"FRED {series_id}: {str(e)}")
        except Exception as e:
            result["errors"].append(f"FRED connection: {str(e)}")
    else:
        result["errors"].append("FRED API key not configured")
    
    # Fetch live 10Y yield from YFinance
    try:
        ticker = yf.Ticker(config.YFINANCE_TICKERS["us_10y_yield"])
        hist = ticker.history(period="1d")
        if not hist.empty:
            result["yield_10y"] = float(hist["Close"].iloc[-1])
    except Exception as e:
        result["errors"].append(f"YFinance ^TNX: {str(e)}")
    
    return result


def get_sa_metrics() -> dict:
    """
    Load South African metrics from JSON file and live USD/ZAR rate.
    
    Returns:
        Dictionary containing:
        - debt_zar_billions: Total debt in ZAR billions
        - annual_revenue_zar_billions: Annual revenue in ZAR billions
        - annual_interest_expense_zar_billions: Interest expense in ZAR billions
        - gdp_growth_forecast_pct: GDP growth forecast (%)
        - bond_yield_10y_static: Static 10Y bond yield (%)
        - usd_zar: Live USD/ZAR exchange rate
        - last_updated: When JSON was last updated
        - errors: List of any errors encountered
    """
    result = {
        "debt_zar_billions": None,
        "annual_revenue_zar_billions": None,
        "annual_interest_expense_zar_billions": None,
        "gdp_growth_forecast_pct": None,
        "bond_yield_10y_static": None,
        "usd_zar": None,
        "last_updated": None,
        "errors": []
    }
    
    # Load JSON fiscal data
    json_path = config.SA_FISCAL_JSON_PATH
    if json_path.exists():
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            
            result["debt_zar_billions"] = data.get("debt_zar_billions")
            result["annual_revenue_zar_billions"] = data.get("annual_revenue_zar_billions")
            result["annual_interest_expense_zar_billions"] = data.get("annual_interest_expense_zar_billions")
            result["gdp_growth_forecast_pct"] = data.get("gdp_growth_forecast_pct")
            result["bond_yield_10y_static"] = data.get("bond_yield_10y_static")
            result["last_updated"] = data.get("last_updated")
        except json.JSONDecodeError as e:
            result["errors"].append(f"JSON parse error: {str(e)}")
        except Exception as e:
            result["errors"].append(f"JSON load error: {str(e)}")
    else:
        result["errors"].append(f"SA fiscal JSON not found at {json_path}")
    
    # Fetch live USD/ZAR from YFinance
    try:
        ticker = yf.Ticker(config.YFINANCE_TICKERS["usd_zar"])
        hist = ticker.history(period="1d")
        if not hist.empty:
            result["usd_zar"] = float(hist["Close"].iloc[-1])
    except Exception as e:
        result["errors"].append(f"YFinance ZAR=X: {str(e)}")
    
    return result


def get_live_market_data() -> dict:
    """
    Fetch only the live market data (yields and FX rates).
    
    This is a lighter-weight call for more frequent updates.
    
    Returns:
        Dictionary containing:
        - us_10y_yield: Current 10Y Treasury yield (%)
        - usd_zar: USD/ZAR exchange rate
        - timestamp: When data was fetched
        - errors: List of any errors encountered
    """
    result = {
        "us_10y_yield": None,
        "usd_zar": None,
        "timestamp": datetime.now().isoformat(),
        "errors": []
    }
    
    # Fetch US 10Y yield
    try:
        ticker = yf.Ticker(config.YFINANCE_TICKERS["us_10y_yield"])
        hist = ticker.history(period="1d")
        if not hist.empty:
            result["us_10y_yield"] = float(hist["Close"].iloc[-1])
    except Exception as e:
        result["errors"].append(f"YFinance ^TNX: {str(e)}")
    
    # Fetch USD/ZAR
    try:
        ticker = yf.Ticker(config.YFINANCE_TICKERS["usd_zar"])
        hist = ticker.history(period="1d")
        if not hist.empty:
            result["usd_zar"] = float(hist["Close"].iloc[-1])
    except Exception as e:
        result["errors"].append(f"YFinance ZAR=X: {str(e)}")
    
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
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period)
        if not hist.empty:
            return hist[["Close"]]
        return None
    except Exception as e:
        print(f"Error fetching historical data for {ticker_symbol}: {e}")
        return None

