from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, make_response
from database import init_db, add_paste, get_all_pastes, get_paste, delete_paste
from auth import check_password
from datetime import datetime
import sys

app = Flask(__name__)
app.secret_key = 'your_secret_key_for_sessions'

init_db()

# Главная страница (админка) - требует пароль
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
    
    # Получаем все записи для отображения
    pastes = get_all_pastes()
    return render_template('admin.html', pastes=pastes)

# Создание новой записи (доступно только админу)
@app.route('/create', methods=['POST'])
def create():
    if not session.get('is_admin'):
        return redirect(url_for('admin'))
    
    content = request.form.get('content')
    if not content:
        return "Текст не может быть пустым", 400
    
    paste_id = add_paste(content)
    
    # Формируем ОБЕ ссылки: с оформлением и сырую
    host_url = request.host_url.rstrip('/')
    view_url = f"{host_url}/view/{paste_id}"
    raw_url = f"{host_url}/raw/{paste_id}"
    
    return jsonify({
        'success': True,
        'view_url': view_url,
        'raw_url': raw_url,
        'paste_id': paste_id
    })

# Просмотр записи (доступно всем по ссылке) - HTML версия
@app.route('/view/<paste_id>')
def view(paste_id):
    content = get_paste(paste_id)
    if content is None:
        return "Запись не найдена или была удалена", 404
    # Очищаем контент для HTML отображения
    clean_content = content.replace('\r\n', '\n').replace('\r', '\n')
    return render_template('view.html', content=clean_content)

# Просмотр записи в виде ЧИСТОГО ТЕКСТА (для анализа)
@app.route('/raw/<paste_id>')
def view_raw(paste_id):
    """
    Функция для отдачи сырого (plain text) содержимого вставки.
    """
    # КРИТИЧЕСКИЙ ОТЛАДОЧНЫЙ БЛОК 1: начало обработки запроса
    print(f"\n=== [DEBUG] Начало обработки /raw/{paste_id} ===", file=sys.stderr)
    print(f"[DEBUG] Время запроса: {datetime.now().isoformat()}", file=sys.stderr)
    
    # Получаем контент из базы данных
    content = get_paste(paste_id)
    
    # КРИТИЧЕСКИЙ ОТЛАДОЧНЫЙ БЛОК 2: что получили из БД
    print(f"[DEBUG] Результат get_paste('{paste_id}'):", file=sys.stderr)
    print(f"[DEBUG]   - content is None? {content is None}", file=sys.stderr)
    print(f"[DEBUG]   - Тип content: {type(content)}", file=sys.stderr)
    
    if content is None:
        print(f"[DEBUG]   - Вставка с ID '{paste_id}' не найдена в БД", file=sys.stderr)
        print(f"=== [DEBUG] Конец обработки /raw/{paste_id} ===\n", file=sys.stderr)
        return "Вставка не найдена", 404
    
    # Анализ полученного контента
    print(f"[DEBUG]   - Длина content: {len(content)} символов", file=sys.stderr)
    
    # ===== КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ =====
    # Очищаем текст от проблемных символов перед отправкой
    clean_content = content.replace('\r\n', '\n').replace('\r', '\n')
    print(f"[DEBUG]   - Длина ПОСЛЕ очистки: {len(clean_content)} символов", file=sys.stderr)
    
    # Проверяем последние символы
    print(f"[DEBUG]   - Последние 100 символов ДО очистки: '{content[-100:]}'", file=sys.stderr)
    print(f"[DEBUG]   - Последние 100 символов ПОСЛЕ очистки: '{clean_content[-100:]}'", file=sys.stderr)
    
    # Проверяем, нет ли в тексте специальных символов, которые могут обрывать вывод
    problematic_chars = ['\x00', '\x1a', '\x0c']  # нулевой байт, Ctrl+Z, form feed
    for char in problematic_chars:
        if char in clean_content:
            print(f"[DEBUG] ВНИМАНИЕ! В тексте найден проблемный символ: {repr(char)}", file=sys.stderr)
    
    # Создаём ответ из ОЧИЩЕННОГО текста
    response = make_response(clean_content)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    
    # КРИТИЧЕСКИЙ ОТЛАДОЧНЫЙ БЛОК 3: что отправляем в ответе
    print(f"[DEBUG] Параметры ответа:", file=sys.stderr)
    print(f"[DEBUG]   - Content-Type: {response.headers.get('Content-Type')}", file=sys.stderr)
    response_data = clean_content  # Уже очищено выше
    print(f"[DEBUG]   - Длина ответа: {len(response_data)} символов", file=sys.stderr)
    print(f"[DEBUG]   - Последние 50 символов ответа: '{response_data[-50:]}'", file=sys.stderr)
    print(f"=== [DEBUG] Конец обработки /raw/{paste_id} ===\n", file=sys.stderr)
    
    return response

# API для удаления (только для админа)
@app.route('/api/delete/<paste_id>', methods=['POST'])
def api_delete(paste_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
    
    if delete_paste(paste_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Не удалось удалить'}), 404

# Выход из админки
@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
