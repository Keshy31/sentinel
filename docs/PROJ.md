This document outlines the architecture, data strategy, and development phases for **Project Sentinel**, a terminal-based dashboard designed to monitor the structural integrity of US and South African sovereign debt.

-----

# Project Sentinel: Sovereign Debt & Fiscal Dominance Monitor

## 1. Executive Summary

**Project Sentinel** is a real-time command-line interface (CLI) dashboard. Its purpose is to track the transition of the US and South African economies from "Normal" debt cycles into "Fiscal Dominance" (The Doom Loop).

It visualizes the "Druckenmiller Thesis"—comparing government borrowing costs ($r$) against economic growth ($g$) and tax revenues—to identify when debt service becomes mathematically unsustainable.

## 2. Theoretical Framework

The dashboard does not just show numbers; it evaluates the **health of the debt cycle** based on four triggers:

1.  **The Growth Gap ($r - g$):**
      * *Safe:* GDP Growth ($g$) > Bond Yield ($r$).
      * *Danger:* Bond Yield ($r$) > GDP Growth ($g$).
2.  **The Tax Squeeze (Interest vs. Revenue):**
      * *Safe:* Interest payments consume < 10% of tax revenue.
      * *Critical:* Interest payments consume > 20% of tax revenue (The "Doom Loop" Threshold).
3.  **Net Liquidity ("The Plumbing"):**
      * Tracks how Central Bank balance sheet mechanics (Fed Assets - TGA - RRP) drive asset prices (S&P 500).
      * High correlation implies market dependency on liquidity injection rather than fundamentals.
4.  **Yield Curve Inversion (Recession Signal):**
      * *Critical:* 3M Yield > 10Y Yield (Inverted - Recession Warning).

### Advanced Indicators (Phase 5+)
5.  **Market Real Yield & Inflation Expectations:**
      * Uses 5Y Breakevens (`T5YIE`) to calculate *Market Real Yield* (10Y Nominal - 5Y Breakeven).
6.  **Term Premium Decomposition:**
      * Tracks `ACMTP10` to distinguish between Fed rate expectations vs. supply/risk premium. A spike in Term Premium while Fed expectations are flat signals "Fiscal Dominance" panic.
7.  **Capital Flight Signals (Gold/Bond Ratio):**
      * Rising Gold prices alongside rising Bond Yields (falling bond prices) indicates a loss of confidence in the currency/sovereign debt.

## 3. System Architecture

### Tech Stack

  * **Language:** Python 3.10+
  * **Interface:** `rich` (Phase 1-4) -> `textual` (Phase 5+ for interactive TUI).
  * **Charts:** `plotext` (for rendering time-series charts inside the terminal).
  * **Data Processing:** `duckdb` + `pandas` (High-performance analytics).
  * **Caching:** `Parquet` files (Data Lakehouse architecture).
  * **Live Market Data:** `yfinance` (Yahoo Finance API).
  * **US Macro Data:** `fredapi` (Federal Reserve Economic Data).
  * **Configuration:** `JSON` (for manual entry of South African fiscal data).
  * **Environment:** `python-dotenv` (for secure API key management).

### Data Flow Diagram

```text
[Yahoo Finance API] --> (Live Yields/FX) -----\
                                              |--> [DuckDB Analytics Engine] <--> [Parquet Cache]
[FRED API] -----------> (US Macro Data) ------/             |
                                                            |
[config.json] --------> (SA Fiscal Data) -------------------/
                                                            |
                                                            v
                                                   [Rich/Textual UI Renderer]
```

## 4. Data Strategy

### A. United States (Fully Automated)

We will programmatically fetch all US metrics to ensure real-time accuracy.

  * **Market Data (Live):** 
      * US 10Y Yield (`^TNX`).
      * US 3M Yield (`^IRX`).
      * S&P 500 (`^GSPC`).
      * Gold (`GC=F`).
  * **Macro Data (Lagged/Monthly):**
      * Total Public Debt (`GFDEBTN`).
      * Federal Interest Outlays (`A091RC1Q027SBEA`).
      * Federal Tax Receipts (`W006RC1Q027SBEA`).
      * GDP Growth (`GDP`).
      * Net Liquidity Components (Fed Assets, TGA, RRP).
      * **New:** 5-Year Breakeven Inflation (`T5YIE`).
      * **New:** 10-Year Term Premium (`ACMTP10`).

### C. Caching Strategy (DuckDB + Parquet)

To prevent API rate limits and enable offline startup, all fetched data is cached locally.

  * **Macro Data:** Cached for 24 hours.
  * **Market Data:** Cached for 15 minutes.
  * **Fallback:** If API fails, display last known good value from DB.

## 5. Development Phases

We will build this in distinct phases.

### Phase 1: The "Pulse" (Connectivity Proof)
  * **Goal:** Establish API connections and print raw text data to the console.
  * **Status:** Completed.

### Phase 2: The Logic Engine & Hybrid Integration
  * **Goal:** Implement the "Dalio Math", the Manual Data Loader, and **DuckDB Caching**.
  * **Deliverables:**
      * **Persistence Layer:** DuckDB + Parquet.
      * **Calculation Module:** US/SA Doom Loop Ratios.
  * **Status:** Completed.

### Phase 3: The Dashboard (UI Implementation)
  * **Goal:** Replace text printouts with the `rich` TUI.
  * **Deliverables:**
      * Split screen layout (US/SA).
      * Live Ticker.
      * Visual Styling (Red/Green indicators).
  * **Status:** Completed.

### Phase 4: The "Doom Loop" Indicators & Advanced Analytics
  * **Goal:** Add the "Interpretation Layer" and "Net Liquidity" analysis.
  * **Deliverables:**
      * **Net Liquidity Chart:** Dual axis chart tracking "The Plumbing" vs S&P 500.
      * **Status Headers:** Visual warnings for Fiscal Dominance.
      * **Visceral Metrics:** "Days of Interest" ($ spent on interest per day).
  * **Status:** In Progress.

### Phase 5: Interactive TUI & Deep Analytics (Future)
  * **Goal:** Upgrade UI to `Textual` for interactivity and implement deep financial modeling.
  * **Deliverables:**
      * **Interactive TUI:** Tabs for [US], [SA], [Liquidity], [Forex].
      * **Drill-down:** Enter key on metrics to see full-screen historical charts.
      * **Advanced Analytics:**
          * Market Real Yield (using Breakevens).
          * Term Premium Decomposition.
          * "Day Zero" Forecast (Linear Regression on Interest/Revenue ratio).
      * **News Ticker:** RSS scrolling marquee for context.
      * **Global Grid:** Multi-country comparison table.

## 6. Project Directory Structure

```text
project_sentinel/
├── .env                  # API Keys (FRED_API_KEY=...)
├── config.py             # Constants (Thresholds, File Paths)
├── main.py               # Entry point (Run Loop)
├── data/
│   ├── cache/            # Parquet files
│   └── sa_fiscal.json    # Manual input file for SA Budget data
├── modules/
│   ├── __init__.py
│   ├── data_loader.py    # Handles FRED, YFinance, and JSON loading
│   ├── db_manager.py     # DuckDB and Parquet interactions
│   ├── logic.py          # Pure functions for financial math
│   ├── render_chart.py   # Plotext charting functions
│   └── ui_layout.py      # Rich panels and table composition
└── requirements.txt      # Dependencies
```
