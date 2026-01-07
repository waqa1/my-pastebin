from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, make_response
from database import init_db, add_paste, get_all_pastes, get_paste, delete_paste
from auth import check_password
from datetime import datetime
import sys

app = Flask(__name__)
app.secret_key = 'your_secret_key_for_sessions'

init_db()

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
    
    pastes = get_all_pastes()
    return render_template('admin.html', pastes=pastes)

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
    
    # Очищаем для HTML
    clean_content = content.replace('\r\n', '\n').replace('\r', '\n')
    clean_content = clean_content.replace('\x0b', '').replace('\x0c', '')
    
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
    
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ
    # 1. Заменяем переносы строк
    clean_content = content.replace('\r\n', '\n').replace('\r', '\n')
    # 2. Удаляем опасные управляющие символы, которые могут обрывать вывод
    clean_content = clean_content.replace('\x0b', '').replace('\x0c', '')  # вертикальная табуляция и form feed
    clean_content = clean_content.replace('\x00', '')  # нулевой байт
    clean_content = clean_content.replace('\x1a', '')  # Ctrl+Z (конец файла в Windows)
    
    print(f"[DEBUG RAW] Длина исходная: {len(content)}", file=sys.stderr)
    print(f"[DEBUG RAW] Длина очищенная: {len(clean_content)}", file=sys.stderr)
    print(f"[DEBUG RAW] Последние 100 символов: '{clean_content[-100:]}'", file=sys.stderr)
    
    response = make_response(clean_content)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    # Явно указываем размер для надёжности
    response.headers['Content-Length'] = str(len(clean_content.encode('utf-8')))
    
    print(f"=== [DEBUG RAW] Завершено ===\n", file=sys.stderr)
    return response

@app.route('/api/delete/<paste_id>', methods=['POST'])
def api_delete(paste_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
    
    if delete_paste(paste_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Не удалось удалить'}), 404

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
