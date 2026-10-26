"""
Comprehensive audit logging system with rollback capability.
Tracks all changes to critical entities with full context.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from contextlib import contextmanager


class AuditLogger:
    """
    Centralized audit logging with transaction support.
    Logs all changes to students, items, assignments, and attendance.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions with automatic rollback on error"""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def log_action(self, 
                   action: str,
                   entity_type: str,
                   entity_id: str,
                   details: Dict[str, Any],
                   old_data: Optional[Dict[str, Any]] = None,
                   new_data: Optional[Dict[str, Any]] = None,
                   user_context: Optional[str] = None,
                   conn: Optional[sqlite3.Connection] = None) -> int:
        """Log an action with full context for potential rollback"""
        should_close = False
        if conn is None:
            conn = self.get_connection()
            should_close = True
        
        try:
            cursor = conn.execute("""
                INSERT INTO admin_logs (
                    timestamp, action, entity_type, entity_id,
                    details, old_data, new_data, user_context, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'success')
            """, (
                datetime.now().isoformat(),
                action,
                entity_type,
                entity_id,
                json.dumps(details) if isinstance(details, dict) else str(details),
                json.dumps(old_data) if old_data else None,
                json.dumps(new_data) if new_data else None,
                user_context or "system"
            ))
            
            log_id = cursor.lastrowid
            
            if should_close:
                conn.commit()
            
            return log_id
            
        finally:
            if should_close:
                conn.close()
    
    def log_student_create(self, student_id: str, data: Dict[str, Any], 
                          user: Optional[str] = None, conn: Optional[sqlite3.Connection] = None):
        """Log student creation"""
        return self.log_action(
            action="create_student",
            entity_type="student",
            entity_id=student_id,
            details={"message": f"Created student {student_id}"},
            new_data=data,
            user_context=user,
            conn=conn
        )
    
    def log_student_update(self, student_id: str, old_data: Dict[str, Any], 
                          new_data: Dict[str, Any], user: Optional[str] = None,
                          conn: Optional[sqlite3.Connection] = None):
        """Log student update"""
        changes = self._get_changes(old_data, new_data)
        return self.log_action(
            action="update_student",
            entity_type="student",
            entity_id=student_id,
            details={"message": f"Updated student {student_id}", "changes": changes},
            old_data=old_data,
            new_data=new_data,
            user_context=user,
            conn=conn
        )
    
    def log_student_delete(self, student_id: str, data: Dict[str, Any],
                          user: Optional[str] = None, conn: Optional[sqlite3.Connection] = None):
        """Log student deletion"""
        return self.log_action(
            action="delete_student",
            entity_type="student",
            entity_id=student_id,
            details={"message": f"Deleted student {student_id}"},
            old_data=data,
            user_context=user,
            conn=conn
        )
    
    def _get_changes(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get dictionary of changed fields"""
        changes = {}
        all_keys = set(old_data.keys()) | set(new_data.keys())
        
        for key in all_keys:
            old_val = old_data.get(key)
            new_val = new_data.get(key)
            
            if old_val != new_val:
                changes[key] = {"old": old_val, "new": new_val}
        
        return changes
    
    def get_entity_history(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """Get full audit history for an entity"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM admin_logs
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY timestamp DESC
            """, (entity_type, entity_id))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def rollback_to_log(self, log_id: int, execute: bool = False) -> Dict[str, Any]:
        """Rollback an entity to a previous state based on audit log"""
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM admin_logs WHERE log_id = ?", (log_id,))
            log = cursor.fetchone()
            
            if not log:
                return {"success": False, "error": "Log entry not found"}
            
            log_dict = dict(log)
            old_data = json.loads(log_dict["old_data"]) if log_dict["old_data"] else None
            
            if not old_data:
                return {"success": False, "error": "No rollback data available"}
            
            if execute:
                entity_type = log_dict["entity_type"]
                entity_id = log_dict["entity_id"]
                
                if entity_type == "student":
                    self._rollback_student(entity_id, old_data, conn)
                
                self.log_action(
                    action="rollback",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    details={"message": f"Rolled back to log {log_id}"},
                    new_data=old_data,
                    user_context="system_rollback",
                    conn=conn
                )
                
                conn.commit()
                return {"success": True, "action": "rolled_back"}
            else:
                return {"success": True, "action": "preview", "would_restore": old_data}
                
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def _rollback_student(self, student_id: str, old_data: Dict, conn: sqlite3.Connection):
        """Rollback student to previous state"""
        conn.execute("""
            UPDATE students
            SET first_name = ?, last_name = ?, level = ?, status = ?,
                updated_at = datetime('now')
            WHERE student_id = ?
        """, (
            old_data.get("first_name"),
            old_data.get("last_name"),
            old_data.get("level"),
            old_data.get("status"),
            student_id
        ))
