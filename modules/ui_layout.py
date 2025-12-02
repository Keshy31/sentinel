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


def format_value(value, suffix: str = "", decimals: int = 2) -> str:
    """Format a numeric value for display, handling None."""
    if value is None:
        return "[dim]N/A[/dim]"
    if isinstance(value, float):
        return f"{value:,.{decimals}f}{suffix}"
    return str(value)


def format_ratio_with_status(ratio: float, suffix: str = "%") -> str:
    """Format ratio with color based on status."""
    if ratio is None:
        return "[dim]N/A[/dim]"
    
    status = logic.get_interest_ratio_status(ratio)
    ratio_pct = ratio * 100
    
    if status == "CRITICAL":
        return f"[bold red]{ratio_pct:.1f}{suffix}[/bold red] [red]CRITICAL[/red]"
    elif status == "WARNING":
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


def create_us_panel(data: dict) -> Panel:
    """Create the US metrics panel."""
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2), expand=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")
    
    # Core Metrics
    table.add_row("Total Public Debt", format_value(data.get("total_debt"), " B", 0))
    table.add_row("GDP", format_value(data.get("gdp"), " B", 0))
    table.add_row("Interest Payments", format_value(data.get("interest_payments"), " B", 1))
    table.add_row("Tax Receipts", format_value(data.get("tax_receipts"), " B", 1))
    table.add_row("10Y Treasury Yield", format_value(data.get("yield_10y"), "%", 2))
    
    # Real Yield & Growth Spread
    yield_10y = data.get("yield_10y")
    inflation = data.get("inflation_yoy")
    gdp_growth = data.get("gdp_growth")
    
    if yield_10y is not None and inflation is not None:
        real_yield = logic.calculate_real_yield(yield_10y, inflation)
        table.add_row("Real Yield (r-i)", format_value(real_yield, "%", 2))
    
    if yield_10y is not None and gdp_growth is not None:
        spread = logic.calculate_growth_spread(yield_10y, gdp_growth)
        status = logic.get_growth_spread_status(spread)
        color = "red" if status == "CRITICAL" else "green"
        table.add_row("Growth Spread (r-g)", f"[bold {color}]{spread:+.1f}%[/bold {color}]")

    # Ratios
    if data.get("interest_payments") and data.get("tax_receipts"):
        ratio = logic.calculate_interest_revenue_ratio(
            data["interest_payments"],
            data["tax_receipts"]
        )
        table.add_row("Interest/Revenue", format_ratio_with_status(ratio))
    
    if data.get("total_debt") and data.get("gdp"):
        debt_gdp = logic.calculate_debt_to_gdp_ratio(data["total_debt"], data["gdp"])
        
        # Color code Debt/GDP
        status = logic.get_debt_gdp_status(debt_gdp, is_emerging_market=False)
        color = "white"
        if status == "CRITICAL": color = "red"
        elif status == "WARNING": color = "yellow"
        
        table.add_row("Debt/GDP", f"[{color}]{debt_gdp:,.1f}%[/{color}]")
    
    # Vigilante Alert
    if yield_10y and logic.get_bond_vigilante_status(yield_10y):
        table.add_row("", "")
        table.add_row("[bold white on red]⚠️ VIGILANTE ATTACK[/bold white on red]", "")

    # Sparkline
    sparkline = render_chart.build_sparkline("^TNX", months=6, width=40, height=10)
    
    content = Group(
        table,
        Text(""),
        Text("10Y Yield Trend (6mo):", style="dim cyan"),
        Text.from_ansi(sparkline)
    )
    
    # Border color based on status
    border_style = "blue"
    if data.get("interest_payments") and data.get("tax_receipts"):
        ratio = logic.calculate_interest_revenue_ratio(data["interest_payments"], data["tax_receipts"])
        if logic.get_interest_ratio_status(ratio) == "CRITICAL":
            border_style = "red"
    if yield_10y and logic.get_bond_vigilante_status(yield_10y):
        border_style = "red"
    
    return Panel(
        content,
        title="[bold blue]🇺🇸 UNITED STATES (The Empire)[/bold blue]",
        border_style=border_style
    )


def create_sa_panel(data: dict) -> Panel:
    """Create the SA metrics panel."""
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2), expand=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")
    
    table.add_row("Total Debt", format_value(data.get("debt_zar_billions"), " B ZAR", 0))
    table.add_row("Annual Revenue", format_value(data.get("annual_revenue_zar_billions"), " B ZAR", 0))
    table.add_row("Interest Expense", format_value(data.get("annual_interest_expense_zar_billions"), " B ZAR", 0))
    table.add_row("GDP Growth Forecast", format_value(data.get("gdp_growth_forecast_pct"), "%", 1))
    table.add_row("10Y Yield (Static)", format_value(data.get("bond_yield_10y_static"), "%", 1))
    table.add_row("USD/ZAR (Live)", format_value(data.get("usd_zar"), "", 2))
    
    # Debt/GDP (Estimated or Actual)
    rev = data.get("annual_revenue_zar_billions")
    debt = data.get("debt_zar_billions")
    gdp = data.get("gdp_zar_billions")
    
    if debt:
        if gdp:
            debt_gdp = logic.calculate_debt_to_gdp_ratio(debt, gdp)
            label = "Debt/GDP"
        elif rev:
            est_gdp = rev * 4.0 # Estimate GDP as ~4x Revenue
            debt_gdp = logic.calculate_debt_to_gdp_ratio(debt, est_gdp)
            label = "Debt/GDP (Est)"
        else:
            debt_gdp = None
            
        if debt_gdp is not None:
            # Color code
            status = logic.get_debt_gdp_status(debt_gdp, is_emerging_market=True)
            color = "white"
            if status == "CRITICAL": color = "red"
            elif status == "WARNING": color = "yellow"
            
            table.add_row(label, f"[{color}]{debt_gdp:.1f}%[/{color}]")

    # Ratios
    interest = data.get("annual_interest_expense_zar_billions")
    revenue = data.get("annual_revenue_zar_billions")
    if interest and revenue:
        ratio = logic.calculate_interest_revenue_ratio(interest, revenue)
        table.add_row("Interest/Revenue", format_ratio_with_status(ratio))
    
    # Growth Spread
    bond_yield = data.get("bond_yield_10y_static")
    gdp_growth = data.get("gdp_growth_forecast_pct")
    if bond_yield and gdp_growth:
        spread = logic.calculate_growth_spread(bond_yield, gdp_growth)
        status = logic.get_growth_spread_status(spread)
        color = "red" if status == "CRITICAL" else "green"
        table.add_row("Growth Spread (r-g)", f"[bold {color}]{spread:+.1f}%[/bold {color}]")
    
    # Currency Risk Alert
    usd_zar = data.get("usd_zar")
    if usd_zar and logic.get_currency_risk_status(usd_zar):
        table.add_row("", "")
        table.add_row("[bold white on red]⚠️ CURRENCY CRISIS[/bold white on red]", "")

    # Sparkline
    sparkline = render_chart.build_sparkline("ZAR=X", months=6, width=40, height=10)
    
    content = Group(
        table,
        Text(""),
        Text("USD/ZAR Trend (6mo):", style="dim cyan"),
        Text.from_ansi(sparkline)
    )
    
    # Border color based on status
    border_style = "green"
    if interest and revenue:
        ratio = logic.calculate_interest_revenue_ratio(interest, revenue)
        if logic.get_interest_ratio_status(ratio) == "CRITICAL":
            border_style = "red"
    if usd_zar and logic.get_currency_risk_status(usd_zar):
        border_style = "red"

    return Panel(
        content,
        title="[bold green]🇿🇦 SOUTH AFRICA (Emerging Mkt)[/bold green]",
        subtitle=f"[dim]Data: {data.get('last_updated', 'Unknown')}[/dim]",
        border_style=border_style
    )


def create_charts_panel() -> Panel:
    """Create the historical charts panel."""
    # US Growth Spread Chart (US_GROWTH_SPREAD)
    chart = render_chart.build_full_chart("US_GROWTH_SPREAD", months=6, width=80, height=12)
    
    content = Group(
        Text("US Growth Spread (Yield vs GDP) - 6 Month Trend", style="bold cyan"),
        Text.from_ansi(chart)
    )
    
    return Panel(
        content,
        title="[bold yellow]MACRO TRENDS[/bold yellow]",
        border_style="yellow"
    )


def create_footer(us_data: dict, sa_data: dict) -> Panel:
    """Create the status bar/footer with global alert."""
    is_critical = False
    
    # Check US Criticals
    if us_data.get("interest_payments") and us_data.get("tax_receipts"):
        ratio = logic.calculate_interest_revenue_ratio(us_data["interest_payments"], us_data["tax_receipts"])
        if logic.get_interest_ratio_status(ratio) == "CRITICAL": is_critical = True
        
    if us_data.get("yield_10y") and logic.get_bond_vigilante_status(us_data["yield_10y"]): 
        is_critical = True

    if us_data.get("total_debt") and us_data.get("gdp"):
        debt_gdp = logic.calculate_debt_to_gdp_ratio(us_data["total_debt"], us_data["gdp"])
        if logic.get_debt_gdp_status(debt_gdp, False) == "CRITICAL": is_critical = True
        
    # Check SA Criticals
    if sa_data.get("usd_zar") and logic.get_currency_risk_status(sa_data["usd_zar"]): 
        is_critical = True
        
    sa_int = sa_data.get("annual_interest_expense_zar_billions")
    sa_rev = sa_data.get("annual_revenue_zar_billions")
    if sa_int and sa_rev:
        ratio = logic.calculate_interest_revenue_ratio(sa_int, sa_rev)
        if logic.get_interest_ratio_status(ratio) == "CRITICAL": is_critical = True

    if is_critical:
        content = "[bold white on red] ALERT: FISCAL DOMINANCE DETECTED - SYSTEM INSTABILITY [/bold white on red]"
    else:
        content = "[dim]Checking for Fiscal Dominance...[/dim] [bold green]SYSTEM STABLE[/bold green]"
    
    return Panel(Align.center(content), box=box.MINIMAL, style="dim white")


def build_dashboard_layout(us_data: dict, sa_data: dict, blink_state: bool = True) -> Layout:
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
    
    # Split main into live metrics (top) and historical charts (bottom)
    layout["main"].split_column(
        Layout(name="live_metrics", ratio=1),
        Layout(name="historical_charts", ratio=1)
    )
    
    layout["live_metrics"].split_row(
        Layout(name="us_panel", ratio=1),
        Layout(name="sa_panel", ratio=1)
    )
    
    layout["us_panel"].update(create_us_panel(us_data))
    layout["sa_panel"].update(create_sa_panel(sa_data))
    
    layout["historical_charts"].update(create_charts_panel())
    
    layout["footer"].update(create_footer(us_data, sa_data))
    
    return layout
