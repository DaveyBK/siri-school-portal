"""
Migrate production database to new schema version.
Backs up existing database before migration.
"""

import shutil
from pathlib import Path
from datetime import datetime

from inventory.db_schema import init_database, get_current_version, get_schema_info
from inventory.db import DB_PATH

def migrate_production_database():
    """Migrate production database with backup"""
    
    print("=" * 60)
    print("PRODUCTION DATABASE MIGRATION")
    print("=" * 60)
    
    if not DB_PATH.exists():
        print(f"❌ Production database not found at: {DB_PATH}")
        return
    
    # 1. Create backup
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"inventory_pre_migration_{timestamp}.db"
    
    print(f"\n1. Creating backup...")
    shutil.copy2(DB_PATH, backup_path)
    print(f"   ✅ Backup created: {backup_path}")
    
    # 2. Check current schema version
    print(f"\n2. Checking current schema...")
    conn = init_database(DB_PATH)
    current_version = get_current_version(conn)
    print(f"   Current schema version: {current_version}")
    
    # 3. Get schema info
    info = get_schema_info(conn)
    print(f"\n3. Database info:")
    print(f"   Schema version: {info['version']}")
    print(f"   Tables: {', '.join(info['tables'])}")
    print(f"   Migrations available: {info['migrations_available']}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Migration Complete!")
    print("=" * 60)
    print(f"\nBackup saved to: {backup_path}")
    print("Your production database is now using the new schema system.")

if __name__ == "__main__":
    migrate_production_database()
