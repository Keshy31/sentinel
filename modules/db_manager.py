"""
Project Sentinel - Database Manager

Handles SQLite interactions for caching macroeconomic and market data.
"""

import sqlite3
import json
from io import StringIO
from datetime import datetime
from typing import Optional, Any, Dict, Tuple
from pathlib import Path
import pandas as pd

import config

class DatabaseManager:
    def __init__(self, db_path: Path = config.DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Create a database connection."""
        return sqlite3.connect(self.db_path)

    def init_db(self) -> None:
        """Initialize the database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Table for single value metrics (e.g., GDP, Yield)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metric_cache (
                key TEXT PRIMARY KEY,
                value REAL,
                timestamp DATETIME,
                source TEXT
            )
        """)
        
        # Table for chart data (serialized JSON)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chart_cache (
                ticker TEXT PRIMARY KEY,
                data_json TEXT,
                timestamp DATETIME
            )
        """)
        
        conn.commit()
        conn.close()

    def set_metric(self, key: str, value: float, source: str) -> None:
        """Store a metric value with current timestamp."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO metric_cache (key, value, timestamp, source)
            VALUES (?, ?, ?, ?)
        """, (key, value, datetime.now().isoformat(), source))
        
        conn.commit()
        conn.close()

    def get_metric(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a metric from cache.
        
        Returns:
            Dict with 'value', 'timestamp', 'source' or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT value, timestamp, source FROM metric_cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                "value": row[0],
                "timestamp": row[1],
                "source": row[2]
            }
        return None

    def set_chart(self, ticker: str, df: pd.DataFrame) -> None:
        """Store chart data (DataFrame) as JSON."""
        # Reset index to make Date a column, so it serializes nicely
        df_reset = df.reset_index()
        # Convert date to string to ensure JSON serialization works
        if 'Date' in df_reset.columns:
             df_reset['Date'] = df_reset['Date'].astype(str)
             
        data_json = df_reset.to_json(orient="records")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO chart_cache (ticker, data_json, timestamp)
            VALUES (?, ?, ?)
        """, (ticker, data_json, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()

    def get_chart(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve chart data from cache.
        
        Returns:
            Dict with 'data' (DataFrame) and 'timestamp', or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT data_json, timestamp FROM chart_cache WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            try:
                data_json = row[0]
                timestamp = row[1]
                
                # Deserialize JSON back to DataFrame
                df = pd.read_json(StringIO(data_json), orient="records")
                
                # Ensure we have a DatetimeIndex if Date column exists
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'], utc=True)
                    df.set_index('Date', inplace=True)
                
                return {
                    "data": df,
                    "timestamp": timestamp
                }
            except Exception as e:
                print(f"Error deserializing chart cache for {ticker}: {e}")
                return None
                
        return None

# Global instance
db = DatabaseManager()
