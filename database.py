import sqlite3
from datetime import datetime
import secrets
import string

def init_db():
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pastes (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def generate_id(length=8):
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def add_paste(content):
    paste_id = generate_id()
    
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("INSERT INTO pastes (id, content, created_at) VALUES (?, ?, ?)",
              (paste_id, content, datetime.now()))
    conn.commit()
    conn.close()
    
    return paste_id

def get_all_pastes():
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("SELECT id, created_at, content FROM pastes ORDER BY created_at DESC")
    pastes = c.fetchall()
    conn.close()
    
    result = []
    for paste in pastes:
        paste_id, created_at, content = paste
        preview = content[:100] + "..." if len(content) > 100 else content
        formatted_date = created_at.split('.')[0] if isinstance(created_at, str) else created_at
        result.append({
            'id': paste_id,
            'created_at': formatted_date,
            'preview': preview
        })
    return result

def get_paste(paste_id):
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("SELECT content FROM pastes WHERE id = ?", (paste_id,))
    paste = c.fetchone()
    conn.close()
    return paste[0] if paste else None

def delete_paste(paste_id):
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("DELETE FROM pastes WHERE id = ?", (paste_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted