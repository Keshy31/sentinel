"""
Project Sentinel - Modules Package

This package contains all the core modules for the Sentinel dashboard:
- data_loader: Fetches data from FRED, YFinance, and local JSON
- logic: Financial calculations and threshold checks
- render_chart: Plotext chart generation
- ui_layout: Rich dashboard layout and rendering
"""

from . import data_loader
from . import logic
from . import render_chart
from . import ui_layout

__all__ = ["data_loader", "logic", "render_chart", "ui_layout"]

