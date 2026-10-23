"""Script to automatically load complete pre-populated database data."""

import os
from sqlalchemy import text
from backend.database.connection import engine
from scripts.create_tables import create_tables

BACKUP_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ai_smart_classroom_complete_data.sql')


def load_data():
    print("1. Ensuring all database tables exist...")
    create_tables()

    if not os.path.exists(BACKUP_FILE):
        raise FileNotFoundError(f"Backup file not found at: {BACKUP_FILE}")

    print(f"2. Loading pre-populated data from {os.path.basename(BACKUP_FILE)}...")
    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split into statements
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

    with engine.begin() as conn:
        for stmt in statements:
            if stmt.startswith('--'):
                # remove leading comments
                lines = [l for l in stmt.split('\n') if not l.strip().startswith('--')]
                stmt = '\n'.join(lines).strip()
            if not stmt:
                continue
            conn.execute(text(stmt))

    print("3. Pre-populated data successfully loaded into PostgreSQL database!")


if __name__ == '__main__':
    load_data()
