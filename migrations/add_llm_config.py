"""
Database migration script to create the llm_config table.
Run this script once to add LLM provider configuration support.

Usage:
    python migrations/add_llm_config.py
"""

import os
import sys
import sqlite3

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def migrate():
    """Create llm_config table if it doesn't exist."""
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'instance',
        'autoscoring.db'
    )

    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        print("The table will be created automatically when the app starts.")
        sys.exit(0)

    print(f"Migrating database: {db_path}")

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_config'"
        )
        if cursor.fetchone():
            print("- Table already exists: llm_config")
        else:
            cursor.execute("""
                CREATE TABLE llm_config (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✓ Created table: llm_config")

        # Add UPDATE trigger for updated_at
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name='llm_config_update_timestamp'"
        )
        if cursor.fetchone():
            print("- Trigger already exists: llm_config_update_timestamp")
        else:
            cursor.execute("""
                CREATE TRIGGER llm_config_update_timestamp
                AFTER UPDATE ON llm_config
                FOR EACH ROW
                BEGIN
                    UPDATE llm_config SET updated_at = CURRENT_TIMESTAMP WHERE key = NEW.key;
                END
            """)
            print("✓ Created trigger: llm_config_update_timestamp")

        conn.commit()
        print("\nMigration completed successfully!")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    migrate()
