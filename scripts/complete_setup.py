from backend.database.connection import engine
from sqlalchemy import text

def setup():
    print("Starting complete database setup and alignment...")
    with engine.begin() as conn:
        # 1. Add missing updated_at to students and make email nullable
        conn.execute(text("""
            ALTER TABLE students 
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW();
            ALTER TABLE students 
            ALTER COLUMN email DROP NOT NULL;
        """))
        print("- Verified students.updated_at and nullable students.email columns.")

        # 2. Add missing attendance_source to attendance_records
        conn.execute(text("""
            ALTER TABLE attendance_records 
            ADD COLUMN IF NOT EXISTS attendance_source VARCHAR(20) NULL;
        """))
        print("- Verified attendance_records.attendance_source column.")

        # 3. Ensure teachers exist
        teachers = conn.execute(text("SELECT id, user_id, teacher_id FROM teachers ORDER BY id")).fetchall()
        teacher_id_to_use = teachers[0][0] if teachers else 1
        print(f"- Using teacher ID {teacher_id_to_use} for default classroom.")

        # 4. Ensure Classroom 1 exists
        conn.execute(text(f"""
            INSERT INTO classrooms (id, classroom_code, name, department, year, section, teacher_id, is_active, created_at, updated_at)
            VALUES (1, 'CLASS_1', 'AI Smart Classroom', 'AD', 3, 'B', {teacher_id_to_use}, TRUE, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET 
                is_active = TRUE,
                teacher_id = EXCLUDED.teacher_id;
        """))
        # Reset sequence for classrooms
        conn.execute(text("SELECT setval('classrooms_id_seq', (SELECT COALESCE(MAX(id), 1) FROM classrooms));"))
        print("- Verified Classroom 1 exists.")

        # 5. Add classroom_id to classroom_sessions
        conn.execute(text("""
            ALTER TABLE classroom_sessions 
            ADD COLUMN IF NOT EXISTS classroom_id INTEGER DEFAULT 1;
        """))
        conn.execute(text("""
            UPDATE classroom_sessions SET classroom_id = 1 WHERE classroom_id IS NULL;
        """))
        conn.execute(text("""
            ALTER TABLE classroom_sessions ALTER COLUMN classroom_id SET NOT NULL;
        """))
        print("- Verified classroom_sessions.classroom_id column.")

        # 6. Ensure students are enrolled in classroom 1
        conn.execute(text("""
            INSERT INTO classroom_members (classroom_id, student_id, joined_at, is_active)
            SELECT 1, student_id, NOW(), TRUE 
            FROM students
            ON CONFLICT ON CONSTRAINT uq_classroom_student DO NOTHING;
        """))
        print("- Enrolled students into Classroom 1.")

    print("Database setup and alignment completed successfully!")

if __name__ == "__main__":
    setup()
