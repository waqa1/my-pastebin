import sqlite3
import secrets
import string
from datetime import datetime

# Функция для генерации случайного ID
def generate_id(length=8):
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    # Создаём таблицу "pastes" с полями: id, текст, дата создания, секретный ключ для удаления
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

# Добавление новой вставки
def add_paste(content):
    # Нормализуем концы строк: заменяем \r\n и \r на \n
    normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    paste_id = generate_id()
    secret_key = generate_id(16)
    
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("INSERT INTO pastes (id, content, created_at, secret_key) VALUES (?, ?, ?, ?)",
              (paste_id, normalized_content, datetime.now(), secret_key))
    conn.commit()
    conn.close()
    return paste_id

# Получение всех вставок (для админки)
def get_all_pastes():
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("SELECT id, content, created_at FROM pastes ORDER BY created_at DESC")
    pastes = c.fetchall()
    conn.close()
    
    # Форматируем результат
    result = []
    for paste_id, content, created_at in pastes:
        # Обрезаем контент для отображения в списке
        preview = content[:200] + "..." if len(content) > 200 else content
        result.append({
            'id': paste_id,
            'preview': preview,
            'created_at': created_at,
            'length': len(content)
        })
    return result

# Получение конкретной вставки по ID
def get_paste(paste_id):
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("SELECT content FROM pastes WHERE id = ?", (paste_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return result[0]  # Возвращаем текст
    return None

# Удаление вставки по ID
def delete_paste(paste_id):
    conn = sqlite3.connect('pastes.db')
    c = conn.cursor()
    c.execute("DELETE FROM pastes WHERE id = ?", (paste_id,))
    rows_deleted = c.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0
