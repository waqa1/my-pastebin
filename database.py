import os
from datetime import datetime
import uuid
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import re
import sys

Base = declarative_base()

class Paste(Base):
    __tablename__ = 'pastes'
    id = Column(String(10), primary_key=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    secret_key = Column(String(16), nullable=False)

engine = None
SessionLocal = None

def init_db():
    global engine, SessionLocal
    
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        database_url = 'sqlite:///paste_local.db'
        print("⚠️ DATABASE_URL не найден. Используется SQLite для локальной разработки.", file=sys.stderr)
    else:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        print("✅ Используется база данных PostgreSQL (Render).", file=sys.stderr)
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

def generate_id(length=8):
    return str(uuid.uuid4()).replace('-', '')[:length]

def clean_text_for_storage(text):
    if not text:
        return text
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    cleaned = []
    for char in text:
        code = ord(char)
        if code == 9 or code == 10 or (code >= 32 and code != 127):
            cleaned.append(char)
        else:
            cleaned.append(' ')
    text = ''.join(cleaned)
    text = text.replace('\ufeff', '').replace('\x00', '').replace('\x1a', '')
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def add_paste(content):
    print(f"\n=== [DEBUG SAVE] Начало сохранения ===", file=sys.stderr)
    
    clean_content = clean_text_for_storage(content)
    paste_id = generate_id()
    secret_key = generate_id(16)
    
    print(f"[DEBUG SAVE] ID новой вставки: {paste_id}", file=sys.stderr)
    
    db = SessionLocal()
    try:
        new_paste = Paste(id=paste_id, content=clean_content, secret_key=secret_key)
        db.add(new_paste)
        db.commit()
        print(f"[DEBUG SAVE] Успешно сохранено вставка {paste_id}", file=sys.stderr)
        return paste_id
    except Exception as e:
        db.rollback()
        print(f"[DEBUG SAVE] Ошибка сохранения: {e}", file=sys.stderr)
        raise
    finally:
        db.close()
    
    print(f"=== [DEBUG SAVE] Конец сохранения ===\n", file=sys.stderr)

def get_all_pastes():
    db = SessionLocal()
    pastes = db.query(Paste).order_by(Paste.created_at.desc()).all()
    db.close()
    
    result = []
    for paste in pastes:
        preview = paste.content[:200] + "..." if len(paste.content) > 200 else paste.content
        result.append({
            'id': paste.id,
            'preview': preview,
            'created_at': paste.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'length': len(paste.content)
        })
    return result

def get_paste(paste_id):
    db = SessionLocal()
    paste = db.query(Paste).filter(Paste.id == paste_id).first()
    db.close()
    
    if paste:
        return paste.content
    return None

def get_pastes_by_ids(paste_ids):
    if not paste_ids:
        return []
    
    db = SessionLocal()
    from sqlalchemy import case
    order_case = case([(Paste.id == pid, i) for i, pid in enumerate(paste_ids)], else_=len(paste_ids))
    pastes = db.query(Paste).filter(Paste.id.in_(paste_ids)).order_by(order_case).all()
    db.close()
    
    return [(p.id, p.content, p.created_at.strftime('%Y-%m-%d %H:%M:%S')) for p in pastes]

def delete_paste(paste_id):
    db = SessionLocal()
    paste = db.query(Paste).filter(Paste.id == paste_id).first()
    if paste:
        db.delete(paste)
        db.commit()
        db.close()
        return True
    db.close()
    return False
