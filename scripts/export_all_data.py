import json
from datetime import datetime, date
from backend.database.connection import engine
from sqlalchemy import text

tables = [
    'users',
    'teachers',
    'classrooms',
    'students',
    'classroom_members',
    'classroom_sessions',
    'attendance_records',
    'attention_records',
    'frame_inference_summaries',
]


def export_data():
    output_file = 'ai_smart_classroom_complete_data.sql'
    print(f"Exporting existing database data to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('-- AI Smart Classroom Complete Database Export\n')
        f.write(f'-- Exported at: {datetime.now().isoformat()}\n\n')
        f.write('SET statement_timeout = 0;\n')
        f.write("SET client_encoding = 'UTF8';\n\n")

        with engine.connect() as conn:
            for t in tables:
                rows = conn.execute(text(f'SELECT * FROM {t}')).fetchall()
                if not rows:
                    f.write(f'-- No rows in {t}\n\n')
                    continue

                cols = list(rows[0]._mapping.keys())
                cols_str = ', '.join([f'"{c}"' for c in cols])

                val_clauses = []
                for r in rows:
                    m = r._mapping
                    row_vals = []
                    for c in cols:
                        v = m[c]
                        if v is None:
                            row_vals.append('NULL')
                        elif isinstance(v, bool):
                            row_vals.append('TRUE' if v else 'FALSE')
                        elif isinstance(v, (int, float)):
                            row_vals.append(str(v))
                        elif isinstance(v, (datetime, date)):
                            row_vals.append(f"'{v.isoformat()}'")
                        elif isinstance(v, (dict, list)):
                            val_str = json.dumps(v).replace("'", "''")
                            row_vals.append(f"'{val_str}'::json")
                        elif isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                            try:
                                parsed = json.loads(v)
                                val_str = json.dumps(parsed).replace("'", "''")
                                row_vals.append(f"'{val_str}'::json")
                            except Exception:
                                escaped = v.replace("'", "''")
                                row_vals.append(f"'{escaped}'")
                        else:
                            escaped = str(v).replace("'", "''")
                            row_vals.append(f"'{escaped}'")
                    val_clauses.append('(' + ', '.join(row_vals) + ')')

                f.write(f'-- Table: {t} ({len(rows)} rows)\n')
                f.write(f'INSERT INTO {t} ({cols_str}) VALUES\n' + ',\n'.join(val_clauses) + '\nON CONFLICT DO NOTHING;\n\n')

                if 'id' in cols:
                    f.write(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE((SELECT MAX(id) FROM {t}), 1), true);\n\n")

    print(f"Data successfully exported to {output_file}!")


if __name__ == '__main__':
    export_data()
