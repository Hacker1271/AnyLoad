# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
# ANYLOAD V1.1 - DATABASE MANAGER
# ═══════════════════════════════════════════════════════════════════════════
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
from contextlib import contextmanager


class DatabaseManager:
    """
    Elite database manager with:
    - Media library logging
    - Vault management with PIN security
    - Settings storage
    - Proper resource cleanup (no leaks)
    """
    
    def __init__(self, db_path: Path):
        """Initialize database connection"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create connection
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=10.0
        )
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        # Create tables
        self._create_tables()
        
        print(f"[✓] Database initialized: {self.db_path}")
    
    def _create_tables(self):
        """Create all required tables"""
        cursor = self.conn.cursor()
        
        # Media library table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                format TEXT,
                quality TEXT,
                size_bytes INTEGER,
                duration_seconds INTEGER,
                thumbnail_path TEXT,
                download_date TEXT NOT NULL,
                source_url TEXT
            )
        ''')
        
        # Vault table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vault (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                vault_path TEXT UNIQUE NOT NULL,
                file_type TEXT NOT NULL,
                added_date TEXT NOT NULL
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Security questions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer_hash TEXT NOT NULL
            )
        ''')
        
        self.conn.commit()
        print("[✓] Database tables created")
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONTEXT MANAGER (SAFE TRANSACTIONS)
    # ═══════════════════════════════════════════════════════════════════════
    @contextmanager
    def transaction(self):
        """Context manager for safe transactions"""
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"[✗] Transaction failed: {e}")
            raise
        finally:
            cursor.close()
    
    # ═══════════════════════════════════════════════════════════════════════
    # MEDIA LIBRARY
    # ═══════════════════════════════════════════════════════════════════════
    def add_media(
        self,
        filepath: str,
        filename: str,
        file_type: str,
        format: str = None,
        quality: str = None,
        size_bytes: int = None,
        duration_seconds: int = None,
        thumbnail_path: str = None,
        source_url: str = None
    ) -> bool:
        """
        Add media to library (INSERT OR IGNORE for safety)
        Returns: True if added, False if already exists
        """
        try:
            with self.transaction() as cursor:
                cursor.execute('''
                    INSERT OR IGNORE INTO media (
                        filepath, filename, file_type, format, quality,
                        size_bytes, duration_seconds, thumbnail_path,
                        download_date, source_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    filepath,
                    filename,
                    file_type,
                    format,
                    quality,
                    size_bytes,
                    duration_seconds,
                    thumbnail_path,
                    datetime.now().isoformat(),
                    source_url
                ))
                
                # Check if row was actually inserted
                if cursor.rowcount > 0:
                    print(f"[✓] Media added to library: {filename}")
                    return True
                else:
                    print(f"[!] Media already in library: {filename}")
                    return False
        
        except Exception as e:
            print(f"[✗] Failed to add media: {e}")
            return False
    
    def get_all_media(self, file_type: str = None) -> List[dict]:
        """
        Get all media from library
        file_type: 'video', 'audio', or None for all
        """
        try:
            cursor = self.conn.cursor()
            
            if file_type:
                cursor.execute(
                    'SELECT * FROM media WHERE file_type = ? ORDER BY download_date DESC',
                    (file_type,)
                )
            else:
                cursor.execute('SELECT * FROM media ORDER BY download_date DESC')
            
            rows = cursor.fetchall()
            cursor.close()
            
            return [dict(row) for row in rows]
        
        except Exception as e:
            print(f"[✗] Failed to get media: {e}")
            return []
    
    def get_media_by_path(self, filepath: str) -> Optional[dict]:
        """Get media info by filepath"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM media WHERE filepath = ?', (filepath,))
            row = cursor.fetchone()
            cursor.close()
            
            return dict(row) if row else None
        
        except Exception as e:
            print(f"[✗] Failed to get media: {e}")
            return None
    
    def delete_media(self, filepath: str) -> bool:
        """Delete media from library"""
        try:
            with self.transaction() as cursor:
                cursor.execute('DELETE FROM media WHERE filepath = ?', (filepath,))
            
            print(f"[✓] Media deleted from library: {filepath}")
            return True
        
        except Exception as e:
            print(f"[✗] Failed to delete media: {e}")
            return False
    
    def update_media_path(self, old_path: str, new_path: str) -> bool:
        """Update media filepath (for rename)"""
        try:
            with self.transaction() as cursor:
                cursor.execute(
                    'UPDATE media SET filepath = ?, filename = ? WHERE filepath = ?',
                    (new_path, Path(new_path).name, old_path)
                )
            
            print(f"[✓] Media path updated: {old_path} -> {new_path}")
            return True
        
        except Exception as e:
            print(f"[✗] Failed to update media path: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════
    # VAULT MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    def add_to_vault(
        self,
        original_name: str,
        vault_path: str,
        file_type: str
    ) -> bool:
        """Add file to vault"""
        try:
            with self.transaction() as cursor:
                cursor.execute('''
                    INSERT INTO vault (original_name, vault_path, file_type, added_date)
                    VALUES (?, ?, ?, ?)
                ''', (
                    original_name,
                    vault_path,
                    file_type,
                    datetime.now().isoformat()
                ))
            
            print(f"[✓] Added to vault: {original_name}")
            return True
        
        except Exception as e:
            print(f"[✗] Failed to add to vault: {e}")
            return False
    
    def get_vault_files(self) -> List[Tuple[str, str, str]]:
        """
        Get all vault files
        Returns: List of (original_name, vault_path, file_type)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT original_name, vault_path, file_type FROM vault ORDER BY added_date DESC')
            rows = cursor.fetchall()
            cursor.close()
            
            return [(row[0], row[1], row[2]) for row in rows]
        
        except Exception as e:
            print(f"[✗] Failed to get vault files: {e}")
            return []
    
    def remove_from_vault(self, vault_path: str) -> bool:
        """Remove file from vault"""
        try:
            with self.transaction() as cursor:
                cursor.execute('DELETE FROM vault WHERE vault_path = ?', (vault_path,))
            
            print(f"[✓] Removed from vault: {vault_path}")
            return True
        
        except Exception as e:
            print(f"[✗] Failed to remove from vault: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════
    # PIN & SECURITY
    # ═══════════════════════════════════════════════════════════════════════
    def set_pin(self, pin: str) -> bool:
        """
        Set vault PIN (hashed with SHA256)
        """
        try:
            pin_hash = hashlib.sha256(pin.encode()).hexdigest()
            
            with self.transaction() as cursor:
                cursor.execute(
                    'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                    ('vault_pin', pin_hash)
                )
            
            print("[✓] PIN set successfully")
            return True
        
        except Exception as e:
            print(f"[✗] Failed to set PIN: {e}")
            return False
    
    def check_pin(self, pin: str) -> bool:
        """Verify PIN"""
        try:
            pin_hash = hashlib.sha256(pin.encode()).hexdigest()
            
            cursor = self.conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', ('vault_pin',))
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return row[0] == pin_hash
            
            return False
        
        except Exception as e:
            print(f"[✗] Failed to check PIN: {e}")
            return False
    
    def is_pin_set(self) -> bool:
        """Check if PIN is set"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', ('vault_pin',))
            row = cursor.fetchone()
            cursor.close()
            
            return row is not None
        
        except Exception as e:
            print(f"[✗] Failed to check PIN status: {e}")
            return False
    
    def save_security_questions(self, qa_list: List[Tuple[str, str]]) -> bool:
        """
        Save security questions and answers
        qa_list: [(question, answer), ...]
        """
        try:
            with self.transaction() as cursor:
                # Clear existing questions
                cursor.execute('DELETE FROM security_questions')
                
                # Insert new questions
                for question, answer in qa_list:
                    answer_hash = hashlib.sha256(answer.lower().strip().encode()).hexdigest()
                    cursor.execute(
                        'INSERT INTO security_questions (question, answer_hash) VALUES (?, ?)',
                        (question, answer_hash)
                    )
            
            print(f"[✓] Saved {len(qa_list)} security questions")
            return True
        
        except Exception as e:
            print(f"[✗] Failed to save security questions: {e}")
            return False
    
    def verify_security_questions(self, answers: List[str]) -> bool:
        """Verify security question answers"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT answer_hash FROM security_questions ORDER BY id')
            rows = cursor.fetchall()
            cursor.close()
            
            if len(rows) != len(answers):
                return False
            
            for i, row in enumerate(rows):
                answer_hash = hashlib.sha256(answers[i].lower().strip().encode()).hexdigest()
                if row[0] != answer_hash:
                    return False
            
            return True
        
        except Exception as e:
            print(f"[✗] Failed to verify security questions: {e}")
            return False
    
    def has_security_questions(self) -> bool:
        """Check if security questions are set"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM security_questions')
            count = cursor.fetchone()[0]
            cursor.close()
            
            return count > 0
        
        except Exception as e:
            print(f"[✗] Failed to check security questions: {e}")
            return False
    
    def get_security_questions(self) -> List[str]:
        """Get security questions (without answers)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT question FROM security_questions ORDER BY id')
            rows = cursor.fetchall()
            cursor.close()
            
            return [row[0] for row in rows]
        
        except Exception as e:
            print(f"[✗] Failed to get security questions: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════
    # SETTINGS
    # ═══════════════════════════════════════════════════════════════════════
    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting"""
        try:
            with self.transaction() as cursor:
                cursor.execute(
                    'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                    (key, value)
                )
            
            return True
        
        except Exception as e:
            print(f"[✗] Failed to set setting: {e}")
            return False
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            cursor.close()
            
            return row[0] if row else default
        
        except Exception as e:
            print(f"[✗] Failed to get setting: {e}")
            return default
    
    # ═══════════════════════════════════════════════════════════════════════
    # CLEANUP
    # ═══════════════════════════════════════════════════════════════════════
    def close(self):
        """Close database connection (CRITICAL: prevents resource leak)"""
        try:
            if self.conn:
                self.conn.close()
                print("[✓] Database connection closed")
        except Exception as e:
            print(f"[!] Error closing database: {e}")
    
    def __del__(self):
        """Destructor: auto-close connection"""
        self.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL DATABASE INSTANCE
# ═══════════════════════════════════════════════════════════════════════════
def get_database(base_path: Path) -> DatabaseManager:
    """Get or create database instance"""
    db_path = base_path / "anyload.db"
    return DatabaseManager(db_path)
