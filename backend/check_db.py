import sqlite3
import os

db_path = "sustainai.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    
    cursor.execute("SELECT * FROM recommendations LIMIT 1;")
    col_names = [description[0] for description in cursor.description]
    print(f"Columns: {col_names}")
    
    cursor.execute("SELECT issue, reasoning_proof, control_action FROM recommendations LIMIT 5;")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Issue: {row[0]}")
        print(f"Proof: {row[1]}")
        print(f"Command: {row[2]}")
        print("-" * 20)
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
