from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import init_db, add_paste, get_all_pastes, get_paste, delete_paste
from auth import check_password

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
    
    # Формируем ссылку для просмотра
    view_url = request.host_url + 'view/' + paste_id
    
    return jsonify({
        'success': True,
        'view_url': view_url,
        'paste_id': paste_id
    })

# Просмотр записи (доступно всем по ссылке)
@app.route('/view/<paste_id>')
def view(paste_id):
    content = get_paste(paste_id)
    if content is None:
        return "Запись не найдена или была удалена", 404
    return render_template('view.html', content=content)

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