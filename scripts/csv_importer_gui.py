"""
CSV Importer GUI - Student Data Import Tool
Drag & drop CSV files, preview, and import to database
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import inventory module
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import json
import os
import sqlite3
from datetime import datetime

class CSVImporterGUI:
    def __init__(self, root, models=None, callback=None):
        # Validate root window
        if not root:
            raise ValueError("root window cannot be None")
        
        self.root = root
        self.models = models  # Database models module (optional)
        self.callback = callback  # Callback function after import (optional)
        
        # Data storage
        self.csv_files = []
        self.combined_df = None
        self.sort_column = None
        self.sort_reverse = False
        
        # Column mapping (customize based on your needs)
        self.column_mapping = {
            'Student ID': 'student_id',
            'Name': 'name',
            'Age': 'age',
            'Phone': 'phone',
            'Schoolwork Place': 'location',
            'Source': 'source',
            'Level Check': 'level',
            'Start Date': 'start_date',
            'Note': 'notes',
            'Parent LINE ID': 'parent_line_id',
            'LINE ID': 'parent_line_id'
        }
        
        # Initialize UI
        try:
            self.setup_ui()
        except Exception as e:
            import traceback
            print(f"Error in setup_ui: {e}")
            print(traceback.format_exc())
            raise
        
    def setup_ui(self):
        """Create the user interface"""
        
        # Title
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="📊 Student Data Importer",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=15)
        
        # Main container
        main_frame = tk.Frame(self.root, bg="#ecf0f1")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel - File list
        left_frame = tk.Frame(main_frame, bg="white", relief="solid", borderwidth=1)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # File list header
        file_header = tk.Label(
            left_frame,
            text="CSV Files to Import",
            font=("Arial", 12, "bold"),
            bg="white",
            anchor="w"
        )
        file_header.pack(fill="x", padx=10, pady=(10, 5))
        
        # File listbox with scrollbar
        list_frame = tk.Frame(left_frame, bg="white")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.file_listbox = tk.Listbox(
            list_frame,
            font=("Arial", 10),
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE
        )
        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # File buttons
        btn_frame = tk.Frame(left_frame, bg="white")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        add_btn = tk.Button(
            btn_frame,
            text="➕ Add CSV Files",
            command=self.add_files,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            relief="flat",
            padx=20,
            pady=8
        )
        add_btn.pack(side="left", padx=2)
        
        remove_btn = tk.Button(
            btn_frame,
            text="➖ Remove Selected",
            command=self.remove_file,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            relief="flat",
            padx=20,
            pady=8
        )
        remove_btn.pack(side="left", padx=2)
        
        clear_btn = tk.Button(
            btn_frame,
            text="🗑️ Clear All",
            command=self.clear_files,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            relief="flat",
            padx=20,
            pady=8
        )
        clear_btn.pack(side="left", padx=2)
        
        # Right panel - Preview and options
        right_frame = tk.Frame(main_frame, bg="white", relief="solid", borderwidth=1)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # Preview header
        preview_header = tk.Label(
            right_frame,
            text="Data Preview",
            font=("Arial", 12, "bold"),
            bg="white",
            anchor="w"
        )
        preview_header.pack(fill="x", padx=10, pady=(10, 5))
        
        # Preview frame with treeview
        preview_frame = tk.Frame(right_frame, bg="white")
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Scrollbars for preview
        preview_scroll_y = tk.Scrollbar(preview_frame)
        preview_scroll_y.pack(side="right", fill="y")
        
        preview_scroll_x = tk.Scrollbar(preview_frame, orient="horizontal")
        preview_scroll_x.pack(side="bottom", fill="x")
        
        self.preview_tree = ttk.Treeview(
            preview_frame,
            yscrollcommand=preview_scroll_y.set,
            xscrollcommand=preview_scroll_x.set,
            height=10
        )
        self.preview_tree.pack(fill="both", expand=True)
        
        preview_scroll_y.config(command=self.preview_tree.yview)
        preview_scroll_x.config(command=self.preview_tree.xview)
        
        # Statistics label
        self.stats_label = tk.Label(
            right_frame,
            text="No data loaded",
            font=("Arial", 9),
            bg="white",
            fg="#7f8c8d",
            anchor="w"
        )
        self.stats_label.pack(fill="x", padx=10, pady=5)
        
        # Bottom action panel
        action_frame = tk.Frame(self.root, bg="#ecf0f1")
        action_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Options frame
        options_frame = tk.Frame(action_frame, bg="white", relief="solid", borderwidth=1)
        options_frame.pack(fill="x", pady=(0, 5))
        
        tk.Label(
            options_frame,
            text="Import Options:",
            font=("Arial", 10, "bold"),
            bg="white"
        ).pack(side="left", padx=10, pady=10)
        
        self.remove_duplicates_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Remove duplicate Student IDs",
            variable=self.remove_duplicates_var,
            bg="white",
            font=("Arial", 9)
        ).pack(side="left", padx=5)
        
        self.save_json_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Save as JSON",
            variable=self.save_json_var,
            bg="white",
            font=("Arial", 9)
        ).pack(side="left", padx=5)
        
        self.save_db_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Save as SQLite DB",
            variable=self.save_db_var,
            bg="white",
            font=("Arial", 9)
        ).pack(side="left", padx=5)
        
        self.save_excel_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            options_frame,
            text="Save as Excel",
            variable=self.save_excel_var,
            bg="white",
            font=("Arial", 9)
        ).pack(side="left", padx=5)
        
        # Action buttons
        button_frame = tk.Frame(action_frame, bg="white", relief="solid", borderwidth=1)
        button_frame.pack(fill="x")
        
        preview_btn = tk.Button(
            button_frame,
            text="👁️ Preview Data",
            command=self.preview_data,
            bg="#9b59b6",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            relief="flat",
            padx=30,
            pady=12
        )
        preview_btn.pack(side="left", padx=10, pady=10)
        
        import_btn = tk.Button(
            button_frame,
            text="✅ Import Data",
            command=self.import_data,
            bg="#27ae60",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            relief="flat",
            padx=30,
            pady=12
        )
        import_btn.pack(side="left", padx=10, pady=10)
        
        # Status bar
        self.status_bar = tk.Label(
            self.root,
            text="Ready to import CSV files",
            bg="#34495e",
            fg="white",
            anchor="w",
            font=("Arial", 9),
            padx=10,
            pady=5
        )
        self.status_bar.pack(side="bottom", fill="x")
    
    def add_files(self):
        """Add CSV files to the list"""
        files = filedialog.askopenfilenames(
            title="Select CSV Files",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        
        for file in files:
            if file not in self.csv_files:
                self.csv_files.append(file)
                filename = os.path.basename(file)
                self.file_listbox.insert(tk.END, filename)
        
        self.update_status(f"Added {len(files)} file(s)")
    
    def remove_file(self):
        """Remove selected file from list"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            self.file_listbox.delete(index)
            del self.csv_files[index]
            self.update_status("File removed")
    
    def clear_files(self):
        """Clear all files from list"""
        self.file_listbox.delete(0, tk.END)
        self.csv_files = []
        self.combined_df = None
        self.clear_preview()
        self.update_status("All files cleared")
    
    def preview_data(self):
        """Preview the combined data"""
        if not self.csv_files:
            messagebox.showwarning("No Files", "Please add CSV files first!")
            return
        
        self.update_status("Loading and combining CSV files...")
        self.root.update()
        
        try:
            # Read and combine all CSV files
            all_data = []
            for file in self.csv_files:
                try:
                    # Try different encodings. Every cell is read as text, as typed: pandas would turn a number such as
                    # 12345 into 12345.0 (and drop the 0 of a phone number), and "NA" into an empty cell.
                    keep_text = dict(dtype=str, keep_default_na=False)
                    try:
                        df = pd.read_csv(file, encoding='utf-8-sig', **keep_text)
                    except UnicodeDecodeError:
                        try:
                            df = pd.read_csv(file, encoding='utf-8', **keep_text)
                        except UnicodeDecodeError:
                            df = pd.read_csv(file, encoding='latin1', **keep_text)
                    
                    df['source_file'] = os.path.basename(file)
                    all_data.append(df)
                except Exception as e:
                    messagebox.showwarning(
                        "File Error", 
                        f"Could not read {os.path.basename(file)}:\n{str(e)}"
                    )
                    continue
            
            if not all_data:
                messagebox.showerror("Error", "No valid CSV files could be read!")
                self.update_status("Failed to load files")
                return
            
            self.combined_df = pd.concat(all_data, ignore_index=True)
            
            # Remove duplicates if option selected
            if self.remove_duplicates_var.get() and 'Student ID' in self.combined_df.columns:
                before = len(self.combined_df)
                self.combined_df = self.combined_df.drop_duplicates(subset=['Student ID'], keep='last')
                removed = before - len(self.combined_df)
                if removed > 0:
                    self.update_status(f"Removed {removed} duplicate entries")
            
            # Display preview
            self.display_preview(self.combined_df)
            self.update_status(f"Preview loaded: {len(self.combined_df)} records")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV files:\n{str(e)}")
            self.update_status("Error loading files")
    
    def display_preview(self, df):
        """Display data in the preview tree"""
        self.clear_preview()
        
        # Setup columns (limit to first 15 for preview)
        columns = list(df.columns)[:15]
        self.preview_tree["columns"] = columns
        self.preview_tree["show"] = "headings"
        
        # Setup column headings with appropriate widths and click handlers
        for col in columns:
            # Adjust width based on column content
            max_len = max(
                len(str(col)),
                df[col].astype(str).str.len().max() if len(df) > 0 else 0
            )
            width = min(max(max_len * 7, 80), 200)  # 7px per char, min 80, max 200
            
            # Make header clickable for sorting
            self.preview_tree.heading(col, text=col, command=lambda c=col: self.sort_column_data(c))
            self.preview_tree.column(col, width=width)
        
        # Insert data (first 100 rows for preview)
        for idx, row in df.head(100).iterrows():
            values = [str(row[col]) if col in row.index else "" for col in columns]
            self.preview_tree.insert("", "end", values=values)
        
        # Update statistics
        if len(columns) < len(df.columns):
            extra_cols = len(df.columns) - len(columns)
            stats = f"Total Records: {len(df)} | Columns: {len(df.columns)} (showing first {len(columns)}) | Showing first 100 rows"
        else:
            stats = f"Total Records: {len(df)} | Columns: {len(df.columns)} | Showing first 100 rows"
        self.stats_label.config(text=stats)
    
    def clear_preview(self):
        """Clear the preview tree"""
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        self.preview_tree["columns"] = []
        self.stats_label.config(text="No data loaded")
    
    def sort_column_data(self, column):
        """Sort preview data by column alphabetically"""
        if self.combined_df is None:
            return
        
        # Check if this column is already sorted in this direction
        if self.sort_column == column:
            # Toggle sort direction
            self.sort_reverse = not self.sort_reverse
        else:
            # New column selected, sort ascending
            self.sort_reverse = False
        
        # Store current sort state
        self.sort_column = column
        
        # Sort dataframe
        sorted_df = self.combined_df.sort_values(by=column, ascending=not self.sort_reverse, na_position='last')
        
        # Refresh display with sorted data
        self.display_preview(sorted_df)
    
    def import_data(self):
        """Import data to database"""
        if self.combined_df is None:
            messagebox.showwarning("No Data", "Please preview data first!")
            return
        
        # If we have models module, ask if user wants direct import
        if self.models and self.callback:
            result = messagebox.askyesno(
                "Import Destination",
                "Import directly to the current application database?\n\n"
                "Yes = Import to current app\nNo = Save to files only"
            )
            if result:
                self.import_to_database()
                return
        
        # Otherwise, ask for output directory
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return
        
        self.save_to_files(output_dir)
    
    def import_to_database(self):
        """Import data directly to the application database"""
        try:
            self.update_status("Importing to database...")
            self.root.update()
            
            df = self.combined_df.copy()
            
            # Both headings map to parent_line_id: two columns of that name would refuse every row. Refuse the file.
            if 'Parent LINE ID' in df.columns and 'LINE ID' in df.columns:
                messagebox.showerror(
                    "Import refused",
                    "This file has both a 'Parent LINE ID' and a 'LINE ID' column. Keep one of them and import again. "
                    "Nothing was imported.")
                self.update_status("Import refused - two LINE ID columns")
                return
            
            # Rename columns to match database schema
            df = df.rename(columns=self.column_mapping)
            df = df.fillna('')
            
            # Validate required fields
            if 'student_id' not in df.columns:
                messagebox.showerror("Error", "Student ID column not found in CSV!")
                self.update_status("Import failed - missing Student ID")
                return
            
            # Import student records using models module
            imported_count = 0
            blank_count = 0      # rows with no student ID
            refused_count = 0    # rows refused with a message (in errors)
            errors = []
            extra_details = {}  # Store additional details separately
            
            for idx, row in df.iterrows():
                try:
                    # Extract values from row
                    student_id = str(row.get('student_id', '')).strip()
                    if not student_id:
                        blank_count += 1
                        continue
                    
                    # Split name into first and last if needed
                    name = str(row.get('name', '')).strip()
                    if ' ' in name:
                        parts = name.split(' ', 1)
                        first_name = parts[0]
                        last_name = parts[1]
                    else:
                        first_name = name
                        last_name = ''
                    
                    level = str(row.get('level', '')).strip()

                    # An empty cell (no column, or nothing in it) keeps what is stored: a single-word name keeps the stored
                    # last name, an empty Name keeps the first name, an empty Level keeps the level (update_student does
                    # the keeping, so an import never blanks stored data).
                    # Parent LINE ID: no column or an empty cell keeps the stored one (an import never blanks it);
                    # a value must have the LINE user ID shape, or this row is refused with a message.
                    line_id = str(row.get('parent_line_id', '')).strip() or None
                    if line_id:
                        from inventory.validation import validate_line_id
                        valid, line_error = validate_line_id(line_id)
                        if not valid:
                            raise ValueError(f"{student_id}: the parent LINE ID ending …{line_id[-4:]} was refused and "
                                             f"the row was not imported. {line_error}")

                    # Check if student already exists
                    existing = self.models.get_student(student_id)
                    
                    if existing:
                        # Update existing student
                        self.models.update_student(
                            student_id=student_id,
                            first_name=first_name,
                            last_name=last_name,
                            level=level,
                            parent_line_id=line_id
                        )
                    else:
                        # Insert new student
                        self.models.add_student(
                            student_id=student_id,
                            first_name=first_name,
                            last_name=last_name,
                            level=level,
                            parent_line_id=line_id
                        )
                    
                    # Store extra details for separate file
                    extra_details[student_id] = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'level': level,
                        'age': str(row.get('age', '')).strip(),
                        'phone': str(row.get('phone', '')).strip(),
                        'location': str(row.get('location', '')).strip(),
                        'source': str(row.get('source', '')).strip(),
                        'start_date': str(row.get('start_date', '')).strip(),
                        'notes': str(row.get('notes', '')).strip()
                    }
                    
                    imported_count += 1
                    
                except Exception as e:
                    refused_count += 1
                    errors.append(f"Row {idx + 2}: {str(e)}")
            
            # Save extra details to JSON file in data directory
            details_saved = False
            if extra_details:
                try:
                    data_dir = Path(__file__).resolve().parent.parent / "data"
                    data_dir.mkdir(exist_ok=True)
                    details_file = data_dir / "student_details.json"
                    
                    # Load existing details if file exists
                    if details_file.exists():
                        with open(details_file, 'r', encoding='utf-8') as f:
                            existing_details = json.load(f)
                    else:
                        existing_details = {}
                    
                    # Merge new details: an empty cell keeps the detail already stored, like the database fields
                    for sid, new_values in extra_details.items():
                        merged = dict(existing_details.get(sid) or {})
                        merged.update({k: v for k, v in new_values.items() if v})
                        existing_details[sid] = merged
                    
                    # Save updated details
                    with open(details_file, 'w', encoding='utf-8') as f:
                        json.dump(existing_details, f, indent=2, ensure_ascii=False)
                    details_saved = True
                except Exception as e:
                    errors.append(f"Could not save details file: {str(e)}")
            
            # Show summary: the heading says how it went; blank and refused rows are counted apart
            if imported_count == 0:
                msg = "❌ Nothing was imported\n\n"
            elif errors:
                msg = "⚠️ Import finished with problems\n\n"
            else:
                msg = "✅ Import Complete!\n\n"
            msg += f"Records imported: {imported_count}\n"
            msg += f"Rows refused: {refused_count}\n"
            msg += f"Blank rows skipped (no student ID): {blank_count}\n"
            if details_saved:
                msg += f"\nExtra details saved to: data/student_details.json"
            
            if errors:
                msg += f"\n\nErrors encountered: {len(errors)}\n"
                msg += "\nFirst few errors:\n"
                msg += "\n".join(errors[:5])
                if len(errors) > 5:
                    msg += f"\n... and {len(errors) - 5} more"
            
            messagebox.showinfo("Import Summary", msg)
            self.update_status(f"Import complete: {imported_count} records saved")
            
            # Call callback to refresh main window if provided
            if self.callback:
                try:
                    self.callback()
                except Exception as e:
                    print(f"Callback error: {e}")
            
            # Close the window after successful import
            self.root.after(500, self.root.destroy)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import data:\n{str(e)}")
            self.update_status("Import failed")
    
    def save_to_files(self, output_dir):
        """Save data to JSON, SQLite, and/or Excel files"""
        try:
            self.update_status("Saving files...")
            self.root.update()
            
            df = self.combined_df.copy()
            df = df.rename(columns=self.column_mapping)
            df = df.fillna('')
            
            saved_files = []
            
            # Save as JSON
            if self.save_json_var.get():
                json_path = os.path.join(output_dir, 'students.json')
                records = df.to_dict('records')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(records, f, indent=2, ensure_ascii=False)
                saved_files.append('students.json')
            
            # Save as SQLite
            if self.save_db_var.get():
                db_path = os.path.join(output_dir, 'students.db')
                conn = sqlite3.connect(db_path)
                df.to_sql('students', conn, if_exists='replace', index=False)
                conn.close()
                saved_files.append('students.db')
            
            # Save as Excel
            if self.save_excel_var.get():
                excel_path = os.path.join(output_dir, 'students.xlsx')
                df.to_excel(excel_path, index=False, engine='openpyxl')
                saved_files.append('students.xlsx')
            
            # Success message
            msg = f"✅ Export Complete!\n\n"
            msg += f"Records saved: {len(df)}\n"
            msg += f"Output directory: {output_dir}\n\n"
            msg += f"Files created:\n" + "\n".join(f"• {f}" for f in saved_files)
            
            messagebox.showinfo("Success", msg)
            self.update_status(f"Export complete: {len(df)} records saved")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data:\n{str(e)}")
            self.update_status("Export failed")
    
    def update_status(self, message):
        """Update status bar"""
        self.status_bar.config(text=message)
        self.root.update()


def main():
    root = tk.Tk()
    app = CSVImporterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("="*60)
        print("ERROR OCCURRED:")
        print("="*60)
        traceback.print_exc()
        print("="*60)
        input("\nPress Enter to exit...")
        