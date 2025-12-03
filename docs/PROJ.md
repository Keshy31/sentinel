This document outlines the architecture, data strategy, and development phases for **Project Sentinel**, a terminal-based dashboard designed to monitor the structural integrity of US and South African sovereign debt.

-----

# Project Sentinel: Sovereign Debt & Fiscal Dominance Monitor

## 1. Executive Summary

**Project Sentinel** is a real-time command-line interface (CLI) dashboard. Its purpose is to track the transition of the US and South African economies from "Normal" debt cycles into "Fiscal Dominance" (The Doom Loop).

It visualizes the "Druckenmiller Thesis"—comparing government borrowing costs ($r$) against economic growth ($g$) and tax revenues—to identify when debt service becomes mathematically unsustainable.

## 2. Theoretical Framework

The dashboard does not just show numbers; it evaluates the **health of the debt cycle** based on three triggers:

1.  **The Growth Gap ($r - g$):**
      * *Safe:* GDP Growth ($g$) > Bond Yield ($r$).
      * *Danger:* Bond Yield ($r$) > GDP Growth ($g$).
2.  **The Tax Squeeze (Interest vs. Revenue):**
      * *Safe:* Interest payments consume < 10% of tax revenue.
      * *Critical:* Interest payments consume > 20% of tax revenue (The "Doom Loop" Threshold).
3.  **Market Confidence:**
      * Rising Long-Term Yields (Bond Vigilantes revolting).
      * Currency devaluation (Loss of trust).
4.  **Yield Curve Inversion (Recession Signal):**
      * *Safe:* 10Y Yield > 3M Yield (Positive slope).
      * *Critical:* 3M Yield > 10Y Yield (Inverted - Recession Warning).

## 3. System Architecture

### Tech Stack

  * **Language:** Python 3.10+
  * **Interface:** `rich` library (for "Bloomberg Terminal" style aesthetics).
  * **Charts:** `plotext` (for rendering time-series charts inside the terminal).
  * **Data Processing:** `pandas`.
  * **Caching:** `sqlite3` (Standard Library) for offline capabilities and rate-limit handling.
  * **Live Market Data:** `yfinance` (Yahoo Finance API).
  * **US Macro Data:** `fredapi` (Federal Reserve Economic Data).
  * **Configuration:** `JSON` (for manual entry of South African fiscal data).
  * **Environment:** `python-dotenv` (for secure API key management).

### Data Flow Diagram

```text
[Yahoo Finance API] --> (Live Yields/FX) -----\
                                              |--> [Data Processing Engine] <--> [SQLite Cache]
[FRED API] -----------> (US Debt/GDP/Tax) ----/             |                    (Persistence)
                                                            |
[config.json] --------> (SA Fiscal Data) -------------------/                         |
                                                                                      v
                                                                             [Rich UI Renderer]
```

## 4. Data Strategy

### A. United States (Fully Automated)

We will programmatically fetch all US metrics to ensure real-time accuracy.

  * **Market Data (Live):** 
      * US 10Y Yield (`^TNX`).
      * US 3M Yield (`^IRX`).
  * **Macro Data (Lagged/Monthly):**
      * Total Public Debt (`GFDEBTN`).
      * Federal Interest Outlays (`A091RC1Q027SBEA`).
      * Federal Tax Receipts (`W006RC1Q027SBEA`).
      * GDP Growth (`GDP`).

### C. Caching Strategy (SQLite)

To prevent API rate limits and enable offline startup, all fetched data is cached in a local `sentinel.db`.

  * **Macro Data:** Cached for 24 hours.
  * **Market Data:** Cached for 15 minutes.
  * **Fallback:** If API fails, display last known good value from DB with a "STALE" warning.

## 5. Development Phases

We will build this in 4 distinct phases. Each phase results in a testable milestone.

### Phase 1: The "Pulse" (Connectivity Proof)

  * **Goal:** Establish API connections and print raw text data to the console.
  * **Deliverables:**
      * Script connecting to Yahoo Finance to fetch US 10Y and USD/ZAR.
      * Script connecting to FRED to fetch US Debt.
      * Basic `print()` output confirming data retrieval.
  * **Test:** Run script $\rightarrow$ See current interest rates and debt numbers.

### Phase 2: The Logic Engine & Hybrid Integration

  * **Goal:** Implement the "Dalio Math", the Manual Data Loader, and **SQLite Caching**.
  * **Deliverables:**
      * **Calculation Module:**
          * Compute US Interest/Revenue Ratio.
          * Compute US ($r - g$).
      * **Persistence Layer:**
          * Implement `DatabaseManager` class using `sqlite3`.
          * Create tables for `metrics` and `historical_charts`.
      * **Config Loader:** Create the Python function to read `sa_fiscal.json`.
      * **SA Calculation:** Compute SA Interest/Revenue using the JSON data.
  * **Test:**
      * Change a number in `sa_fiscal.json` $\rightarrow$ Run script $\rightarrow$ See the calculated ratio change.
      * Disconnect Internet $\rightarrow$ Run script $\rightarrow$ Verify data loads from Cache.

### Phase 3: The Dashboard (UI Implementation)

  * **Goal:** Replace text printouts with the `rich` TUI (Text User Interface).
  * **Deliverables:**
      * **Layout Design:** Split screen (US Left / SA Right).
      * **Live Ticker:** Implement the `Live()` refresh loop (updating every 60s).
      * **Visual Styling:**
          * Green text for "Safe".
          * Red text/background for "Critical".
          * Blinking indicators for live updates.
  * **Test:** The dashboard runs continuously in the terminal without crashing.

### Phase 4: The "Doom Loop" Indicators

  * **Goal:** Add the "Interpretation Layer."
  * **Deliverables:**
      * Add status headers (e.g., "STATUS: FISCAL DOMINANCE").
      * Logic:
          * IF `US Interest/Rev > 18%` $\rightarrow$ Display Warning.
          * IF `US 10Y > 5%` $\rightarrow$ Display "VIGILANTE ATTACK".
          * IF `10Y - 3M < 0` $\rightarrow$ Display "YIELD CURVE INVERTED".
  * **Test:** Verify that threshold logic correctly triggers the visual warnings.

## 6. Project Directory Structure

```text
project_sentinel/
├── .env                  # API Keys (FRED_API_KEY=...)
├── config.py             # Constants (Thresholds, File Paths)
├── main.py               # Entry point (Run Loop)
├── data/
│   └── sa_fiscal.json    # Manual input file for SA Budget data
├── modules/
│   ├── __init__.py
│   ├── data_loader.py    # Handles FRED, YFinance, and JSON loading
│   ├── logic.py          # Pure functions for financial math
│   ├── render_chart.py   # Plotext charting functions
│   └── ui_layout.py      # Rich panels and table composition
└── requirements.txt      # Dependencies
```
