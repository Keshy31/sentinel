#!/usr/bin/env python3
"""
Project Sentinel - Interactive TUI

A Textual-based terminal dashboard for monitoring Sovereign Debt & Fiscal Dominance.
"""

import time
import feedparser
from datetime import datetime
from typing import List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Static, Label, TabbedContent, TabPane, DataTable, Button
from textual.reactive import reactive
from textual.worker import Worker, get_current_worker

from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich import box

from modules import data_loader, logic, render_chart
import config

# =============================================================================
# Custom Widgets
# =============================================================================

class NewsTicker(Static):
    """Scrolling news ticker fetching from RSS."""
    
    NEWS_ITEMS = reactive([])
    current_index = reactive(0)
    
    def on_mount(self) -> None:
        """Start background fetch and scroll."""
        self.update_news()
        self.set_interval(600, self.update_news) # Fetch every 10 mins
        self.set_interval(0.2, self.scroll_ticker) # Scroll speed
        
    def update_news(self) -> None:
        """Fetch RSS feeds in background."""
        self.run_worker(self._fetch_rss, thread=True)
        
    def _fetch_rss(self):
        items = []
        keywords = ["Treasury", "Fed", "Auction", "Yield", "Bond", "Debt", "Inflation", "Gold"]
        
        for url in config.RSS_FEEDS:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]: # Top 5 per feed
                    title = entry.title
                    # Simple keyword filter
                    if any(k.lower() in title.lower() for k in keywords):
                        source = feed.feed.get('title', 'News')
                        items.append(f"[{source}] {title}")
            except Exception:
                pass
        
        if items:
            self.NEWS_ITEMS = items

    def scroll_ticker(self) -> None:
        """Update the displayed text."""
        if not self.NEWS_ITEMS:
            self.update("Fetching market news...")
            return
            
        # Create a rolling string
        text = "  ***  ".join(self.NEWS_ITEMS) + "  ***  "
        # Display a window of it? 
        # For simple ticker, just cycle through items
        item = self.NEWS_ITEMS[self.current_index % len(self.NEWS_ITEMS)]
        self.update(f"📰 {item}")
        self.current_index += 1


class MetricPanel(Static):
    """Display a single large metric with status."""
    
    def __init__(self, title: str, value: str, status: str = "SAFE", **kwargs):
        super().__init__(**kwargs)
        self.title_text = title
        self.value_text = value
        self.status = status
        
    def render(self) -> Panel:
        color = "green"
        if self.status == "WARNING": color = "yellow"
        elif self.status == "CRITICAL": color = "red"
        
        return Panel(
            f"[{color}]{self.value_text}[/{color}]\n[dim]{self.status}[/dim]",
            title=self.title_text,
            border_style=color
        )

class FiscalDashboard(Container):
    """
    Fiscal Dashboard for a specific country.
    """
    
    def __init__(self, country_code: str, **kwargs):
        super().__init__(**kwargs)
        self.country_code = country_code
        self.metrics_data = {}
        
    def compose(self) -> ComposeResult:
        yield Label(f"Loading {self.country_code} Data...", id=f"loading-{self.country_code}")
        
        with Vertical(id=f"content-{self.country_code}", classes="hidden"):
            # Top Row: Key Metrics
            with Horizontal(classes="metrics-row"):
                yield DataTable(id=f"fiscal-stats-{self.country_code}", classes="panel")
                yield DataTable(id=f"monetary-stats-{self.country_code}", classes="panel")
            
            # Middle: Charts
            with Horizontal(classes="charts-row"):
                yield Static(id=f"chart-yield-{self.country_code}", classes="chart-panel")
                yield Static(id=f"chart-gold-{self.country_code}", classes="chart-panel")
                
            # Bottom: Alerts
            yield Static(id=f"alerts-{self.country_code}", classes="alert-bar")

    def on_mount(self) -> None:
        self.load_data()
        self.set_interval(60, self.load_data)

    def load_data(self) -> None:
        self.run_worker(self._fetch_data, thread=True)

    def _fetch_data(self):
        data = data_loader.get_country_metrics(self.country_code)
        self.call_from_thread(self.update_ui, data)

    def update_ui(self, data: dict) -> None:
        self.query_one(f"#loading-{self.country_code}").display = False
        self.query_one(f"#content-{self.country_code}").display = True
        self.query_one(f"#content-{self.country_code}").remove_class("hidden")
        
        # 1. Update Fiscal Stats
        fiscal_table = self.query_one(f"#fiscal-stats-{self.country_code}", DataTable)
        fiscal_table.cursor_type = "row"
        fiscal_table.clear()
        if not fiscal_table.columns:
            fiscal_table.add_columns("Metric", "Value")
        
        self._populate_fiscal_table(fiscal_table, data)
        
        # 2. Update Monetary Stats
        mon_table = self.query_one(f"#monetary-stats-{self.country_code}", DataTable)
        mon_table.cursor_type = "row"
        mon_table.clear()
        if not mon_table.columns:
            mon_table.add_columns("Metric", "Value")
            
        self._populate_monetary_table(mon_table, data)
        
        # 3. Charts (Ascii)
        # Yield Curve
        yield_chart = render_chart.build_yield_curve_chart(self.country_code, width=50, height=10)
        self.query_one(f"#chart-yield-{self.country_code}").update(
            Panel(Text.from_ansi(yield_chart), title="Yield Curve", border_style="white")
        )
        
        # Gold/Bond Ratio (If US) or just Yield History
        if self.country_code == "US":
            # Comparison Chart: Gold vs 10Y Yield
            gold_bond_chart = render_chart.build_comparison_chart(["GC=F", "^TNX"], width=50, height=10)
            self.query_one(f"#chart-gold-{self.country_code}").update(
                Panel(Text.from_ansi(gold_bond_chart), title="Gold vs Yields (Deflation/Confidence)", border_style="yellow")
            )
        else:
             # Just Yield History
            ticker = config.COUNTRIES[self.country_code]["metrics"].get("yield_10y")
            if ticker:
                hist_chart = render_chart.build_full_chart(ticker, width=50, height=10)
                self.query_one(f"#chart-gold-{self.country_code}").update(
                    Panel(Text.from_ansi(hist_chart), title="10Y Yield History", border_style="yellow")
                )

        # 4. Alerts
        self._update_alerts(data)

    def _populate_fiscal_table(self, table: DataTable, data: dict) -> None:
        currency = data.get("currency_symbol", "")
        
        # Debt
        debt = data.get("total_debt")
        table.add_row("Total Debt", f"{debt:,.0f} B {currency}" if debt else "N/A")
        
        # Debt/GDP
        if data.get("total_debt") and data.get("gdp"):
            ratio = logic.calculate_debt_to_gdp_ratio(data["total_debt"], data["gdp"])
            status = logic.get_debt_gdp_status(ratio)
            # Rich formatting in DataTable requires Text objects or string markup
            # Textual DataTable supports rich text
            color = "red" if status == "CRITICAL" else "yellow" if status == "WARNING" else "green"
            table.add_row("Debt/GDP", f"[{color}]{ratio:.1f}%[/{color}]")
        
        # Interest/Revenue
        if data.get("interest_payments") and data.get("tax_receipts"):
            ratio = logic.calculate_interest_revenue_ratio(data["interest_payments"], data["tax_receipts"])
            status = logic.get_interest_ratio_status(ratio)
            color = "red" if status == "CRITICAL" else "yellow" if status == "WARNING" else "green"
            table.add_row("Interest/Revenue", f"[{color}]{ratio*100:.1f}%[/{color}]")
            
        # Days of Interest
        yield_10y = data.get("yield_10y")
        if debt and yield_10y:
            daily_cost = logic.calculate_days_of_interest(debt, yield_10y)
            table.add_row("Daily Interest Cost", f"[bold red]{daily_cost:,.2f} B {currency}[/bold red]")

    def _populate_monetary_table(self, table: DataTable, data: dict) -> None:
        # Yields
        y10 = data.get("yield_10y")
        table.add_row("10Y Yield", f"{y10:.2f}%" if y10 else "N/A")
        
        # Inflation
        inf = data.get("inflation_yoy")
        table.add_row("Inflation (YoY)", f"{inf:.2f}%" if inf else "N/A")
        
        # Real Yield
        if y10 and inf:
            real = logic.calculate_real_yield(y10, inf)
            color = "green" if real > 0 else "red"
            table.add_row("Real Yield", f"[{color}]{real:+.2f}%[/{color}]")
            
        # Currency
        if "usd_zar" in data and data["usd_zar"]:
             table.add_row("USD/ZAR", f"{data['usd_zar']:.2f}")
        
    def _update_alerts(self, data: dict) -> None:
        alerts = []
        # Check Debt Spiral
        if data.get("interest_payments") and data.get("tax_receipts"):
            ratio = logic.calculate_interest_revenue_ratio(data["interest_payments"], data["tax_receipts"])
            if ratio > 0.20:
                alerts.append("CRITICAL: DEBT SPIRAL DETECTED (Int/Rev > 20%)")
        
        alert_widget = self.query_one(f"#alerts-{self.country_code}")
        if alerts:
            alert_widget.update(" | ".join(alerts))
            alert_widget.add_class("critical")
        else:
            alert_widget.update("System Status: STABLE")
            alert_widget.remove_class("critical")


class GlobalGrid(Container):
    """
    Multi-country comparison table.
    """
    
    def compose(self) -> ComposeResult:
        yield Label("Global Sovereign Debt Monitor", classes="header-label")
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Country", "10Y Yield", "Debt/GDP", "Int/Revenue", "Status")
        self.load_data()
        self.set_interval(60, self.load_data)
        
    def load_data(self) -> None:
        self.run_worker(self._fetch_all, thread=True)
        
    def _fetch_all(self):
        rows = []
        for code in ["US", "SA", "JP", "UK", "DE"]:
            data = data_loader.get_country_metrics(code)
            
            # Yield
            y10 = f"{data.get('yield_10y', 0):.2f}%" if data.get('yield_10y') else "N/A"
            
            # Debt/GDP
            dg = "N/A"
            if data.get("total_debt") and data.get("gdp"):
                ratio = logic.calculate_debt_to_gdp_ratio(data["total_debt"], data["gdp"])
                dg = f"{ratio:.1f}%"
                
            # Int/Rev
            ir = "N/A"
            if data.get("interest_payments") and data.get("tax_receipts"):
                ratio = logic.calculate_interest_revenue_ratio(data["interest_payments"], data["tax_receipts"])
                ir = f"{ratio*100:.1f}%"
                
            # Status
            status = "STABLE" # Simple logic for now
            if data.get("yield_10y", 0) > 10: status = "CRITICAL"
            
            rows.append((config.COUNTRIES[code]["flag"] + " " + code, y10, dg, ir, status))
            
        self.call_from_thread(self.update_table, rows)

    def update_table(self, rows: List[tuple]):
        table = self.query_one(DataTable)
        table.clear()
        table.add_rows(rows)


class LiquidityPanel(Container):
    """
    Net Liquidity Visualization.
    """
    def compose(self) -> ComposeResult:
        yield Label("Global Net Liquidity vs S&P 500", classes="header-label")
        yield Static(id="liquidity-chart", classes="chart-panel")
        
    def on_mount(self) -> None:
        self.load_chart()
        
    def load_chart(self):
        self.run_worker(self._render, thread=True)
        
    def _render(self):
        # This can be slow, so run in worker
        chart_str = render_chart.build_liquidity_chart(width=100, height=20)
        self.call_from_thread(self.query_one("#liquidity-chart").update, Text.from_ansi(chart_str))


class SentinelApp(App):
    """The Main Application."""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    Header {
        dock: top;
    }
    
    Footer {
        dock: bottom;
    }
    
    NewsTicker {
        dock: bottom;
        height: 1;
        background: $primary;
        color: white;
    }
    
    .hidden {
        display: none;
    }
    
    .metrics-row {
        height: 14;
        margin-bottom: 1;
    }
    
    .panel {
        width: 1fr;
        height: 100%;
        padding: 1;
    }
    
    .charts-row {
        height: 1fr;
    }
    
    .chart-panel {
        width: 1fr;
        height: 100%;
        border: solid green;
    }
    
    .header-label {
        text-align: center;
        text-style: bold;
        padding: 1;
    }
    
    .alert-bar {
        height: 3;
        background: $surface;
        color: green;
        text-align: center;
        content-align: center middle;
        text-style: bold;
    }
    
    .alert-bar.critical {
        background: red;
        color: white;
        animate: blink 1s;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_data", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with TabbedContent():
            with TabPane("🇺🇸 US", id="tab-us"):
                yield FiscalDashboard("US")
                
            with TabPane("🇿🇦 SA", id="tab-sa"):
                yield FiscalDashboard("SA")
                
            with TabPane("🌍 Global", id="tab-global"):
                yield GlobalGrid()
                
            with TabPane("💧 Liquidity", id="tab-liquidity"):
                yield LiquidityPanel()
                
        yield NewsTicker()

    def action_refresh_data(self):
        # Trigger reload on all dashboards
        for dashboard in self.query(FiscalDashboard):
            dashboard.load_data()
        for grid in self.query(GlobalGrid):
            grid.load_data()
        for liq in self.query(LiquidityPanel):
            liq.load_chart()

if __name__ == "__main__":
    app = SentinelApp()
    app.run()

