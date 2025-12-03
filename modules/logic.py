"""
Project Sentinel - Logic Engine

Pure functions for financial calculations:
- Doom Loop Ratio (Interest Burden)
- Growth Spread (r - g)
- Real Yield (r - inflation)
- Threshold checks and alert status

Advanced Analytics:
- Market Real Yield (using Breakevens)
- Term Premium Analysis
- Doom Loop Regression Forecasting
"""

from typing import Literal, Optional, Tuple
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

from modules import data_loader

AlertStatus = Literal["SAFE", "WARNING", "CRITICAL"]


def calculate_interest_revenue_ratio(
    interest_expense: float,
    tax_revenue: float
) -> float:
    """
    Calculate the Doom Loop Ratio (Interest Burden).
    
    Formula: Ratio = Annual Interest Expense / Annual Tax Revenue
    
    Args:
        interest_expense: Annual interest expense in billions
        tax_revenue: Annual tax revenue in billions
    
    Returns:
        Ratio as a decimal (e.g., 0.18 for 18%)
    """
    if tax_revenue == 0:
        return float('inf')
    return interest_expense / tax_revenue


def calculate_days_of_interest(
    total_debt: float,
    avg_interest_rate: float
) -> float:
    """
    Calculate Daily Interest Cost (Days of Interest).
    
    Formula: Daily Cost = (Total Debt * (Average Interest Rate / 100)) / 365
    
    Args:
        total_debt: Total Public Debt (Billions)
        avg_interest_rate: Average Interest Rate on Debt (%) (Approximate with 10Y Yield or blended rate)
    
    Returns:
        Daily Interest Cost in Billions.
    """
    if total_debt is None or avg_interest_rate is None:
        return 0.0
    return (total_debt * (avg_interest_rate / 100.0)) / 365.0


def calculate_growth_spread(
    bond_yield: float,
    gdp_growth: float
) -> float:
    """
    Calculate the Growth Spread (r - g).
    
    Formula: Spread = 10Y Bond Yield (r) - GDP Growth Rate (g)
    
    Args:
        bond_yield: 10-Year bond yield as percentage (e.g., 4.5 for 4.5%)
        gdp_growth: GDP growth rate as percentage (e.g., 2.5 for 2.5%)
    
    Returns:
        Spread as percentage points. Negative = Safe, Positive = Danger
    """
    return bond_yield - gdp_growth


def calculate_real_yield(
    nominal_yield: float,
    inflation_rate: float
) -> float:
    """
    Calculate Real Yield (r_real).
    
    Formula: Real Yield = Nominal Yield - Inflation Rate
    
    Args:
        nominal_yield: Nominal bond yield (%)
        inflation_rate: Inflation rate (%, e.g. YoY CPI)
        
    Returns:
        Real yield as percentage.
    """
    return nominal_yield - inflation_rate


def calculate_yield_spread(
    long_yield: float,
    short_yield: float
) -> float:
    """
    Calculate Yield Curve Spread (e.g., 10Y - 3M).
    
    Args:
        long_yield: Long-term bond yield (e.g., 10Y)
        short_yield: Short-term bond yield (e.g., 3M)
        
    Returns:
        Spread in percentage points.
    """
    return long_yield - short_yield


def calculate_debt_to_gdp_ratio(
    total_debt: float,
    gdp: float
) -> float:
    """
    Calculate Debt-to-GDP ratio.
    
    Args:
        total_debt: Total public debt in billions
        gdp: Gross Domestic Product in billions
    
    Returns:
        Ratio as percentage (e.g., 123.5 for 123.5%)
    """
    if gdp == 0:
        return float('inf')
    return (total_debt / gdp) * 100


# =============================================================================
# Status Checkers
# =============================================================================

def get_interest_ratio_status(
    ratio: float,
    warning_threshold: float = 0.15,
    critical_threshold: float = 0.20
) -> AlertStatus:
    """
    Determine alert status based on interest/revenue ratio.
    
    Args:
        ratio: Interest/Revenue ratio as decimal
        warning_threshold: Threshold for WARNING status (default 15%)
        critical_threshold: Threshold for CRITICAL status (default 20%)
    
    Returns:
        AlertStatus: "SAFE", "WARNING", or "CRITICAL"
    """
    if ratio >= critical_threshold:
        return "CRITICAL"
    elif ratio >= warning_threshold:
        return "WARNING"
    return "SAFE"


def get_growth_spread_status(spread: float) -> AlertStatus:
    """
    Determine alert status based on growth spread (r - g).
    
    Args:
        spread: Growth spread in percentage points
    
    Returns:
        AlertStatus: "SAFE" if negative (growth > yield), "CRITICAL" if positive
    """
    if spread > 0:
        return "CRITICAL"
    return "SAFE"


def get_yield_curve_status(spread: float) -> AlertStatus:
    """
    Determine alert status based on Yield Curve Spread (10Y - 3M).
    
    Args:
        spread: Yield spread in percentage points
        
    Returns:
        AlertStatus: "CRITICAL" if negative (Inverted), "SAFE" if positive
    """
    if spread < 0:
        return "CRITICAL"
    return "SAFE"


def get_bond_vigilante_status(bond_yield: float, threshold: float = 5.0) -> bool:
    """Check for Bond Vigilante Attack (Yield Spike)."""
    return bond_yield > threshold


def get_currency_risk_status(usd_zar: float, threshold: float = 19.0) -> bool:
    """Check for Currency Crisis."""
    return usd_zar > threshold


def get_debt_gdp_status(
    ratio: float,
    is_emerging_market: bool = False
) -> AlertStatus:
    """
    Determine alert status based on Debt/GDP ratio.
    
    Thresholds:
    - Developed (US): Warning > 100%, Critical > 120%
    - Emerging (SA): Warning > 70%, Critical > 90%
    """
    if is_emerging_market:
        warn, crit = 70.0, 90.0
    else:
        warn, crit = 100.0, 120.0
        
    if ratio >= crit:
        return "CRITICAL"
    elif ratio >= warn:
        return "WARNING"
    return "SAFE"


# =============================================================================
# Advanced Analytics (Phase 4)
# =============================================================================

def calculate_market_real_yield(
    nominal_10y: float,
    breakeven_5y: float
) -> float:
    """
    Calculate Market Real Yield.
    
    Formula: 10Y Nominal Yield - 5Y Breakeven Inflation
    This represents the real return investors demand.
    """
    return nominal_10y - breakeven_5y


def calculate_fed_rate_expectation(
    nominal_10y: float,
    term_premium_10y: float
) -> float:
    """
    Decompose 10Y Yield to find implied Fed Rate path.
    
    Formula: Fed Expectation = 10Y Nominal - Term Premium
    """
    return nominal_10y - term_premium_10y


def predict_doom_loop_day_zero() -> Tuple[Optional[float], Optional[str]]:
    """
    Predict when Interest will consume 100% of Tax Revenue (Ratio = 1.0).
    
    Returns:
        Tuple[years_remaining, estimated_date_str]
        years_remaining: Float years until Day Zero (e.g., 12.4)
        estimated_date_str: Formatted date string (e.g., "2038-05-12")
    """
    # 1. Get Data
    df = data_loader.get_fiscal_history_data()
    
    # If missing, try to fetch
    if df is None:
        print("Fetching Fiscal History for Regression...")
        success = data_loader.fetch_fiscal_history()
        if success:
            df = data_loader.get_fiscal_history_data()
            
    if df is None or df.empty:
        return None, "Insufficient Data"
        
    # 2. Prepare for Regression
    # We want to regress Ratio vs Time
    # X = Time (ordinal), y = Ratio
    
    # Use last 10 years or all available
    df = df.dropna()
    if len(df) < 10:
        return None, "Insufficient Data Points"
        
    # Create ordinal date
    # Fix: Wrap toordinal in lambda to avoid TypeError
    df['date_ordinal'] = df.index.map(lambda x: x.toordinal())
    
    X = df['date_ordinal'].values.reshape(-1, 1)
    y = df['ratio'].values
    
    # 3. Fit Model
    model = LinearRegression()
    model.fit(X, y)
    
    slope = model.coef_[0]
    intercept = model.intercept_
    
    # 4. Solve for y = 1.0
    # 1.0 = slope * x + intercept
    # x = (1.0 - intercept) / slope
    
    if slope <= 0:
        return None, "Trend is Improving (Slope <= 0)"
        
    day_zero_ordinal = (1.0 - intercept) / slope
    
    try:
        day_zero_date = datetime.fromordinal(int(day_zero_ordinal))
        now = datetime.now()
        
        days_remaining = (day_zero_date - now).days
        years_remaining = days_remaining / 365.25
        
        if years_remaining < 0:
             return 0.0, "Already Passed!"
             
        return years_remaining, day_zero_date.strftime("%Y-%m-%d")
        
    except Exception as e:
        return None, f"Calculation Error: {e}"
