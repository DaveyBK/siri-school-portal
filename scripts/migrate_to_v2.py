"""
Migrate production database to schema version 2.
Adds audit rollback capability.
"""

import shutil
from pathlib import Path
from datetime import datetime

from inventory.db_schema import init_database, get_current_version, get_schema_info
from inventory.db import DB_PATH

def migrate_to_v2():
    """Migrate to schema version 2"""
    
    print("=" * 60)
    print("MIGRATION TO SCHEMA VERSION 2")
    print("=" * 60)
    
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        return
    
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"inventory_pre_v2_{timestamp}.db"
    
    print(f"\n1. Creating backup...")
    shutil.copy2(DB_PATH, backup_path)
    print(f"   ✅ Backup created: {backup_path}")
    
    print(f"\n2. Checking current schema...")
    conn = init_database(DB_PATH)
    current_version = get_current_version(conn)
    print(f"   Current schema version: {current_version}")
    
    if current_version >= 2:
        print(f"   ⚠️  Already at version 2 or higher!")
        conn.close()
        return
    
    print(f"\n3. Applying migrations...")
    conn.close()
    conn = init_database(DB_PATH)
    
    new_version = get_current_version(conn)
    info = get_schema_info(conn)
    
    print(f"\n4. Migration complete:")
    print(f"   New schema version: {new_version}")
    print(f"   Tables: {', '.join(info['tables'])}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Migration to Version 2 Complete!")
    print("=" * 60)

if __name__ == "__main__":
    migrate_to_v2()
