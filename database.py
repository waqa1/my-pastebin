import sqlite3
import secrets
import string
from datetime import datetime
import sys
import re

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
    """
    Сохранение вставки с расширенной очисткой и диагностикой.
    """
    print(f"\n=== [DEBUG SAVE] Начало сохранения ===", file=sys.stderr)
    
    # Расширенная очистка перед сохранением
    clean_content = clean_text_for_storage(content)
    
    paste_id = generate_id()
    secret_key = generate_id(16)
    
    # Диагностика: что сохраняем
    print(f"[DEBUG SAVE] ID новой вставки: {paste_id}", file=sys.stderr)
    print(f"[DEBUG SAVE] Длина исходного текста: {len(content)}", file=sys.stderr)
    print(f"[DEBUG SAVE] Длина очищенного текста: {len(clean_content)}", file=sys.stderr)
    
    # Проверка последних символов
    last_chars_raw = content[-150:] if len(content) > 150 else content
    last_chars_clean = clean_content[-150:] if len(clean_content) > 150 else clean_content
    
    print(f"[DEBUG SAVE] Последние 150 символов ДО очистки: '{last_chars_raw}'", file=sys.stderr)
    print(f"[DEBUG SAVE] Последние 150 символов ПОСЛЕ очистки: '{last_chars_clean}'", file=sys.stderr)
    
    # Поиск необычных символов в исходном тексте
    print(f"[DEBUG SAVE] Поиск нестандартных символов...", file=sys.stderr)
    for i, char in enumerate(content[-200:] if len(content) > 200 else content):
        code = ord(char)
        if code < 32 or code == 127:
            pos = len(content) - (len(content[-200:]) if len(content) > 200 else len(content)) + i
            print(f"[DEBUG SAVE] Позиция {pos}: символ #{code} (hex: {hex(code)}) = {repr(char)}", file=sys.stderr)
    
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("INSERT INTO pastes (id, content, created_at, secret_key) VALUES (?, ?, ?, ?)",
              (paste_id, clean_content, datetime.now(), secret_key))
    conn.commit()
    conn.close()
    
    print(f"[DEBUG SAVE] Успешно сохранено вставка {paste_id}", file=sys.stderr)
    print(f"=== [DEBUG SAVE] Конец сохранения ===\n", file=sys.stderr)
    
    return paste_id

def clean_text_for_storage(text):
    """
    Очистка текста перед сохранением в базу данных.
    """
    if not text:
        return text
    
    # 1. Нормализация концов строк
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 2. Удаление всех управляющих символов (кроме табуляции и переноса строки)
    cleaned = []
    for char in text:
        code = ord(char)
        if code == 9 or code == 10 or (code >= 32 and code != 127):
            cleaned.append(char)
        else:
            # Заменяем проблемные символы на пробел
            cleaned.append(' ')
    
    text = ''.join(cleaned)
    
    # 3. Удаление BOM и других специфичных символов
    text = text.replace('\ufeff', '').replace('\x00', '').replace('\x1a', '')
    
    # 4. Удаление повторяющихся пробелов
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()

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

def get_pastes_by_ids(paste_ids):
    if not paste_ids:
        return []
    
    placeholders = ', '.join(['?'] * len(paste_ids))
    
    # Эмуляция ORDER BY FIELD для сохранения порядка
    query = f"SELECT id, content, created_at FROM pastes WHERE id IN ({placeholders}) ORDER BY CASE id"
    for i, pid in enumerate(paste_ids):
        query += f" WHEN '{pid}' THEN {i}"
    query += " END"
    
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute(query, paste_ids)
    pastes = c.fetchall()
    conn.close()
    return pastes

def delete_paste(paste_id):
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("DELETE FROM pastes WHERE id = ?", (paste_id,))
    rows_deleted = c.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0
