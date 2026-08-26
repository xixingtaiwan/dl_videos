#!/usr/bin/env python3
"""
Configuration file for Video Import Tool
Update these settings to match your PostgreSQL setup
"""

from pathlib import Path

# Base Directory
BASE_DIR = Path('/Users/eric/Moonova/ShortVideo/Download-Videos')
JSON_DIR = BASE_DIR / 'idrama'
DOWNLOAD_DIR = BASE_DIR / 'videos'

# PostgreSQL Database Configuration
DATABASE_CONFIG = {
    'host': 'localhost',           # PostgreSQL host
    'port': 5432,                  # PostgreSQL port
    'user': 'video_user',          # PostgreSQL user
    'password': 'postgres123',     # PostgreSQL password
    'database': 'films_db',        # Database name
}

# Alternative: Connection string format
# DATABASE_URL = 'postgresql://postgres:password@localhost:5432/films_db'

# Scan interval (seconds)
SCAN_INTERVAL = 600  # 10 minutes (change to 300 for 5 min, 1800 for 30 min)

# Logging
LOG_FILE = BASE_DIR / 'import_tool.log'

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = [2, 4]  # Seconds to wait between retries

print("⚠️  IMPORTANT: Configure PostgreSQL credentials in config.py")
print(f"   Host: {DATABASE_CONFIG['host']}")
print(f"   Port: {DATABASE_CONFIG['port']}")
print(f"   User: {DATABASE_CONFIG['user']}")
print(f"   Database: {DATABASE_CONFIG['database']}")
print(f"   ⚠️  Update 'password' field before running!")
