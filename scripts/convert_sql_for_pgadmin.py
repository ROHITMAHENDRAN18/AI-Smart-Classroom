import re

with open('ai_smart_classroom_phase19_backup.sql', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_copy = False
copy_table = ''
copy_cols = ''
data_rows = []

def format_val(val):
    if val == r'\N' or val == '':
        return 'NULL'
    if val == 't':
        return 'TRUE'
    if val == 'f':
        return 'FALSE'
    # Check if pure number (not string like 24AD095 or timestamps)
    # Check if student id or session id or code
    if re.fullmatch(r'^-?\d+$', val):
        return val
    if re.fullmatch(r'^-?\d+\.\d+$', val):
        return val
    # string, escape single quotes
    escaped = val.replace("'", "''")
    return f"'{escaped}'"

for line in lines:
    stripped = line.strip()
    if stripped.startswith('COPY ') and 'FROM stdin;' in stripped:
        in_copy = True
        part = stripped[len('COPY '):-len(' FROM stdin;')]
        copy_table, copy_cols = part.split(' ', 1)
        data_rows = []
        continue
    
    if in_copy:
        if stripped == r'\.':
            in_copy = False
            if data_rows:
                val_lines = []
                for row in data_rows:
                    vals = [format_val(v) for v in row]
                    val_lines.append('(' + ', '.join(vals) + ')')
                insert_stmt = f'INSERT INTO {copy_table} {copy_cols} VALUES\n' + ',\n'.join(val_lines) + ';\n'
                new_lines.append(insert_stmt)
            continue
        else:
            line_no_nl = line.rstrip('\r\n')
            parts = line_no_nl.split('\t')
            data_rows.append(parts)
            continue
    
    new_lines.append(line)

with open('ai_smart_classroom_phase19_backup.sql', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Successfully converted all COPY statements to standard INSERT statements!')
