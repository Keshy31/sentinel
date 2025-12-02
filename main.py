#!/usr/bin/env python3
"""
Project Sentinel - Sovereign Debt & Fiscal Dominance Monitor

Entry point for the dashboard application.
Phase 1: Test harness to verify data fetching works.
Phase 2: Chart engine integration.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box

from modules import data_loader, logic, render_chart
import config


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


def display_us_data(console: Console, data: dict, show_sparkline: bool = True) -> None:
    """Display US economic data in a formatted panel."""
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Total Public Debt", format_value(data.get("total_debt"), " B", 0))
    table.add_row("GDP", format_value(data.get("gdp"), " B", 0))
    table.add_row("Interest Payments", format_value(data.get("interest_payments"), " B", 1))
    table.add_row("Tax Receipts", format_value(data.get("tax_receipts"), " B", 1))
    table.add_row("10Y Treasury Yield", format_value(data.get("yield_10y"), "%", 2))
    
    # Calculate and display ratios if we have the data
    if data.get("interest_payments") and data.get("tax_receipts"):
        ratio = logic.calculate_interest_revenue_ratio(
            data["interest_payments"],
            data["tax_receipts"]
        )
        table.add_row("Interest/Revenue Ratio", format_ratio_with_status(ratio))
    
    if data.get("total_debt") and data.get("gdp"):
        debt_gdp = logic.calculate_debt_to_gdp_ratio(data["total_debt"], data["gdp"])
        table.add_row("Debt/GDP Ratio", format_value(debt_gdp, "%", 1))
    
    # Build content with optional sparkline
    if show_sparkline:
        sparkline = render_chart.build_sparkline("^TNX", months=6, width=36, height=4)
        from rich.console import Group
        content = Group(
            table,
            Text(""),
            Text("10Y Yield Trend (6mo):", style="dim cyan"),
            Text.from_ansi(sparkline)
        )
    else:
        content = table
    
    panel = Panel.fit(
        content,
        title="[bold blue]🇺🇸 UNITED STATES[/bold blue]",
        border_style="blue"
    )
    console.print(panel)
    
    # Show any errors
    if data.get("errors"):
        console.print("[dim red]Errors:[/dim red]")
        for error in data["errors"]:
            console.print(f"  [red]• {error}[/red]")


def display_sa_data(console: Console, data: dict, show_sparkline: bool = True) -> None:
    """Display South African economic data in a formatted panel."""
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Total Debt", format_value(data.get("debt_zar_billions"), " B ZAR", 0))
    table.add_row("Annual Revenue", format_value(data.get("annual_revenue_zar_billions"), " B ZAR", 0))
    table.add_row("Interest Expense", format_value(data.get("annual_interest_expense_zar_billions"), " B ZAR", 0))
    table.add_row("GDP Growth Forecast", format_value(data.get("gdp_growth_forecast_pct"), "%", 1))
    table.add_row("10Y Bond Yield (Static)", format_value(data.get("bond_yield_10y_static"), "%", 1))
    table.add_row("USD/ZAR (Live)", format_value(data.get("usd_zar"), "", 2))
    
    # Calculate and display interest/revenue ratio
    interest = data.get("annual_interest_expense_zar_billions")
    revenue = data.get("annual_revenue_zar_billions")
    if interest and revenue:
        ratio = logic.calculate_interest_revenue_ratio(interest, revenue)
        table.add_row("Interest/Revenue Ratio", format_ratio_with_status(ratio))
    
    # Calculate growth spread
    bond_yield = data.get("bond_yield_10y_static")
    gdp_growth = data.get("gdp_growth_forecast_pct")
    if bond_yield and gdp_growth:
        spread = logic.calculate_growth_spread(bond_yield, gdp_growth)
        status = logic.get_growth_spread_status(spread)
        color = "red" if status == "CRITICAL" else "green"
        table.add_row("Growth Spread (r - g)", f"[bold {color}]{spread:+.1f}%[/bold {color}]")
    
    # Build content with optional sparkline
    if show_sparkline:
        sparkline = render_chart.build_sparkline("ZAR=X", months=6, width=36, height=4)
        from rich.console import Group
        content = Group(
            table,
            Text(""),
            Text("USD/ZAR Trend (6mo):", style="dim cyan"),
            Text.from_ansi(sparkline)
        )
    else:
        content = table
    
    panel = Panel.fit(
        content,
        title="[bold green]🇿🇦 SOUTH AFRICA[/bold green]",
        subtitle=f"[dim]Data from: {data.get('last_updated', 'Unknown')}[/dim]",
        border_style="green"
    )
    console.print(panel)
    
    # Show any errors
    if data.get("errors"):
        console.print("[dim red]Errors:[/dim red]")
        for error in data["errors"]:
            console.print(f"  [red]• {error}[/red]")


def display_full_charts(console: Console) -> None:
    """Display detailed full charts for both markets."""
    console.print()
    console.print("[bold cyan]📊 Detailed Charts[/bold cyan]")
    console.print()
    
    # US 10Y Treasury Yield Chart
    console.print("[yellow]Building US 10Y Treasury chart...[/yellow]")
    us_chart = render_chart.build_full_chart("^TNX", months=6, width=60, height=10)
    console.print(Panel.fit(
        Text.from_ansi(us_chart),
        title="[bold blue]US 10Y Treasury Yield[/bold blue]",
        border_style="blue"
    ))
    console.print()
    
    # USD/ZAR Chart
    console.print("[yellow]Building USD/ZAR chart...[/yellow]")
    zar_chart = render_chart.build_full_chart("ZAR=X", months=6, width=60, height=10)
    console.print(Panel.fit(
        Text.from_ansi(zar_chart),
        title="[bold green]USD/ZAR Exchange Rate[/bold green]",
        border_style="green"
    ))


def main():
    """Main entry point - Phase 1 & 2 test harness."""
    # Initialize database
    data_loader.init_db()
    
    console = Console()
    
    console.print()
    console.print(Panel.fit(
        "[bold white]PROJECT SENTINEL[/bold white]\n"
        "[dim]Sovereign Debt & Fiscal Dominance Monitor[/dim]",
        border_style="bright_white",
        padding=(1, 4)
    ))
    console.print()
    
    # Phase 1 & 2: Test data fetching and charts
    console.print("[bold cyan]Phase 1 & 2: Data Harness + Chart Engine Test[/bold cyan]")
    console.print("[dim]Fetching data from FRED, YFinance, and local JSON...[/dim]")
    console.print()
    
    # Fetch US data
    console.print("[yellow]Fetching US metrics...[/yellow]")
    us_data = data_loader.get_us_metrics()
    display_us_data(console, us_data, show_sparkline=True)
    console.print()
    
    # Fetch SA data
    console.print("[yellow]Fetching SA metrics...[/yellow]")
    sa_data = data_loader.get_sa_metrics()
    display_sa_data(console, sa_data, show_sparkline=True)
    console.print()
    
    # Fetch live market data
    console.print("[yellow]Fetching live market data...[/yellow]")
    live_data = data_loader.get_live_market_data()
    
    live_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    live_table.add_column("Metric", style="cyan")
    live_table.add_column("Value", style="white")
    live_table.add_row("US 10Y Yield", format_value(live_data.get("us_10y_yield"), "%", 2))
    live_table.add_row("USD/ZAR", format_value(live_data.get("usd_zar"), "", 4))
    live_table.add_row("Timestamp", live_data.get("timestamp", "Unknown"))
    
    console.print(Panel.fit(
        live_table,
        title="[bold magenta]📡 LIVE MARKET DATA[/bold magenta]",
        border_style="magenta"
    ))
    
    if live_data.get("errors"):
        for error in live_data["errors"]:
            console.print(f"  [red]• {error}[/red]")
    
    # Phase 2: Display full detailed charts
    display_full_charts(console)
    
    console.print()
    console.print("[bold green]✓ Phase 1 & 2 Complete[/bold green]")
    console.print("[dim]Next: Implement Phase 3 (Dashboard Assembly with Rich Live)[/dim]")


if __name__ == "__main__":
    main()
