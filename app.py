from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, make_response
from database import init_db, add_paste, get_all_pastes, get_paste, delete_paste, get_pastes_by_ids, SessionLocal, Paste
from auth import check_password
from datetime import datetime
import sys
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key_for_sessions'



@app.route('/', methods=['GET', 'POST'])
def admin():
    if not session.get('is_admin'):
        if request.method == 'POST':
            password = request.form.get('password')
            if check_password(password):
                session['is_admin'] = True
                return redirect(url_for('admin'))
            else:
                return "Неверный пароль", 403
        return render_template('create.html')
    
    # Получаем номер страницы
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Получаем данные из базы
    db = SessionLocal()
    
    # Общее количество записей
    total_pastes = db.query(Paste).count()
    
    # Записи для текущей страницы
    pastes = db.query(Paste).order_by(Paste.created_at.desc()) \
                           .offset((page - 1) * per_page) \
                           .limit(per_page).all()
    
    # Формируем список как раньше
    result = []
    host_url = request.host_url.rstrip('/')
    
    for paste in pastes:
        preview = paste.content[:200] + "..." if len(paste.content) > 200 else paste.content
        result.append({
            'id': paste.id,
            'preview': preview,
            'created_at': paste.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'length': len(paste.content),
            'view_url': f"{host_url}/view/{paste.id}",
            'raw_url': f"{host_url}/raw/{paste.id}"
        })
    
    db.close()
    
    # Вычисляем общее количество страниц
    total_pages = max(1, (total_pastes + per_page - 1) // per_page)
    
    # Передаем ВСЕ необходимые переменные в шаблон
    return render_template('admin.html', 
                         pastes=result,
                         current_page=page,
                         total_pages=total_pages,
                         total_pastes=total_pastes)

@app.route('/create', methods=['POST'])
def create():
    if not session.get('is_admin'):
        return redirect(url_for('admin'))
    
    content = request.form.get('content')
    if not content:
        return "Текст не может быть пустым", 400
    
    paste_id = add_paste(content)
    
    host_url = request.host_url.rstrip('/')
    view_url = f"{host_url}/view/{paste_id}"
    raw_url = f"{host_url}/raw/{paste_id}"
    
    return jsonify({
        'success': True,
        'view_url': view_url,
        'raw_url': raw_url,
        'paste_id': paste_id
    })

@app.route('/view/<paste_id>')
def view(paste_id):
    content = get_paste(paste_id)
    if content is None:
        return "Запись не найдена или была удалена", 404
    
    # Очистка для HTML
    clean_content = clean_text_for_output(content)
    return render_template('view.html', content=clean_content)

@app.route('/raw/<paste_id>')
def view_raw(paste_id):
    """
    Функция для отдачи сырого (plain text) содержимого вставки.
    """
    print(f"\n=== [DEBUG RAW] Обработка /raw/{paste_id} ===", file=sys.stderr)
    
    content = get_paste(paste_id)
    if content is None:
        print(f"[DEBUG RAW] Вставка не найдена", file=sys.stderr)
        return "Вставка не найдена", 404
    
    # Расширенная очистка текста
    clean_content = clean_text_for_output(content)
    
    print(f"[DEBUG RAW] Длина исходная: {len(content)}", file=sys.stderr)
    print(f"[DEBUG RAW] Длина очищенная: {len(clean_content)}", file=sys.stderr)
    print(f"[DEBUG RAW] Последние 100 символов: '{clean_content[-100:]}'", file=sys.stderr)
    
    response = make_response(clean_content)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    response.headers['Content-Length'] = str(len(clean_content.encode('utf-8')))

        # --- НАЧАЛО ИСПРАВЛЕНИЯ ---
    # Критически важные заголовки против кэширования
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
    
    print(f"=== [DEBUG RAW] Завершено ===\n", file=sys.stderr)
    return response

@app.route('/merge', methods=['POST'])
def merge_pastes():
    if not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
    
    data = request.get_json()
    selected_ids = data.get('selected_ids', [])
    
    if not selected_ids:
        return jsonify({'success': False, 'error': 'Не выбрано ни одной записи'}), 400
    
    pastes = get_pastes_by_ids(selected_ids)
    
    if not pastes:
        return jsonify({'success': False, 'error': 'Записи не найдены'}), 404
    
    merged_content_parts = []
    for paste_id, content, created_at in pastes:
        header = f"\n\n--- [{paste_id}] {created_at} ---\n"
        merged_content_parts.append(header + content)
    
    merged_text = "".join(merged_content_parts).strip()
    new_paste_id = add_paste(merged_text)
    
    host_url = request.host_url.rstrip('/')
    view_url = f"{host_url}/view/{new_paste_id}"
    raw_url = f"{host_url}/raw/{new_paste_id}"
    
    return jsonify({
        'success': True,
        'message': f'Объединено записей: {len(pastes)}',
        'new_paste_id': new_paste_id,
        'view_url': view_url,
        'raw_url': raw_url,
        'merged_preview': merged_text[:500] + '...' if len(merged_text) > 500 else merged_text
    })

@app.route('/api/delete/<paste_id>', methods=['POST'])
def api_delete(paste_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
    
    if delete_paste(paste_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Не удалось удалить'}), 404
        
# начало сортировки
@app.route('/api/pastes/sorted')
def get_sorted_pastes():
    """Возвращает все пасты, отсортированные по дате"""
    if not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    order = request.args.get('order', 'desc')  # 'asc' или 'desc'
    
    try:
        # Получаем все пасты (они уже отсортированы по дате в убывающем порядке из get_all_pastes)
        from database import get_all_pastes
        pastes = get_all_pastes()
        
        # Если нужна сортировка по возрастанию, меняем порядок
        if order == 'asc':
            pastes = list(reversed(pastes))
        
        # Добавляем полные URLs
        host_url = request.host_url.rstrip('/')
        for paste in pastes:
            paste['view_url'] = f"{host_url}/view/{paste['id']}"
            paste['raw_url'] = f"{host_url}/raw/{paste['id']}"
        
        return jsonify({
            'success': True,
            'pastes': pastes,
            'order': order
        })
    except Exception as e:
        print(f"Ошибка при получении отсортированных записей: {e}", file=sys.stderr)
        return jsonify({'success': False, 'error': 'Ошибка сервера'}), 500
# конец сортировки

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin'))

def clean_text_for_output(text):
    """
    Расширенная очистка текста от невидимых и управляющих символов.
    """
    if not text:
        return text
    
    # 1. Нормализация концов строк
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 2. Удаление всех управляющих символов ASCII (кроме табуляции и переноса строки)
    # Это включает: \x00-\x08, \x0b-\x0c, \x0e-\x1f, \x7f
    cleaned = []
    for char in text:
        code = ord(char)
        # Разрешаем: табуляция (\t=9), перенос строки (\n=10), обычные символы
        if code == 9 or code == 10 or (code >= 32 and code != 127) or code > 127:
            cleaned.append(char)
        else:
            # Заменяем проблемные символы на пробел или удаляем
            if code == 13:  # \r (должен быть удалён выше)
                continue
            cleaned.append(' ')
    
    text = ''.join(cleaned)
    
    # 3. Удаление BOM (маркер порядка байт UTF-8)
    if text.startswith('\ufeff'):
        text = text[1:]
    
    # 4. Удаление нулевых байтов и других специфичных символов
    text = text.replace('\x00', '').replace('\x1a', '')  # Ctrl+Z (конец файла)
    
    # 5. Удаление повторяющихся пробелов и пустых строк
    text = re.sub(r'[ \t]+', ' ', text)  # Множественные пробелы/табы -> один пробел
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Множественные пустые строки -> две
    
    return text.strip()
    
init_db()

if __name__ == '__main__':
    app.run(debug=True)











