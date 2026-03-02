"""
Database migration script to add question_text column to jobs table.
Run this script once for existing databases.

Usage:
    python migrations/add_question_text_field.py
"""

import os
import sys
import sqlite3

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def migrate():
    """Add question_text column to jobs table."""
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'instance',
        'autoscoring.db'
    )

    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        print("The column will be created automatically when the app starts.")
        return

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'question_text' not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN question_text TEXT")
            conn.commit()
            print("✓ Added column: question_text")
            print("\n✓ Migration completed successfully!")
        else:
            print("- Column already exists: question_text")
            print("\n✓ No migration needed.")

    except Exception as exc:
        conn.rollback()
        print(f"\n✗ Migration failed: {exc}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
