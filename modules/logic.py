"""
Project Sentinel - Logic Engine

Pure functions for financial calculations:
- Doom Loop Ratio (Interest Burden)
- Growth Spread (r - g)
- Threshold checks and alert status
"""

from typing import Literal

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


def get_interest_ratio_status(
    ratio: float,
    warning_threshold: float = 0.18,
    critical_threshold: float = 0.20
) -> AlertStatus:
    """
    Determine alert status based on interest/revenue ratio.
    
    Args:
        ratio: Interest/Revenue ratio as decimal
        warning_threshold: Threshold for WARNING status (default 18%)
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

