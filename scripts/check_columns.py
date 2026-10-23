from backend.database.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    for table in ['students', 'classroom_sessions', 'attendance_records', 'attention_records', 'classrooms']:
        res = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")).fetchall()
        print(f"Table '{table}' columns: {[r[0] for r in res]}")
