"""
Database connection and initialization for P2P Lifecycle Simulator

This module handles:
- SQLite database connection
- Table creation from schemas
- Database initialization on startup
"""

import sqlite3
import os
from typing import Optional
from contextlib import contextmanager
from backend.config import DATABASE_PATH


class Database:
    """
    Database manager for SQLite operations.

    Provides connection management and initialization utilities.
    """

    def __init__(self, db_path: str = DATABASE_PATH):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """Create data directory if it doesn't exist."""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            sqlite3.Connection: Database connection

        Example:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM purchase_orders")
        """
        conn = sqlite3.connect(self.db_path)
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = ()):
        """
        Execute a single query and return results.

        Args:
            query: SQL query string
            params: Query parameters (for parameterized queries)

        Returns:
            List of sqlite3.Row objects
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """
        Execute an INSERT query and return the last inserted row ID.

        Args:
            query: SQL INSERT statement
            params: Query parameters

        Returns:
            Last inserted row ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.lastrowid

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute an UPDATE or DELETE query and return affected row count.

        Args:
            query: SQL UPDATE or DELETE statement
            params: Query parameters

        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.rowcount

    def initialize_tables(self):
        """
        Create all database tables if they don't exist.

        This method reads SQL schema definitions from schemas.py
        and creates all required tables.
        """
        from backend.schemas import get_create_table_statements

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get all CREATE TABLE statements
            create_statements = get_create_table_statements()

            # Execute each statement
            for statement in create_statements:
                cursor.execute(statement)

            print(f"✓ Database initialized at {self.db_path}")
            print(f"✓ {len(create_statements)} tables created")

    def reset_database(self):
        """
        Drop all tables and recreate them.

        WARNING: This deletes all data. Use only for testing/development.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get list of all tables
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = cursor.fetchall()

            # Drop each table
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table['name']}")

            print(f"✓ All tables dropped")

        # Recreate tables
        self.initialize_tables()


# Global database instance
db = Database()


# ============================================================================
# DATABASE INITIALIZATION FUNCTION
# ============================================================================

def init_database():
    """
    Initialize the database on application startup.

    This function is called when the FastAPI app starts.
    It creates all tables if they don't exist.
    """
    db.initialize_tables()


# ============================================================================
# HELPER FUNCTIONS FOR QUERIES
# ============================================================================

def row_to_dict(row: sqlite3.Row) -> dict:
    """
    Convert sqlite3.Row to dictionary.

    Args:
        row: sqlite3.Row object

    Returns:
        Dictionary representation of the row
    """
    return dict(row) if row else None


def rows_to_dict_list(rows: list) -> list:
    """
    Convert list of sqlite3.Row objects to list of dictionaries.

    Args:
        rows: List of sqlite3.Row objects

    Returns:
        List of dictionaries
    """
    return [dict(row) for row in rows] if rows else []
