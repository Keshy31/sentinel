"""
Project Sentinel - Chart Rendering Engine

Uses plotext to generate ASCII charts for terminal display.
Supports two modes:
- Sparklines: Compact charts for dashboard panels
- Full Charts: Detailed charts with axes, labels, and grid
"""

from typing import Optional
import plotext as plt

from modules import data_loader


# Ticker to human-readable name mapping
TICKER_LABELS = {
    "^TNX": "US 10Y Treasury Yield",
    "ZAR=X": "USD/ZAR Exchange Rate",
}


def _clean_chart_output(chart_str: str) -> str:
    """
    Clean up plotext output for better display in Rich panels.
    
    Removes trailing whitespace, extra blank lines, and normalizes line lengths.
    """
    # Split into lines, strip trailing whitespace from each
    lines = [line.rstrip() for line in chart_str.split('\n')]
    
    # Remove trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()
    
    # Remove leading empty lines  
    while lines and not lines[0].strip():
        lines.pop(0)
    
    # Filter out any lines that are just whitespace
    lines = [line for line in lines if line.strip() or line == '']
    
    return '\n'.join(lines)


def get_chart_title(ticker: str) -> str:
    """
    Get human-readable title for a ticker symbol.
    
    Args:
        ticker: YFinance ticker symbol
    
    Returns:
        Human-readable name or the ticker itself if not found
    """
    return TICKER_LABELS.get(ticker, ticker)


def build_sparkline(
    ticker: str,
    months: int = 6,
    width: int = 40,
    height: int = 5
) -> str:
    """
    Build a compact ASCII sparkline chart for dashboard panels.
    
    Args:
        ticker: YFinance ticker symbol (e.g., "^TNX", "ZAR=X")
        months: Number of months of history to display
        width: Chart width in characters
        height: Chart height in lines
    
    Returns:
        ASCII chart as a string, or error message if data unavailable
    """
    # Fetch historical data
    period = f"{months}mo"
    df = data_loader.get_historical_data(ticker, period)
    
    if df is None or df.empty:
        return f"[No data for {ticker}]"
    
    try:
        # Clear any previous plot
        plt.clf()
        
        # Configure for sparkline (minimal chrome)
        plt.plotsize(width, height)
        plt.theme("dark")
        
        # Extract data
        dates = list(range(len(df)))  # Use numeric x-axis for compactness
        values = df["Close"].tolist()
        
        # Plot the line
        plt.plot(dates, values, marker="braille")
        
        # Minimal axes - no labels for sparkline
        plt.xaxes(False, False)
        plt.yaxes(False, False)
        plt.frame(False)
        
        # Build and return as string
        chart_str = plt.build()
        plt.clf()
        
        return _clean_chart_output(chart_str)
        
    except Exception as e:
        return f"[Chart error: {str(e)}]"


def build_full_chart(
    ticker: str,
    months: int = 6,
    width: int = 60,
    height: int = 12
) -> str:
    """
    Build a detailed ASCII chart with axes, labels, and grid.
    
    Args:
        ticker: YFinance ticker symbol (e.g., "^TNX", "ZAR=X")
        months: Number of months of history to display
        width: Chart width in characters
        height: Chart height in lines
    
    Returns:
        ASCII chart as a string, or error message if data unavailable
    """
    # Fetch historical data
    period = f"{months}mo"
    df = data_loader.get_historical_data(ticker, period)
    
    if df is None or df.empty:
        return f"[No data available for {ticker}]"
    
    try:
        # Clear any previous plot
        plt.clf()
        
        # Configure plot size and theme
        plt.plotsize(width, height)
        plt.theme("dark")
        
        # Extract data
        dates = df.index.tolist()
        values = df["Close"].tolist()
        
        # Create date labels (show first, middle, last)
        date_labels = []
        date_positions = []
        if len(dates) > 0:
            date_positions.append(0)
            date_labels.append(dates[0].strftime("%b %d"))
            
            mid = len(dates) // 2
            date_positions.append(mid)
            date_labels.append(dates[mid].strftime("%b %d"))
            
            date_positions.append(len(dates) - 1)
            date_labels.append(dates[-1].strftime("%b %d"))
        
        # Plot with numeric x values (no legend to keep it clean)
        x_vals = list(range(len(values)))
        plt.plot(x_vals, values, marker="braille")
        
        # Add title
        plt.title(f"{get_chart_title(ticker)} - {months}mo")
        
        # Configure axes
        plt.xticks(date_positions, date_labels)
        
        # Calculate stats
        current_val = values[-1]
        min_val = min(values)
        max_val = max(values)
        change = values[-1] - values[0]
        pct_change = (change / values[0]) * 100 if values[0] != 0 else 0
        
        # Build chart string
        chart_str = plt.build()
        plt.clf()
        
        # Clean up and add summary
        chart_clean = _clean_chart_output(chart_str)
        
        summary = (
            f"Now: {current_val:.2f}  "
            f"Low: {min_val:.2f}  "
            f"High: {max_val:.2f}  "
            f"Chg: {change:+.2f} ({pct_change:+.1f}%)"
        )
        
        return chart_clean + "\n" + summary
        
    except Exception as e:
        return f"[Chart error: {str(e)}]"


def build_comparison_chart(
    tickers: list,
    months: int = 6,
    width: int = 60,
    height: int = 12
) -> str:
    """
    Build a chart comparing multiple tickers (normalized to percentage change).
    
    Args:
        tickers: List of YFinance ticker symbols
        months: Number of months of history
        width: Chart width in characters
        height: Chart height in lines
    
    Returns:
        ASCII chart as a string
    """
    try:
        plt.clf()
        plt.plotsize(width, height)
        plt.theme("dark")
        
        period = f"{months}mo"
        
        for ticker in tickers:
            df = data_loader.get_historical_data(ticker, period)
            if df is not None and not df.empty:
                values = df["Close"].tolist()
                # Normalize to percentage change from start
                base = values[0]
                normalized = [(v / base - 1) * 100 for v in values]
                x_vals = list(range(len(normalized)))
                plt.plot(x_vals, normalized, marker="braille", label=get_chart_title(ticker))
        
        plt.title(f"Relative Performance - {months}mo")
        plt.ylabel("% Change")
        
        chart_str = plt.build()
        plt.clf()
        
        return _clean_chart_output(chart_str)
        
    except Exception as e:
        return f"[Comparison chart error: {str(e)}]"
