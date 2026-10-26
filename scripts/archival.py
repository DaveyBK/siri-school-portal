"""
Archival system for soft deletes and data recovery.
Provides safe deletion with rollback capability.
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from inventory.audit import AuditLogger


class ArchivalManager:
    """
    Manages soft deletes and data recovery.
    Supports archiving students, items, and related records.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.auditor = AuditLogger(db_path)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    # ============= STUDENT ARCHIVAL =============
    
    def archive_student(self, student_id: str, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Archive a student (soft delete).
        Updates status to 'archived' and sets archived_at timestamp.
        """
        conn = self.get_connection()
        try:
            # Get current student data
            cursor = conn.execute(
                "SELECT * FROM students WHERE student_id = ? AND status != 'archived'",
                (student_id,)
            )
            student = cursor.fetchone()
            
            if not student:
                return {"success": False, "error": "Student not found or already archived"}
            
            old_data = dict(student)
            
            # Archive the student
            conn.execute("""
                UPDATE students 
                SET status = 'archived', 
                    archived_at = datetime('now'),
                    updated_at = datetime('now')
                WHERE student_id = ?
            """, (student_id,))
            
            # Log the archival
            self.auditor.log_action(
                action="archive_student",
                entity_type="student",
                entity_id=student_id,
                details={"message": f"Archived student {student_id}"},
                old_data=old_data,
                new_data={"status": "archived"},
                user_context=user,
                conn=conn
            )
            
            conn.commit()
            return {"success": True, "student_id": student_id, "action": "archived"}
            
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def restore_student(self, student_id: str, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Restore an archived student.
        Sets status back to 'active' and clears archived_at.
        """
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM students WHERE student_id = ? AND status = 'archived'",
                (student_id,)
            )
            student = cursor.fetchone()
            
            if not student:
                return {"success": False, "error": "Student not found or not archived"}
            
            old_data = dict(student)
            
            conn.execute("""
                UPDATE students 
                SET status = 'active', 
                    archived_at = NULL,
                    updated_at = datetime('now')
                WHERE student_id = ?
            """, (student_id,))
            
            self.auditor.log_action(
                action="restore_student",
                entity_type="student",
                entity_id=student_id,
                details={"message": f"Restored student {student_id}"},
                old_data=old_data,
                new_data={"status": "active"},
                user_context=user,
                conn=conn
            )
            
            conn.commit()
            return {"success": True, "student_id": student_id, "action": "restored"}
            
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def hard_delete_student(self, student_id: str, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Permanently delete a student and all related records.
        Uses CASCADE to delete assignments, attendance, and QR scans.
        """
        conn = self.get_connection()
        try:
            # Get student data before deletion
            cursor = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
            student = cursor.fetchone()
            
            if not student:
                return {"success": False, "error": "Student not found"}
            
            # Get related record counts
            cursor = conn.execute("SELECT COUNT(*) FROM assignments WHERE student_id = ?", (student_id,))
            assignment_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ?", (student_id,))
            attendance_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM qr_scans WHERE student_id = ?", (student_id,))
            scan_count = cursor.fetchone()[0]
            
            # Log before deletion (for potential recovery)
            self.auditor.log_action(
                action="hard_delete_student",
                entity_type="student",
                entity_id=student_id,
                details={
                    "message": f"Hard deleted student {student_id}",
                    "assignments_deleted": assignment_count,
                    "attendance_deleted": attendance_count,
                    "scans_deleted": scan_count
                },
                old_data=dict(student),
                user_context=user,
                conn=conn
            )
            
            # Delete student (CASCADE will handle related records)
            conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
            
            conn.commit()
            return {
                "success": True,
                "student_id": student_id,
                "action": "hard_deleted",
                "related_records": {
                    "assignments": assignment_count,
                    "attendance": attendance_count,
                    "qr_scans": scan_count
                }
            }
            
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    # ============= ITEM ARCHIVAL =============
    
    def archive_item(self, item_id: str, user: Optional[str] = None) -> Dict[str, Any]:
        """Archive an item (soft delete)"""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM items WHERE item_id = ?",
                (item_id,)
            )
            item = cursor.fetchone()
            
            if not item:
                return {"success": False, "error": "Item not found"}
            
            old_data = dict(item)
            
            # Check for active assignments
            cursor = conn.execute(
                "SELECT COUNT(*) FROM assignments WHERE item_id = ? AND status = 'assigned'",
                (item_id,)
            )
            active_assignments = cursor.fetchone()[0]
            
            if active_assignments > 0:
                return {
                    "success": False,
                    "error": f"Cannot archive item with {active_assignments} active assignments"
                }
            
            conn.execute("""
                UPDATE items 
                SET archived_at = datetime('now'),
                    updated_at = datetime('now')
                WHERE item_id = ?
            """, (item_id,))
            
            self.auditor.log_action(
                action="archive_item",
                entity_type="item",
                entity_id=item_id,
                details={"message": f"Archived item {item_id}"},
                old_data=old_data,
                user_context=user,
                conn=conn
            )
            
            conn.commit()
            return {"success": True, "item_id": item_id, "action": "archived"}
            
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    # ============= QUERY FUNCTIONS =============
    
    def get_archived_students(self) -> List[Dict[str, Any]]:
        """Get all archived students"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM students 
                WHERE status = 'archived'
                ORDER BY archived_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_archived_items(self) -> List[Dict[str, Any]]:
        """Get all archived items"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM items 
                WHERE archived_at IS NOT NULL
                ORDER BY archived_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def cleanup_orphaned_records(self) -> Dict[str, int]:
        """
        Clean up orphaned records (shouldn't exist with CASCADE, but safety check).
        Returns count of cleaned records.
        """
        conn = self.get_connection()
        try:
            # Find assignments without valid students or items
            cursor = conn.execute("""
                SELECT COUNT(*) FROM assignments
                WHERE student_id NOT IN (SELECT student_id FROM students)
                OR item_id NOT IN (SELECT item_id FROM items)
            """)
            orphaned_assignments = cursor.fetchone()[0]
            
            # Find attendance without valid students
            cursor = conn.execute("""
                SELECT COUNT(*) FROM attendance
                WHERE student_id NOT IN (SELECT student_id FROM students)
            """)
            orphaned_attendance = cursor.fetchone()[0]
            
            return {
                "orphaned_assignments": orphaned_assignments,
                "orphaned_attendance": orphaned_attendance
            }
        finally:
            conn.close()
