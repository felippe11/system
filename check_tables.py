import sqlite3

# Verificar tabelas em app.db
conn = sqlite3.connect('instance/app.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tabelas em app.db:')
for table in tables:
    print(f'- {table[0]}')
conn.close()