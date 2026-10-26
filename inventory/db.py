"""
Database access and management functions.
"""

import sqlite3
from pathlib import Path
from inventory.db_schema import init_database, get_schema_info

# Fixed: Use correct path relative to this file
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "inventory.db"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_connection() -> sqlite3.Connection:
    """
    Get database connection with proper initialization.
    Now uses centralized schema management.
    """
    return init_database(DB_PATH)


def init_db():
    """
    Initialize database with full schema.
    This is now a thin wrapper around db_schema.init_database()
    """
    conn = get_connection()

    # Print schema info for verification
    info = get_schema_info(conn)
    print(f"✓ Database initialized at {DB_PATH}")
    print(f"  Schema version: {info['version']}")
    print(f"  Tables: {', '.join(info['tables'])}")

    conn.close()


def db_exists() -> bool:
    """Check if database file exists"""
    return DB_PATH.exists()


# Auto-initialize if database doesn't exist
if not db_exists():
    init_db()
