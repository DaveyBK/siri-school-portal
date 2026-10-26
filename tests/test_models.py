"""Test Part 1: Database Schema Consolidation"""
import sys
from pathlib import Path

# Add project to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from inventory.db_schema import init_database, get_schema_info, get_current_version

DB_PATH = ROOT / "data" / "test_inventory.db"

print("=" * 60)
print("TESTING PART 1: Database Schema Consolidation")
print("=" * 60)

# Test 1: Initialize database
print("\n1. Initializing database...")
try:
    conn = init_database(DB_PATH)
    print("   ✅ Database initialized successfully")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Check schema version
print("\n2. Checking schema version...")
try:
    version = get_current_version(conn)
    print(f"   ✅ Current schema version: {version}")
    if version == 0:
        print("   ⚠️  Warning: Schema version is 0 (not migrated)")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Get schema info
print("\n3. Getting schema information...")
try:
    info = get_schema_info(conn)
    print(f"   ✅ Schema version: {info['version']}")
    print(f"   ✅ Tables found: {len(info['tables'])}")
    print(f"      Tables: {', '.join(info['tables'])}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Check if schema_version table exists
print("\n4. Verifying schema_version table...")
try:
    cursor = conn.execute("SELECT * FROM schema_version")
    rows = cursor.fetchall()
    print(f"   ✅ Schema version table exists")
    print(f"   ✅ Migration records: {len(rows)}")
    for row in rows:
        print(f"      - Version {row[0]}: {row[2]} (applied {row[1]})")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Check foreign keys are enabled
print("\n5. Checking foreign key constraints...")
try:
    cursor = conn.execute("PRAGMA foreign_keys")
    fk_enabled = cursor.fetchone()[0]
    if fk_enabled:
        print("   ✅ Foreign keys are ENABLED")
    else:
        print("   ❌ Foreign keys are DISABLED")
except Exception as e:
    print(f"   ❌ Error: {e}")

conn.close()

print("\n" + "=" * 60)
print("✅ Part 1 Testing Complete!")
print("=" * 60)
print(f"\nTest database created at: {DB_PATH}")
print("You can delete this test database after reviewing results.")
