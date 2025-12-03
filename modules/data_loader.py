"""
Project Sentinel - Data Loader Module

Handles all data ingestion:
- FRED API: US macroeconomic data (debt, GDP, interest payments, tax receipts)
- YFinance: Live market data (bond yields, exchange rates)
- JSON: South African fiscal data (manual updates)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Dict, List

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


def get_country_metrics(country_code: str) -> dict:
    """
    Fetch standard metrics for a specific country.
    
    Args:
        country_code: 'US' or 'SA' (must exist in config.COUNTRIES)
        
    Returns:
        Dictionary containing standard metrics:
        - total_debt
        - interest_payments
        - tax_receipts
        - gdp
        - gdp_growth
        - yield_10y
        - inflation_yoy
        - last_updated
    """
    if country_code not in config.COUNTRIES:
        return {"errors": [f"Unknown country code: {country_code}"]}
        
    country_config = config.COUNTRIES[country_code]
    source_type = country_config.get("source_type")
    
    # Initialize result with standard keys
    result = {
        "total_debt": None,
        "interest_payments": None,
        "tax_receipts": None,
        "gdp": None,
        "gdp_growth": None,
        "yield_10y": None,
        "inflation_yoy": None,
        "currency_symbol": country_config.get("currency_symbol", ""),
        "last_updated": datetime.now().isoformat(),
        "errors": []
    }
    
    if source_type == "FRED_API":
        _fetch_fred_metrics(country_config, result)
    elif source_type == "MANUAL_JSON":
        _fetch_json_metrics(country_config, result)
        
    # Always try to fetch live market data (Yields/FX) if configured
    _fetch_live_market_data(country_config, result)
    
    return result


def _fetch_fred_metrics(country_config: dict, result: dict):
    """Fetch metrics from FRED API."""
    fred = get_fred_client()
    metrics_map = country_config.get("metrics", {})
    
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

    def fetch_inflation_yoy(series_id):
        if not fred: return None
        series = fred.get_series(series_id)
        if series is not None and len(series) >= 13:
            series = series.dropna()
            current = series.iloc[-1]
            year_ago = series.iloc[-13]
            return ((current - year_ago) / year_ago) * 100
        return None

    for key, series_id in metrics_map.items():
        # Skip market data tickers (start with ^ or look like tickers)
        if key == "yield_10y" or key == "usd_zar": continue 
        
        # Special handling for inflation
        if key == "inflation_yoy":
             val = get_cached_or_fetch(
                key=f"{series_id}_yoy", # Unique cache key
                fetch_func=lambda s=series_id: fetch_inflation_yoy(s),
                expiry_seconds=config.CACHE_EXPIRY_MACRO,
                source_name=f"FRED ({series_id}) YoY",
                errors_list=result["errors"]
            )
             result[key] = val
             continue

        val = get_cached_or_fetch(
            key=series_id,
            fetch_func=lambda s=series_id: fetch_fred_series(s),
            expiry_seconds=config.CACHE_EXPIRY_MACRO,
            source_name=f"FRED ({series_id})",
            errors_list=result["errors"]
        )
        result[key] = val


def _fetch_json_metrics(country_config: dict, result: dict):
    """Fetch metrics from local JSON file."""
    json_path = config.PROJECT_ROOT / "data" / country_config.get("json_path", "")
    mapping = country_config.get("json_keys", {})
    
    if json_path.exists():
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            
            # Map JSON keys to standard result keys
            for std_key, json_key in mapping.items():
                if json_key in data:
                    result[std_key] = data[json_key]
                    
            if "last_updated" in data:
                result["last_updated"] = data["last_updated"]
                
        except Exception as e:
            result["errors"].append(f"JSON load error: {str(e)}")
    else:
        result["errors"].append(f"JSON file not found: {json_path}")


def _fetch_live_market_data(country_config: dict, result: dict):
    """Fetch live market data (Yields, FX) from YFinance."""
    metrics_map = country_config.get("metrics", {})
    
    def fetch_ticker(ticker):
        t = yf.Ticker(ticker)
        hist = t.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None

    # Check for yield_10y
    if "yield_10y" in metrics_map:
        ticker = metrics_map["yield_10y"]
        # Only fetch if it looks like a ticker (not a FRED ID) or we want to force it
        # For SA, it's ZAR=X, for US it's ^TNX
        if ticker:
             val = get_cached_or_fetch(
                key=ticker,
                fetch_func=lambda t=ticker: fetch_ticker(t),
                expiry_seconds=config.CACHE_EXPIRY_MARKET,
                source_name=f"YFinance {ticker}",
                errors_list=result["errors"]
            )
             # Prefer live data over static JSON if available
             if val is not None:
                 result["yield_10y"] = val

    # Check for usd_zar or other FX
    if "usd_zar" in metrics_map:
        ticker = metrics_map["usd_zar"]
        val = get_cached_or_fetch(
            key=ticker,
            fetch_func=lambda t=ticker: fetch_ticker(t),
            expiry_seconds=config.CACHE_EXPIRY_MARKET,
            source_name=f"YFinance {ticker}",
            errors_list=result["errors"]
        )
        result["usd_zar"] = val


def get_yield_curve_data(country_code: str) -> Optional[Dict[str, float]]:
    """
    Fetch current yield curve data.
    
    Returns:
        Dict mapping maturity label (e.g. '10Y') to yield value (float).
    """
    if country_code not in config.COUNTRIES:
        return None
        
    curve_config = config.COUNTRIES[country_code].get("yield_curve", {})
    if not curve_config:
        return None
        
    result = {}
    
    def fetch_ticker(ticker):
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except:
            pass
        return None

    for label, ticker in curve_config.items():
        # Short expiry cache for yields
        val = get_cached_or_fetch(
            key=f"yield_{ticker}",
            fetch_func=lambda t=ticker: fetch_ticker(t),
            expiry_seconds=config.CACHE_EXPIRY_MARKET,
            source_name=f"Yield {label}",
            errors_list=[]
        )
        if val is not None:
            result[label] = val
            
    return result if result else None


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

def fetch_net_liquidity_components(years: int = 5) -> bool:
    """
    Fetch and cache the components for Net Liquidity.
    """
    fred = get_fred_client()
    if not fred: return False
    
    # Define time range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years*365)
    
    try:
        # 1. Fetch FRED Series (Global/US Liquidity)
        for key in ["fed_assets", "tga", "reverse_repo"]:
            series_id = config.GLOBAL_SERIES[key]
            # Fetch from FRED
            series = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
            
            if series is not None and not series.empty:
                # Convert to DataFrame
                df = series.to_frame(name="Value")
                df.index.name = "Date"
                
                # Use series ID as cache key (consistent with usage in SQL)
                db.set_chart(series_id, df)
            else:
                print(f"Warning: Empty data for {series_id}")
                return False

        # 2. Fetch S&P 500
        sp500_ticker = config.GLOBAL_SERIES["sp500"]
        sp500 = yf.Ticker(sp500_ticker)
        # Fetch history (YFinance accepts string for start/end)
        sp500_hist = sp500.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
        
        if not sp500_hist.empty:
            df_sp = sp500_hist[["Close"]]
            df_sp.index.name = "Date" # Ensure index name is set
            db.set_chart(sp500_ticker, df_sp)
        else:
             print(f"Warning: Empty data for {sp500_ticker}")
             return False
             
        return True
        
    except Exception as e:
        print(f"Error fetching net liquidity components: {e}")
        return False

def get_net_liquidity_data() -> Optional[pd.DataFrame]:
    """
    Calculate Net Liquidity and join with S&P 500 using DuckDB.
    
    Formula: Net Liquidity = WALCL - WTREGEN - RRPONTSYD
    
    Returns:
        DataFrame with index 'Date' and columns ['Net_Liquidity', 'SP500']
    """
    # 1. Ensure Cache is Populated
    test_key = config.GLOBAL_SERIES["fed_assets"]
    cached = db.get_chart(test_key)
    
    # If missing or old (>24h), fetch fresh
    if not cached or not is_fresh(cached['timestamp'], config.CACHE_EXPIRY_MACRO):
        print("Refreshing Net Liquidity Data...")
        success = fetch_net_liquidity_components()
        if not success and not cached:
            return None
            
    # 2. Execute DuckDB Query
    conn = db.get_duckdb_connection()
    
    # Construct paths to parquet files
    def get_path(ticker):
        safe_ticker = ticker.replace("^", "").replace("=", "").replace("/", "_")
        return str(config.DATA_DIR / "cache" / f"{safe_ticker}.parquet")
    
    path_walcl = get_path(config.GLOBAL_SERIES["fed_assets"])
    path_tga = get_path(config.GLOBAL_SERIES["tga"])
    path_rrp = get_path(config.GLOBAL_SERIES["reverse_repo"])
    path_sp500 = get_path(config.GLOBAL_SERIES["sp500"])
    
    query = f"""
        WITH 
        fed AS (SELECT CAST(Date AS DATE) as d, Value as val FROM read_parquet('{path_walcl}')),
        tga AS (SELECT CAST(Date AS DATE) as d, Value as val FROM read_parquet('{path_tga}')),
        rrp AS (SELECT CAST(Date AS DATE) as d, Value as val FROM read_parquet('{path_rrp}')),
        sp  AS (SELECT CAST(Date AS DATE) as d, Close as val FROM read_parquet('{path_sp500}')),
        
        aligned AS (
            SELECT 
                sp.d as Date,
                sp.val as SP500,
                (SELECT val FROM fed WHERE d <= sp.d ORDER BY d DESC LIMIT 1) as walcl,
                (SELECT val FROM tga WHERE d <= sp.d ORDER BY d DESC LIMIT 1) as tga_val,
                (SELECT val FROM rrp WHERE d <= sp.d ORDER BY d DESC LIMIT 1) as rrp_val
            FROM sp
        )
        SELECT
            Date,
            SP500,
            -- WALCL (M) / 1000 = B
            -- WTREGEN (M) / 1000 = B
            -- RRPONTSYD (B)
            ((walcl / 1000.0) - (tga_val / 1000.0) - rrp_val) as Net_Liquidity
        FROM aligned
        WHERE walcl IS NOT NULL AND tga_val IS NOT NULL AND rrp_val IS NOT NULL
        ORDER BY Date ASC
    """
    
    try:
        df_result = conn.execute(query).df()
        conn.close()
        
        if not df_result.empty:
            df_result.set_index('Date', inplace=True)
            return df_result
        return None
        
    except Exception as e:
        print(f"DuckDB Query Error: {e}")
        conn.close()
        return None
