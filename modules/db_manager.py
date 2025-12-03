"""
Project Sentinel - Database Manager (DuckDB Version)

Handles DuckDB interactions for caching macroeconomic and market data.
- Metrics are stored in a DuckDB table.
- Time-series charts are stored as Parquet files for high performance.
"""

import duckdb
import pandas as pd
from datetime import datetime
from typing import Optional, Any, Dict
from pathlib import Path
import config

class DatabaseManager:
    def __init__(self, db_path: Path = None):
        # If no path provided, use the one from config, but change extension to .duckdb
        if db_path is None:
            self.db_path = config.DB_PATH.with_suffix('.duckdb')
        else:
            self.db_path = db_path
            
        self.cache_dir = config.DATA_DIR / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Create a database connection."""
        return duckdb.connect(str(self.db_path))

    def init_db(self) -> None:
        """Initialize the database tables."""
        conn = self._get_connection()
        
        # Table for single value metrics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metric_cache (
                key VARCHAR PRIMARY KEY,
                value DOUBLE,
                timestamp TIMESTAMP,
                source VARCHAR
            )
        """)
        
        # Table to track chart timestamps (data lives in Parquet)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chart_metadata (
                ticker VARCHAR PRIMARY KEY,
                timestamp TIMESTAMP
            )
        """)
        
        conn.close()

    def set_metric(self, key: str, value: float, source: str) -> None:
        """Store a metric value with current timestamp."""
        conn = self._get_connection()
        timestamp = datetime.now()
        
        # Upsert logic
        conn.execute("""
            INSERT OR REPLACE INTO metric_cache (key, value, timestamp, source)
            VALUES (?, ?, ?, ?)
        """, (key, value, timestamp, source))
        
        conn.close()

    def get_metric(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a metric from cache."""
        conn = self._get_connection()
        
        result = conn.execute(
            "SELECT value, timestamp, source FROM metric_cache WHERE key = ?", 
            (key,)
        ).fetchone()
        
        conn.close()
        
        if result:
            return {
                "value": result[0],
                "timestamp": result[1].isoformat() if hasattr(result[1], 'isoformat') else str(result[1]),
                "source": result[2]
            }
        return None

    def set_chart(self, ticker: str, df: pd.DataFrame) -> None:
        """Store chart data as Parquet and update metadata."""
        # Sanitize ticker for filename
        safe_ticker = ticker.replace("^", "").replace("=", "").replace("/", "_")
        file_path = self.cache_dir / f"{safe_ticker}.parquet"
        
        # Ensure index is saved as a column for SQL querying
        # If index has a name (e.g. "Date"), reset_index will make it a column
        df_to_save = df.copy()
        if df_to_save.index.name == "Date":
            df_to_save = df_to_save.reset_index()
        
        # Save to Parquet
        df_to_save.to_parquet(file_path)
        
        # Update metadata
        conn = self._get_connection()
        timestamp = datetime.now()
        
        conn.execute("""
            INSERT OR REPLACE INTO chart_metadata (ticker, timestamp)
            VALUES (?, ?)
        """, (ticker, timestamp))
        
        conn.close()

    def get_chart(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Retrieve chart data from Parquet cache."""
        conn = self._get_connection()
        
        # Check metadata first
        meta = conn.execute(
            "SELECT timestamp FROM chart_metadata WHERE ticker = ?", 
            (ticker,)
        ).fetchone()
        
        conn.close()
        
        if not meta:
            return None
            
        timestamp = meta[0]
        safe_ticker = ticker.replace("^", "").replace("=", "").replace("/", "_")
        file_path = self.cache_dir / f"{safe_ticker}.parquet"
        
        if not file_path.exists():
            return None
            
        try:
            # Read Parquet
            df = pd.read_parquet(file_path)
            
            # Restore index if Date column exists (compatibility with rest of app)
            if "Date" in df.columns:
                df = df.set_index("Date")
            
            return {
                "data": df,
                "timestamp": timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
            }
        except Exception as e:
            print(f"Error reading parquet for {ticker}: {e}")
            return None

    def get_duckdb_connection(self) -> duckdb.DuckDBPyConnection:
        """Expose raw connection for complex analytical queries."""
        return self._get_connection()

# Global instance
db = DatabaseManager()
