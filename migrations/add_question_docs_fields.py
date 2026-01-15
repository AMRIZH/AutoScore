"""
Database migration script to add new fields to the jobs table.
Run this script once to add the question_doc_paths and additional_notes columns.

Usage:
    python migrations/add_question_docs_fields.py
"""

import os
import sys
import sqlite3

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def migrate():
    """Add new columns to the jobs table."""
    # Get database path from config or use default
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'instance',
        'autoscoring.db'
    )
    
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        print("The columns will be created automatically when the app starts.")
        return
    
    print(f"Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        migrations_done = []
        
        # Add question_doc_paths column if not exists
        if 'question_doc_paths' not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN question_doc_paths TEXT")
            migrations_done.append('question_doc_paths')
            print("✓ Added column: question_doc_paths")
        else:
            print("- Column already exists: question_doc_paths")
        
        # Add additional_notes column if not exists
        if 'additional_notes' not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN additional_notes TEXT")
            migrations_done.append('additional_notes')
            print("✓ Added column: additional_notes")
        else:
            print("- Column already exists: additional_notes")
        
        conn.commit()
        
        if migrations_done:
            print(f"\n✓ Migration completed successfully! Added {len(migrations_done)} column(s).")
        else:
            print("\n✓ No migration needed. All columns already exist.")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
