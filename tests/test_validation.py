"""Test Part 2: Audit Logging Infrastructure"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from inventory.db_schema import init_database
from inventory.audit import AuditLogger

DB_PATH = ROOT / "data" / "test_inventory.db"

print("=" * 60)
print("TESTING PART 2: Audit Logging Infrastructure")
print("=" * 60)

# Initialize database
conn = init_database(DB_PATH)
conn.close()

# Create audit logger
auditor = AuditLogger(DB_PATH)

# Test 1: Log a student creation
print("\n1. Testing student creation logging...")
try:
    log_id = auditor.log_student_create(
        student_id="TEST001",
        data={"first_name": "John", "last_name": "Doe", "level": "SM3"},
        user="test_admin"
    )
    print(f"   ✅ Created audit log with ID: {log_id}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Log a student update
print("\n2. Testing student update logging...")
try:
    log_id = auditor.log_student_update(
        student_id="TEST001",
        old_data={"first_name": "John", "last_name": "Doe", "level": "SM3"},
        new_data={"first_name": "John", "last_name": "Smith", "level": "SM4"},
        user="test_admin"
    )
    print(f"   ✅ Created update audit log with ID: {log_id}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Get entity history
print("\n3. Testing entity history retrieval...")
try:
    history = auditor.get_entity_history("student", "TEST001")
    print(f"   ✅ Found {len(history)} audit records for TEST001")
    for record in history:
        print(f"      - {record['action']} at {record['timestamp']}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Test rollback preview
print("\n4. Testing rollback preview...")
try:
    result = auditor.rollback_to_log(log_id, execute=False)
    if result["success"]:
        print(f"   ✅ Rollback preview successful")
        print(f"      Would restore: {result.get('would_restore', {})}")
    else:
        print(f"   ❌ Rollback preview failed: {result.get('error')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ Part 2 Testing Complete!")
print("=" * 60)
