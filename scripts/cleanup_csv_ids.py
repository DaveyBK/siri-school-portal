import csv
from pathlib import Path

imports_dir = Path("imports")
student_id_files = sorted(imports_dir.glob("Student ID_*.csv"))

print(f"Found {len(student_id_files)} student ID CSV files")
print("\nRemoving .0 from all student IDs:\n")

for csv_file in student_id_files:
    print(f"Processing: {csv_file.name}")
    
    # Read the CSV
    rows = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows.append(header)
        
        for row in reader:
            if row and row[0]:  # If first column (Student ID) exists
                # Remove .0 from student ID
                if row[0].endswith('.0'):
                    row[0] = row[0][:-2]
            rows.append(row)
    
    # Write back
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"  ✓ Updated")

print("\nAll files updated!")
