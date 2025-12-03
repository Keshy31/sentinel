"""
Project Sentinel - UI Layout Engine

Uses Rich library to create the dashboard layout with panels, tables, and live updates.
"""

from datetime import datetime
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.console import Group
from rich.align import Align

from modules import logic, render_chart
import config


def format_value(value, suffix: str = "", decimals: int = 2) -> str:
    """Format a numeric value for display, handling None."""
    if value is None:
        return "[dim]N/A[/dim]"
    if isinstance(value, float):
        return f"{value:,.{decimals}f}{suffix}"
    return str(value)


def format_ratio_with_status(ratio: float, warn: float, crit: float, suffix: str = "%") -> str:
    """Format ratio with color based on status."""
    if ratio is None:
        return "[dim]N/A[/dim]"
    
    ratio_pct = ratio * 100
    
    if ratio >= crit:
        return f"[bold red]{ratio_pct:.1f}{suffix}[/bold red] [red]CRITICAL[/red]"
    elif ratio >= warn:
        return f"[bold yellow]{ratio_pct:.1f}{suffix}[/bold yellow] [yellow]WARNING[/yellow]"
    return f"[bold green]{ratio_pct:.1f}{suffix}[/bold green] [green]SAFE[/green]"


def create_header(blink_state: bool = True) -> Panel:
    """Create the dashboard header."""
    dot = "●" if blink_state else "○"
    dot_color = "red" if blink_state else "dim white"
    
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="right")
    
    title = f"[{dot_color}]{dot}[/{dot_color}] [bold white]PROJECT SENTINEL[/bold white] [dim]- LIVE MONITOR[/dim]"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    grid.add_row(title, f"[dim]{timestamp}[/dim]")
    
    return Panel(grid, style="white", box=box.HEAVY)


def create_indicators_panel(country_code: str, data: dict) -> Panel:
    """Create the standard indicators panel for a country."""
    country_conf = config.COUNTRIES.get(country_code, {})
    thresholds = country_conf.get("thresholds", {})
    currency = country_conf.get("currency_symbol", "")
    flag = country_conf.get("flag", "")
    name = country_conf.get("name", country_code)
    
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2), expand=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")
    
    # 1. Core Fiscal Metrics
    table.add_row("[bold]FISCAL[/bold]", "")
    table.add_row("Total Public Debt", format_value(data.get("total_debt"), f" B {currency}", 0))
    table.add_row("Interest Payments", format_value(data.get("interest_payments"), f" B {currency}", 1))
    table.add_row("Tax Receipts", format_value(data.get("tax_receipts"), f" B {currency}", 1))
    table.add_row("GDP", format_value(data.get("gdp"), f" B {currency}", 0))
    
    # Interest/Revenue Ratio
    if data.get("interest_payments") and data.get("tax_receipts"):
        ratio = logic.calculate_interest_revenue_ratio(
            data["interest_payments"],
            data["tax_receipts"]
        )
        warn = thresholds.get("interest_rev_warning", 0.15)
        crit = thresholds.get("interest_rev_critical", 0.20)
        table.add_row("Interest/Revenue", format_ratio_with_status(ratio, warn, crit))
    else:
        table.add_row("Interest/Revenue", "[dim]N/A[/dim]")

    # Debt/GDP Ratio
    debt_gdp = None
    if data.get("total_debt") and data.get("gdp"):
        debt_gdp = logic.calculate_debt_to_gdp_ratio(data["total_debt"], data["gdp"])
        warn = thresholds.get("debt_gdp_warning", 100.0)
        crit = thresholds.get("debt_gdp_critical", 120.0)
        
        # Color code
        color = "green"
        if debt_gdp >= crit: color = "red"
        elif debt_gdp >= warn: color = "yellow"
        
        table.add_row("Debt/GDP", f"[{color}]{debt_gdp:,.1f}%[/{color}]")
    else:
        table.add_row("Debt/GDP", "[dim]N/A[/dim]")

    table.add_row("", "")
    table.add_row("[bold]MONETARY & ECONOMIC[/bold]", "")

    # Yields & Inflation
    yield_10y = data.get("yield_10y")
    table.add_row("10Y Bond Yield", format_value(yield_10y, "%", 2))
    
    inflation = data.get("inflation_yoy")
    table.add_row("Inflation (YoY)", format_value(inflation, "%", 2))
    
    # Real Yield (r - i)
    if yield_10y is not None and inflation is not None:
        real_yield = logic.calculate_real_yield(yield_10y, inflation)
        color = "green" if real_yield > 0 else "red"
        table.add_row("Real Yield (r - i)", f"[{color}]{real_yield:+.2f}%[/{color}]")
    else:
         table.add_row("Real Yield (r - i)", "[dim]N/A[/dim]")
         
    # Growth Spread (r - g)
    gdp_growth = data.get("gdp_growth")
    if yield_10y is not None and gdp_growth is not None:
        spread = logic.calculate_growth_spread(yield_10y, gdp_growth)
        status = logic.get_growth_spread_status(spread)
        color = "red" if status == "CRITICAL" else "green"
        table.add_row("Growth Spread (r - g)", f"[bold {color}]{spread:+.2f}%[/bold {color}]")
    else:
        table.add_row("Growth Spread (r - g)", "[dim]N/A[/dim]")
        
    # Currency (if applicable)
    if "usd_zar" in data and data["usd_zar"]:
         table.add_row("USD/ZAR", format_value(data["usd_zar"], "", 2))


    # Alerts Section
    alerts = []
    
    # Vigilante Alert
    vigilante_thresh = thresholds.get("yield_10y_vigilante")
    if vigilante_thresh and yield_10y and yield_10y > vigilante_thresh:
        alerts.append("[bold white on red]⚠️ BOND VIGILANTE ATTACK[/bold white on red]")
        
    # Currency Crisis
    currency_thresh = thresholds.get("currency_risk_critical")
    if currency_thresh and data.get("usd_zar") and data["usd_zar"] > currency_thresh:
        alerts.append("[bold white on red]⚠️ CURRENCY CRISIS[/bold white on red]")
        
    # Interest Crisis
    if data.get("interest_payments") and data.get("tax_receipts"):
        ratio = logic.calculate_interest_revenue_ratio(data["interest_payments"], data["tax_receipts"])
        crit = thresholds.get("interest_rev_critical", 0.20)
        if ratio >= crit:
             alerts.append("[bold white on red]⚠️ DEBT SPIRAL DETECTED[/bold white on red]")

    if alerts:
        table.add_row("", "")
        for alert in alerts:
            table.add_row(alert, "")

    # Sparkline (10Y Yield History)
    sparkline_ticker = country_conf.get("metrics", {}).get("yield_10y")
    if sparkline_ticker:
        sparkline = render_chart.build_sparkline(sparkline_ticker, months=6, width=60, height=5)
        content = Group(
            table,
            Text(""),
            Text("10Y Yield Trend (6mo):", style="dim cyan"),
            Text.from_ansi(sparkline)
        )
    else:
        content = table

    # Border Color Logic
    border_style = "blue"
    if alerts:
        border_style = "red"

    return Panel(
        content,
        title=f"[bold]{flag} {name.upper()}[/bold]",
        subtitle=f"[dim]Data: {data.get('last_updated', 'Unknown')}[/dim]",
        border_style=border_style
    )


def create_charts_panel(country_code: str) -> Group:
    """Create the historical charts panel (Split Left/Right)."""
    
    # Left: Yield Curve
    yield_curve_chart = render_chart.build_yield_curve_chart(country_code, width=75, height=15)
    
    # Right: Net Liquidity (Global Context)
    liquidity_chart = render_chart.build_liquidity_chart(width=75, height=15)
    
    # We use a Layout object to split them? 
    # Actually, Rich Panels can contain Layouts? No, Layouts contain Panels.
    # But this function returns a Panel or Group to be put into a Layout slot.
    # If I return a Group, they stack vertically.
    # To split horizontally within this panel, I need to use Columns or Table.
    
    grid = Table.grid(expand=True)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    
    grid.add_row(
        Panel(Text.from_ansi(yield_curve_chart), title="Yield Curve Structure", border_style="green"),
        Panel(Text.from_ansi(liquidity_chart), title="Global Liquidity Context", border_style="yellow")
    )
    
    return grid


def create_footer(data: dict, country_code: str) -> Panel:
    """Create the status bar/footer with global alert."""
    country_conf = config.COUNTRIES.get(country_code, {})
    thresholds = country_conf.get("thresholds", {})
    
    is_critical = False
    
    # Interest/Revenue Check
    if data.get("interest_payments") and data.get("tax_receipts"):
        ratio = logic.calculate_interest_revenue_ratio(data["interest_payments"], data["tax_receipts"])
        crit = thresholds.get("interest_rev_critical", 0.20)
        if ratio >= crit: is_critical = True
        
    # Debt/GDP Check
    if data.get("total_debt") and data.get("gdp"):
        debt_gdp = logic.calculate_debt_to_gdp_ratio(data["total_debt"], data["gdp"])
        crit = thresholds.get("debt_gdp_critical", 120.0)
        if debt_gdp >= crit: is_critical = True

    if is_critical:
        content = "[bold white on red] ALERT: FISCAL DOMINANCE DETECTED - SYSTEM INSTABILITY [/bold white on red]"
    else:
        content = f"[dim]Monitoring {country_conf.get('name')}...[/dim] [bold green]SYSTEM STABLE[/bold green]"
    
    return Panel(Align.center(content), box=box.MINIMAL, style="dim white")


def build_dashboard_layout(country_code: str, data: dict, blink_state: bool = True) -> Layout:
    """
    Build the main dashboard layout.
    """
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3)
    )
    
    layout["header"].update(create_header(blink_state))
    
    # Vertical Split: Top (Indicators), Bottom (Charts)
    layout["main"].split_column(
        Layout(name="indicators", size=24), 
        Layout(name="charts", ratio=1)
    )
    
    # Update Indicators
    layout["indicators"].update(create_indicators_panel(country_code, data))
    
    # Update Charts
    layout["charts"].update(create_charts_panel(country_code))
    
    layout["footer"].update(create_footer(data, country_code))
    
    return layout
