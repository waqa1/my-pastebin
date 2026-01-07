import sqlite3
import secrets
import string
from datetime import datetime
import sys

def generate_id(length=8):
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def init_db():
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pastes (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            secret_key TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_paste(content):
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: очистка при сохранении
    clean_content = content.replace('\r\n', '\n').replace('\r', '\n')
    clean_content = clean_content.replace('\x0b', '').replace('\x0c', '')
    clean_content = clean_content.replace('\x00', '').replace('\x1a', '')
    
    paste_id = generate_id()
    secret_key = generate_id(16)
    
    print(f"\n=== [DEBUG SAVE] Сохранение {paste_id} ===", file=sys.stderr)
    print(f"[DEBUG SAVE] Длина очищенная: {len(clean_content)}", file=sys.stderr)
    print(f"[DEBUG SAVE] Последние 150 символов: '{clean_content[-150:]}'", file=sys.stderr)
    
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("INSERT INTO pastes (id, content, created_at, secret_key) VALUES (?, ?, ?, ?)",
              (paste_id, clean_content, datetime.now(), secret_key))
    conn.commit()
    conn.close()
    
    print(f"=== [DEBUG SAVE] Успешно сохранено ===\n", file=sys.stderr)
    return paste_id

def get_all_pastes():
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("SELECT id, content, created_at FROM pastes ORDER BY created_at DESC")
    pastes = c.fetchall()
    conn.close()
    
    result = []
    for paste_id, content, created_at in pastes:
        preview = content[:200] + "..." if len(content) > 200 else content
        result.append({
            'id': paste_id,
            'preview': preview,
            'created_at': created_at,
            'length': len(content)
        })
    return result

def get_paste(paste_id):
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("SELECT content FROM pastes WHERE id = ?", (paste_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return result[0]
    return None

def delete_paste(paste_id):
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("DELETE FROM pastes WHERE id = ?", (paste_id,))
    rows_deleted = c.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0
