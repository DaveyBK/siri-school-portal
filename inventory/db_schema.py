"""
Database schema definitions and migration system.
Consolidates all table definitions in one place.
"""

import sqlite3
from pathlib import Path
from typing import List, Tuple, Callable
from datetime import datetime

CURRENT_SCHEMA_VERSION = 1
MIGRATIONS: List[Tuple[int, Callable[[sqlite3.Connection], None]]] = []

def migration(version: int):
    """Decorator to register migration functions"""
    def decorator(func: Callable[[sqlite3.Connection], None]):
        MIGRATIONS.append((version, func))
        return func
    return decorator

def create_students_table(conn: sqlite3.Connection):
    """Create students table with all constraints"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT,
            level TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            archived_at TEXT,
            CONSTRAINT valid_status CHECK (status IN ('active', 'inactive', 'archived'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_students_level ON students(level)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_students_status ON students(status)")

def create_items_table(conn: sqlite3.Connection):
    """Create items table with all constraints"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            item_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            description TEXT,
            quantity INTEGER DEFAULT 1,
            condition TEXT DEFAULT 'good',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            archived_at TEXT,
            CONSTRAINT valid_condition CHECK (condition IN ('excellent', 'good', 'fair', 'poor', 'damaged'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_items_condition ON items(condition)")

def create_assignments_table(conn: sqlite3.Connection):
    """Create assignments table with foreign key constraints"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            assigned_date TEXT DEFAULT (datetime('now')),
            returned_date TEXT,
            status TEXT DEFAULT 'assigned',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE,
            CONSTRAINT valid_status CHECK (status IN ('assigned', 'returned', 'lost', 'damaged'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_student ON assignments(student_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_item ON assignments(item_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_assignments_status ON assignments(status)")

def create_attendance_table(conn: sqlite3.Connection):
    """Create attendance table with constraints"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            session_date TEXT NOT NULL,
            status TEXT DEFAULT 'absent',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            CONSTRAINT valid_status CHECK (status IN ('present', 'absent', 'late', 'excused')),
            UNIQUE(student_id, session_date)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(session_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)")

def create_qr_scans_table(conn: sqlite3.Connection):
    """Create QR scans log table"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qr_scans (
            scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_code TEXT NOT NULL,
            student_id TEXT,
            item_id TEXT,
            scan_context TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE SET NULL,
            FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE SET NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_qr_scans_timestamp ON qr_scans(timestamp DESC)")

def create_admin_logs_table(conn: sqlite3.Connection):
    """Create admin action logs table"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now')),
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            details TEXT,
            old_data TEXT,
            new_data TEXT,
            status TEXT DEFAULT 'success',
            user_context TEXT,
            CONSTRAINT valid_status CHECK (status IN ('success', 'failed', 'pending'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_admin_logs_timestamp ON admin_logs(timestamp DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_admin_logs_entity ON admin_logs(entity_type, entity_id)")

def create_schema_version_table(conn: sqlite3.Connection):
    """Create table to track schema version"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        )
    """)

def get_current_version(conn: sqlite3.Connection) -> int:
    """Get current schema version from database"""
    try:
        cursor = conn.execute("SELECT MAX(version) FROM schema_version")
        result = cursor.fetchone()
        return result[0] if result[0] is not None else 0
    except sqlite3.OperationalError:
        return 0

def set_schema_version(conn: sqlite3.Connection, version: int, description: str = ""):
    """Record schema version in database"""
    conn.execute("INSERT INTO schema_version (version, description) VALUES (?, ?)", (version, description))

@migration(2)
def enhance_audit_logs_for_rollback(conn: sqlite3.Connection):
    """Add old_data and new_data columns to admin_logs for rollback support"""
    try:
        cursor = conn.execute("PRAGMA table_info(admin_logs)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'old_data' not in columns:
            conn.execute("ALTER TABLE admin_logs ADD COLUMN old_data TEXT")
            print("   Added old_data column to admin_logs")
        
        if 'new_data' not in columns:
            conn.execute("ALTER TABLE admin_logs ADD COLUMN new_data TEXT")
            print("   Added new_data column to admin_logs")
            
    except Exception as e:
        print(f"   Warning: Could not add columns: {e}")

def create_student_overrides_table(conn: sqlite3.Connection):
    """Create student_overrides table for planned absences and other time-bounded edits"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS student_overrides (
            override_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            scope_json TEXT,
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_student_overrides_student ON student_overrides(student_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_student_overrides_kind_dates ON student_overrides(kind, start_date, end_date)")


@migration(3)
def add_timestamp_columns_to_students(conn: sqlite3.Connection):
    """Add created_at, updated_at, and archived_at columns to students table"""
    try:
        cursor = conn.execute("PRAGMA table_info(students)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'created_at' not in columns:
            conn.execute("ALTER TABLE students ADD COLUMN created_at TEXT")
            print("   Added created_at column to students")

        if 'updated_at' not in columns:
            conn.execute("ALTER TABLE students ADD COLUMN updated_at TEXT")
            print("   Added updated_at column to students")

        if 'archived_at' not in columns:
            conn.execute("ALTER TABLE students ADD COLUMN archived_at TEXT")
            print("   Added archived_at column to students")

        # Set default values for existing records
        import datetime
        now = datetime.datetime.now().isoformat()
        conn.execute("UPDATE students SET created_at = ? WHERE created_at IS NULL", (now,))
        conn.execute("UPDATE students SET updated_at = ? WHERE updated_at IS NULL", (now,))
        print("   Set default timestamps for existing students")

    except Exception as e:
        print(f"   Warning: Could not add timestamp columns to students: {e}")


@migration(4)
def add_student_overrides_table(conn: sqlite3.Connection):
    """Add student_overrides table for planned absences and time-bounded edits"""
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='student_overrides'"
        )
        if cursor.fetchone():
            print("   student_overrides table already exists")
            return

        create_student_overrides_table(conn)
        print("   Created student_overrides table with indexes")

    except Exception as e:
        print(f"   Warning: Could not create student_overrides table: {e}")


@migration(5)
def add_class_roster_tables(conn: sqlite3.Connection):
    """Add class_def and class_roster tables for structured class rosters"""
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='class_def'"
        )
        if cursor.fetchone():
            print("   class_def table already exists")
        else:
            conn.execute("""
                CREATE TABLE class_def (
                    class_id TEXT PRIMARY KEY,
                    class_name TEXT NOT NULL,
                    day_of_week INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    level TEXT,
                    teacher TEXT DEFAULT 'David',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_class_def_day ON class_def(day_of_week)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_class_def_active ON class_def(is_active)")
            print("   Created class_def table with indexes")

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='class_roster'"
        )
        if cursor.fetchone():
            print("   class_roster table already exists")
        else:
            conn.execute("""
                CREATE TABLE class_roster (
                    roster_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    enrolled_at TEXT DEFAULT (datetime('now')),
                    removed_at TEXT,
                    FOREIGN KEY (class_id) REFERENCES class_def(class_id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    UNIQUE(class_id, student_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_class_roster_class ON class_roster(class_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_class_roster_student ON class_roster(student_id)")
            print("   Created class_roster table with indexes")

    except Exception as e:
        print(f"   Warning: Could not create class roster tables: {e}")


@migration(6)
def add_parent_line_id_to_students(conn: sqlite3.Connection):
    """Add parent_line_id column to students table for LINE messaging"""
    try:
        cursor = conn.execute("PRAGMA table_info(students)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'parent_line_id' not in columns:
            conn.execute("ALTER TABLE students ADD COLUMN parent_line_id TEXT")
            print("   Added parent_line_id column to students")
        else:
            print("   parent_line_id column already exists")

    except Exception as e:
        print(f"   Warning: Could not add parent_line_id column: {e}")


@migration(7)
def add_extra_lesson_tables(conn: sqlite3.Connection):
    """Add extra_lesson and extra_lesson_student tables for one-off lessons"""
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='extra_lesson'"
        )
        if cursor.fetchone():
            print("   extra_lesson table already exists")
        else:
            conn.execute("""
                CREATE TABLE extra_lesson (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    lesson_date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    level TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_extra_lesson_date ON extra_lesson(lesson_date)")
            print("   Created extra_lesson table with indexes")

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='extra_lesson_student'"
        )
        if cursor.fetchone():
            print("   extra_lesson_student table already exists")
        else:
            conn.execute("""
                CREATE TABLE extra_lesson_student (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extra_lesson_id INTEGER NOT NULL,
                    student_id TEXT NOT NULL,
                    FOREIGN KEY (extra_lesson_id) REFERENCES extra_lesson(id) ON DELETE CASCADE,
                    FOREIGN KEY (student_id) REFERENCES students(student_id),
                    UNIQUE(extra_lesson_id, student_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_extra_lesson_student_lesson ON extra_lesson_student(extra_lesson_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_extra_lesson_student_student ON extra_lesson_student(student_id)")
            print("   Created extra_lesson_student table with indexes")

    except Exception as e:
        print(f"   Warning: Could not create extra lesson tables: {e}")


@migration(8)
def add_class_cancellations_table(conn: sqlite3.Connection):
    """Add class_cancellations table for temporary class cancellations"""
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='class_cancellations'"
        )
        if cursor.fetchone():
            print("   class_cancellations table already exists")
            return

        conn.execute("""
            CREATE TABLE class_cancellations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id TEXT NOT NULL,
                cancel_start DATE NOT NULL,
                cancel_end DATE NOT NULL,
                reason TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (class_id) REFERENCES class_def(class_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_class_cancel_class ON class_cancellations(class_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_class_cancel_dates ON class_cancellations(cancel_start, cancel_end)")
        print("   Created class_cancellations table with indexes")

    except Exception as e:
        print(f"   Warning: Could not create class_cancellations table: {e}")


CLASS_LEVEL_SEED = [
    ("SM1", "Supermind 1", "Supermind"),
    ("SM2", "Supermind 2", "Supermind"),
    ("SM3", "Supermind 3", "Supermind"),
    ("SM4", "Supermind 4", "Supermind"),
    ("SM5", "Supermind 5", "Supermind"),
    ("SM6", "Supermind 6", "Supermind"),
    ("OP1", "Oxford Phonics 1", "Oxford Phonics"),
    ("OP2", "Oxford Phonics 2", "Oxford Phonics"),
    ("OP3", "Oxford Phonics 3", "Oxford Phonics"),
    ("OP4", "Oxford Phonics 4", "Oxford Phonics"),
    ("EF-ELEM", "English File Elementary", "English File"),
    ("EF-PRE", "English File Pre-Intermediate", "English File"),
    ("EF-INT", "English File Intermediate", "English File"),
    ("EF-INTP", "English File Intermediate Plus", "English File"),
    ("IELTS-A", "IELTS Academic", "IELTS"),
    ("IELTS-G", "IELTS General", "IELTS"),
]


@migration(9)
def add_class_level_table(conn: sqlite3.Connection):
    """Add class_level lookup table seeded with the course levels"""
    # Unlike earlier migrations, errors propagate so a failure is never recorded as applied.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS class_level (
            level_code TEXT PRIMARY KEY,
            level_name TEXT NOT NULL,
            series TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.executemany(
        "INSERT OR IGNORE INTO class_level (level_code, level_name, series, sort_order) VALUES (?, ?, ?, ?)",
        [(code, name, series, i) for i, (code, name, series) in enumerate(CLASS_LEVEL_SEED, start=1)],
    )
    print("   Created class_level table and seeded levels")


@migration(10)
def add_standalone_class_levels(conn: sqlite3.Connection):
    """Add Writing, Reading and Pre-school standalone class types to class_level"""
    conn.executemany(
        "INSERT OR IGNORE INTO class_level (level_code, level_name, series, sort_order) VALUES (?, ?, ?, ?)",
        [
            ("WRITE", "Writing", "Writing", 17),
            ("READ", "Reading", "Reading", 18),
            ("PRE", "Pre-school", "Pre-school", 19),
        ],
    )
    print("   Added standalone class levels")


def init_database(db_path: Path) -> sqlite3.Connection:
    """Initialize database with full schema"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    
    create_schema_version_table(conn)
    current_version = get_current_version(conn)
    
    if current_version == 0:
        create_students_table(conn)
        create_items_table(conn)
        create_assignments_table(conn)
        create_attendance_table(conn)
        create_qr_scans_table(conn)
        create_admin_logs_table(conn)
        create_student_overrides_table(conn)
        set_schema_version(conn, 1, "Initial schema creation")
        conn.commit()
    
    apply_migrations(conn, current_version)
    return conn

def apply_migrations(conn: sqlite3.Connection, from_version: int):
    """Apply all migrations newer than from_version"""
    sorted_migrations = sorted(MIGRATIONS, key=lambda x: x[0])
    for version, migration_func in sorted_migrations:
        if version > from_version:
            print(f"Applying migration to version {version}...")
            try:
                migration_func(conn)
                set_schema_version(conn, version, migration_func.__doc__ or "Migration")
                conn.commit()
                print(f"✓ Migration {version} completed")
            except Exception as e:
                conn.rollback()
                print(f"✗ Migration {version} failed: {e}")
                raise

def get_schema_info(conn: sqlite3.Connection) -> dict:
    """Get information about current schema"""
    version = get_current_version(conn)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    return {"version": version, "tables": tables, "migrations_available": len(MIGRATIONS), "timestamp": datetime.now().isoformat()}

def export_schema(conn: sqlite3.Connection) -> str:
    """Export current schema as SQL"""
    cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%' ORDER BY type DESC, name")
    sql_statements = [row[0] for row in cursor.fetchall() if row[0]]
    return ";\n\n".join(sql_statements) + ";"