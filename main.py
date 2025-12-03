#!/usr/bin/env python3
"""
Project Sentinel - Sovereign Debt & Fiscal Dominance Monitor

Entry point for the dashboard application.
Phase 3: Dashboard Assembly with Rich Live Loop.
"""

import time
import sys
from datetime import datetime

from rich.console import Console
from rich.live import Live

from modules import data_loader, ui_layout

# Configuration
REFRESH_RATE_SECONDS = 0.5  # UI update rate
DATA_FETCH_INTERVAL = 60    # Data fetch interval in seconds
DEFAULT_COUNTRY = "US"      # Default country to monitor

def main():
    """Main entry point."""
    try:
        # Initialize database
        data_loader.init_db()
        
        console = Console()
        console.clear()
        
        # Initial Data Fetch
        console.print(f"[yellow]Initializing Project Sentinel ({DEFAULT_COUNTRY})...[/yellow]")
        
        # Fetch initial metrics
        metrics_data = data_loader.get_country_metrics(DEFAULT_COUNTRY)
        
        # Ensure liquidity data is ready (triggers fetch if needed)
        # We do this once at startup to avoid delay in the loop
        data_loader.get_net_liquidity_data()
        
        last_fetch_time = time.time()
        
        # Initial Layout
        layout = ui_layout.build_dashboard_layout(DEFAULT_COUNTRY, metrics_data, blink_state=True)
        
        # Live Loop
        with Live(layout, screen=True, refresh_per_second=4) as live:
            while True:
                current_time = time.time()
                
                # Check if we need to refresh data
                if current_time - last_fetch_time >= DATA_FETCH_INTERVAL:
                    metrics_data = data_loader.get_country_metrics(DEFAULT_COUNTRY)
                    last_fetch_time = current_time
                
                # Update Blink State (toggle every second)
                blink_state = int(current_time * 2) % 2 == 0
                
                # Rebuild Layout
                layout = ui_layout.build_dashboard_layout(DEFAULT_COUNTRY, metrics_data, blink_state)
                live.update(layout)
                
                # Sleep a bit to prevent 100% CPU usage
                time.sleep(REFRESH_RATE_SECONDS)
                
    except KeyboardInterrupt:
        console.print("\n[bold red]Shutdown initiated...[/bold red]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Fatal Error:[/bold red] {str(e)}")
        # In production, log this
        sys.exit(1)


if __name__ == "__main__":
    main()
