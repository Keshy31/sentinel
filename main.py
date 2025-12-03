#!/usr/bin/env python3
"""
Project Sentinel - Sovereign Debt & Fiscal Dominance Monitor

Entry point for the dashboard application.
"""

import sys
from modules import data_loader

def main():
    """Main entry point."""
    try:
        # Initialize database
        data_loader.init_db()
        
        # Import and run the Textual App
        # We import here to ensure db init happens first if needed, 
        # though Textual app usually handles its own lifecycle.
        from tui import SentinelApp
        
        app = SentinelApp()
        app.run()
                
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
