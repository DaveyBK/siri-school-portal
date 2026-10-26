from inventory import models
from inventory.db import get_connection

# Get all students
students = models.list_students()

print(f"Found {len(students)} students")
print("\nUpdating student IDs (removing .0):")

updated_count = 0
for student in students:
    old_id = student['student_id']
    if old_id.endswith('.0'):
        new_id = old_id[:-2]  # Remove the .0
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('UPDATE students SET student_id = ? WHERE student_id = ?', (new_id, old_id))
            conn.commit()
            conn.close()
            print(f"  {old_id} -> {new_id}")
            updated_count += 1
        except Exception as e:
            print(f"  ERROR: {old_id} -> {new_id}: {e}")

print(f"\nTotal updated: {updated_count}")
print("Done!")
