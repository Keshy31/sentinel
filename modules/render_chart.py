"""
Project Sentinel - Chart Rendering Engine

Uses plotext to generate ASCII charts for terminal display.
"""

# Stub - To be implemented in Phase 2


def build_sparkline(ticker_symbol: str, months: int = 6) -> str:
    """
    Build an ASCII sparkline chart for a given ticker.
    
    Args:
        ticker_symbol: YFinance ticker symbol (e.g., "^TNX", "ZAR=X")
        months: Number of months of history to display
    
    Returns:
        ASCII chart as a string for embedding in Rich panels
    """
    # TODO: Implement in Phase 2
    # 1. Fetch historical data via yfinance
    # 2. Pass to plotext
    # 3. Use plt.build() to get string output
    # 4. Use plt.clf() to clear buffer
    return "[Chart placeholder - Phase 2]"

