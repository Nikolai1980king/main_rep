from flask import Flask, render_template_string, request, redirect, url_for, make_response, jsonify
from flask_socketio import SocketIO, emit, join_room
import os
import uuid
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'super-secret-key'
socketio = SocketIO(app)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

profiles = []
likes = defaultdict(list)
matches = defaultdict(list)
messages = defaultdict(list)
notifications = defaultdict(list)


def add_notification(user_id, message):
    notifications[user_id].append({
        'id': str(uuid.uuid4()),
        'message': message,
        'timestamp': datetime.now()
    })


def check_for_matches(user_id):
    current_profile = next((p for p in profiles if p['user_id'] == user_id), None)
    if not current_profile:
        return
    current_profile_id = profiles.index(current_profile)
    for liked_profile_id in likes[user_id]:
        liked_user_id = profiles[liked_profile_id]['user_id']
        if current_profile_id in likes.get(liked_user_id, []):
            if liked_user_id not in matches[user_id]:
                matches[user_id].append(liked_user_id)
                matches[liked_user_id].append(user_id)
                user_name = current_profile['name']
                matched_user_name = profiles[liked_profile_id]['name']
                add_notification(user_id, f"✨ У вас мэтч с {matched_user_name}! Теперь вы можете общаться.")
                add_notification(liked_user_id, f"✨ У вас мэтч с {user_name}! Теперь вы можете общаться.")


@app.route('/')
def home():
    user_id = request.cookies.get('user_id')
    has_profile = any(p.get('user_id') == user_id for p in profiles) if user_id else False
    user_notifications = notifications.get(user_id, [])
    unread_notifications = [
        n for n in user_notifications
        if datetime.now() - n['timestamp'] < timedelta(minutes=5)
    ]
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Знакомства в кафе</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 20px; }
                h1 { color: #ff6b6b; }
                .button-container { display: flex; flex-direction: column; align-items: center; max-width: 300px; margin: 20px auto; gap: 10px; }
                .modern-btn {
                    background: linear-gradient(90deg, #ff6b6b 0%, #ffb86b 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(255,107,107,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    width: 100%;
                    text-decoration: none;
                    display: block;
                }
                .modern-btn:hover {
                    box-shadow: 0 8px 24px rgba(255,107,107,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
                .notification { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #4CAF50; color: white; padding: 15px 25px; border-radius: 30px; animation: fadeInOut 4s forwards; }
                @keyframes fadeInOut {
                    0% { opacity: 0; top: 0; }
                    10% { opacity: 1; top: 20px; }
                    90% { opacity: 1; top: 20px; }
                    100% { opacity: 0; top: 0; }
                }
            </style>
        </head>
        <body>
            {% for notification in unread_notifications %}
                <div class="notification">{{ notification.message }}</div>
            {% endfor %}

            <h1>Добро пожаловать в наше кафе!</h1>
            <p>Здесь вы можете найти интересных людей.</p>

            <div class="button-container">
                {% if not has_profile %}
                    <a href="/create" class="modern-btn">Создать анкету</a>
                {% else %}
                    <a href="/my_profile" class="modern-btn">Моя анкета</a>
                {% endif %}
                <a href="/visitors" class="modern-btn">Посмотреть посетителей</a>
                <a href="/my_likes" class="modern-btn">Мои лайки</a>
                <a href="/my_matches" class="modern-btn">Мои мэтчи</a>
            </div>
        </body>
        </html>
    ''', has_profile=has_profile, user_id=user_id, unread_notifications=unread_notifications)


@app.route('/create', methods=['GET', 'POST'])
def create_profile():
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
    if any(p.get('user_id') == user_id for p in profiles):
        return redirect(url_for('my_profile'))
    if request.method == 'POST':
        photo = request.files['photo']
        if photo and photo.filename:
            filename = f"{user_id}_{photo.filename}"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
            profile = {
                'id': len(profiles),
                'user_id': user_id,
                'name': request.form['name'],
                'age': request.form['age'],
                'hobbies': request.form['hobbies'],
                'goal': request.form['goal'],
                'photo': filename,
                'likes': 0
            }
            profiles.append(profile)
            resp = make_response(redirect(url_for('view_profile', id=profile['id'])))
            resp.set_cookie('user_id', user_id)
            return resp
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Создать анкету</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px; }
                input, textarea { width: 100%; padding: 10px; margin: 10px 0; }
                .modern-btn {
                    background: linear-gradient(90deg, #ff6b6b 0%, #ffb86b 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(255,107,107,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                }
                .modern-btn:hover {
                    box-shadow: 0 8px 24px rgba(255,107,107,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
                .back-btn {
                    background: linear-gradient(90deg, #6c757d 0%, #495057 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(108,117,125,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                }
                .back-btn:hover {
                    box-shadow: 0 8px 24px rgba(108,117,125,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
            </style>
        </head>
        <body>
            <h2>Создать анкету</h2>
            <form method="post" enctype="multipart/form-data">
                <input type="text" name="name" placeholder="Ваше имя" required>
                <input type="number" name="age" placeholder="Ваш возраст" required>
                <textarea name="hobbies" placeholder="Ваши увлечения" required></textarea>
                <textarea name="goal" placeholder="Цель знакомства" required></textarea>
                <input type="file" name="photo" accept="image/*" required>
                <button type="submit" class="modern-btn">Создать</button>
            </form>
            <a href="/" class="back-btn">← На главную</a>
        </body>
        </html>
    ''')


@app.route('/my_profile')
def my_profile():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect(url_for('home'))

    profile = next((p for p in profiles if p['user_id'] == user_id), None)
    if not profile:
        return redirect(url_for('create'))

    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Моя анкета</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 20px; }
                .card { background: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; padding: 20px; }
                img { max-width: 100%; border-radius: 10px; }
                .modern-btn {
                    background: linear-gradient(90deg, #ff6b6b 0%, #ffb86b 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(255,107,107,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    margin: 5px;
                }
                .modern-btn:hover {
                    box-shadow: 0 8px 24px rgba(255,107,107,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
                .back-btn {
                    background: linear-gradient(90deg, #6c757d 0%, #495057 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(108,117,125,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                }
                .back-btn:hover {
                    box-shadow: 0 8px 24px rgba(108,117,125,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
            </style>
        </head>
        <body>
            <div class="card">
                <img src="{{ url_for('static', filename='uploads/' + profile.photo) }}" alt="Фото">
                <h2>{{ profile.name }}, {{ profile.age }}</h2>
                <p><strong>Увлечения:</strong> {{ profile.hobbies }}</p>
                <p><strong>Цель:</strong> {{ profile.goal }}</p>
                <p>❤️ {{ profile.likes }} лайков</p>
                <form action="/delete/{{ profile.id }}" method="post">
                    <button type="submit" class="modern-btn" style="background: #b00020;">Удалить анкету</button>
                </form>
                <a href="/" class="back-btn">← На главную</a>
            </div>
        </body>
        </html>
    ''', profile=profile)


@app.route('/my_likes')
def my_likes():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect(url_for('home'))

    liked_profiles = []
    for profile_id in likes.get(user_id, []):
        if profile_id < len(profiles):
            liked_profiles.append(profiles[profile_id])

    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Мои лайки</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                .like-card { background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
                .like-card img { max-width: 100px; border-radius: 10px; margin-right: 15px; }
                .like-card h2 { margin: 0; }
                .like-card a { color: #ff6b6b; text-decoration: none; }
                .back-btn {
                    background: linear-gradient(90deg, #6c757d 0%, #495057 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(108,117,125,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                }
                .back-btn:hover {
                    box-shadow: 0 8px 24px rgba(108,117,125,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
            </style>
        </head>
        <body>
            <h1>Мои лайки</h1>
            {% if liked_profiles %}
                {% for profile in liked_profiles %}
                    <div class="like-card">
                        <img src="{{ url_for('static', filename='uploads/' + profile.photo) }}" alt="Фото">
                        <h2>{{ profile.name }}, {{ profile.age }}</h2>
                        <a href="/profile/{{ profile.id }}">Посмотреть анкету</a>
                    </div>
                {% endfor %}
            {% else %}
                <p>Вы пока никого не лайкнули.</p>
            {% endif %}
            <a href="/" class="back-btn">← На главную</a>
        </body>
        </html>
    ''', liked_profiles=liked_profiles)


@app.route('/profile/<int:id>')
def view_profile(id):
    if id >= len(profiles):
        return "Анкета не найдена", 404
    user_id = request.cookies.get('user_id')
    profile = profiles[id]
    is_owner = profile.get('user_id') == user_id
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Анкета</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 20px; }
                .card { background: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; padding: 20px; }
                img { max-width: 100%; border-radius: 10px; }
                .modern-btn {
                    background: linear-gradient(90deg, #ff6b6b 0%, #ffb86b 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(255,107,107,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    margin: 5px;
                }
                .modern-btn:hover {
                    box-shadow: 0 8px 24px rgba(255,107,107,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
                .back-btn {
                    background: linear-gradient(90deg, #6c757d 0%, #495057 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(108,117,125,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                }
                .back-btn:hover {
                    box-shadow: 0 8px 24px rgba(108,117,125,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
            </style>
        </head>
        <body>
            <div class="card">
                <img src="{{ url_for('static', filename='uploads/' + profile.photo) }}" alt="Фото">
                <h2>{{ profile.name }}, {{ profile.age }}</h2>
                <p><strong>Увлечения:</strong> {{ profile.hobbies }}</p>
                <p><strong>Цель:</strong> {{ profile.goal }}</p>
                <p>❤️ {{ profile.likes }} лайков</p>
                {% if not is_owner %}
                    <form action="/like/{{ profile.id }}" method="post">
                        <button type="submit" class="modern-btn">❤️ Лайк</button>
                    </form>
                {% endif %}
                {% if is_owner %}
                    <form action="/delete/{{ profile.id }}" method="post">
                        <button type="submit" class="modern-btn" style="background: #b00020;">Удалить анкету</button>
                    </form>
                {% endif %}
                <a href="/visitors" class="back-btn">← Назад к посетителям</a>
            </div>
        </body>
        </html>
    ''', profile=profile, is_owner=is_owner)


@app.route('/like/<int:id>', methods=['POST'])
def like_profile(id):
    if id >= len(profiles):
        return "Анкета не найдена", 404
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect(url_for('home'))
    if profiles[id]['user_id'] == user_id:
        return "Нельзя лайкнуть свою анкету", 400
    if id not in likes[user_id]:
        likes[user_id].append(id)
        profiles[id]['likes'] += 1
        check_for_matches(user_id)
    return redirect(url_for('view_profile', id=id))


@app.route('/delete/<int:id>', methods=['POST'])
def delete_profile(id):
    if id >= len(profiles):
        return "Анкета не найдена", 404
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect(url_for('home'))
    if profiles[id]['user_id'] != user_id:
        return "Нельзя удалить чужую анкету", 403

    # Удаляем фото
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], profiles[id]['photo']))
    except:
        pass

    # Удаляем из всех списков
    profiles.pop(id)

    # Обновляем индексы в likes
    for user_likes in likes.values():
        for i, liked_id in enumerate(user_likes):
            if liked_id > id:
                user_likes[i] = liked_id - 1
            elif liked_id == id:
                user_likes.remove(liked_id)
                break

    return redirect(url_for('home'))


@app.route('/my_matches')
def my_matches():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect(url_for('home'))
    matched_profiles = []
    for matched_user_id in matches.get(user_id, []):
        profile = next((p for p in profiles if p['user_id'] == matched_user_id), None)
        if profile:
            matched_profiles.append(profile)
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Мои мэтчи</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                .match-card { background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }
                .modern-btn {
                    background: linear-gradient(90deg, #4CAF50 0%, #81c784 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(76,175,80,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    margin-top: 10px;
                    text-decoration: none;
                    display: inline-block;
                }
                .modern-btn:hover {
                    box-shadow: 0 8px 24px rgba(76,175,80,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
                .back-btn {
                    background: linear-gradient(90deg, #6c757d 0%, #495057 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(108,117,125,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                }
                .back-btn:hover {
                    box-shadow: 0 8px 24px rgba(108,117,125,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
            </style>
        </head>
        <body>
            <h1>Мои мэтчи</h1>
            {% if matched_profiles %}
                {% for profile in matched_profiles %}
                    <div class="match-card">
                        <h2>{{ profile.name }}, {{ profile.age }}</h2>
                        <a href="/chat/{{ profile.user_id }}" class="modern-btn">Чат</a>
                    </div>
                {% endfor %}
            {% else %}
                <p>У вас пока нет мэтчей.</p>
            {% endif %}
            <a href="/" class="back-btn">← На главную</a>
        </body>
        </html>
    ''', matched_profiles=matched_profiles)


@app.route('/chat/<string:other_user_id>')
def chat(other_user_id):
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect(url_for('home'))
    if other_user_id not in matches.get(user_id, []):
        return "Чат доступен только для мэтчей", 403
    other_profile = next((p for p in profiles if p['user_id'] == other_user_id), None)
    if not other_profile:
        return "Пользователь не найден", 404
    chat_key = "_".join(sorted([user_id, other_user_id]))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Чат</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                .message { margin: 10px; padding: 10px; border-radius: 10px; max-width: 70%; }
                .my-message { background: #dcf8c6; margin-left: auto; }
                .their-message { background: white; margin-right: auto; }
                .back-btn {
                    background: linear-gradient(90deg, #6c757d 0%, #495057 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(108,117,125,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    text-decoration: none;
                    display: inline-block;
                    margin-bottom: 20px;
                }
                .back-btn:hover {
                    box-shadow: 0 8px 24px rgba(108,117,125,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
                .modern-btn {
                    background: linear-gradient(90deg, #ff6b6b 0%, #ffb86b 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(255,107,107,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    margin-top: 10px;
                }
                .modern-btn:hover {
                    box-shadow: 0 8px 24px rgba(255,107,107,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
                #messages { min-height: 200px; }
                #chat-form { display: flex; flex-direction: column; align-items: stretch; margin-top: 20px; }
                #message-input {
                    width: 100%;
                    padding: 12px;
                    font-size: 1.1em;
                    border-radius: 10px;
                    border: 1px solid #ddd;
                    min-height: 48px;
                    margin-bottom: 10px;
                    resize: none;
                }
            </style>
            <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
        </head>
        <body>
            <a href="/my_matches" class="back-btn">← Назад к мэтчам</a>
            <h1>Чат с {{ other_profile.name }}</h1>
            <div id="messages"></div>
            <form id="chat-form" autocomplete="off">
                <textarea id="message-input" placeholder="Ваше сообщение..." required></textarea>
                <button type="submit" class="modern-btn">Отправить</button>
            </form>
            <script>
                const user_id = "{{ user_id }}";
                const chat_key = "{{ chat_key }}";
                const socket = io();

                function addMessage(msg, isMine) {
                    const div = document.createElement('div');
                    div.className = 'message ' + (isMine ? 'my-message' : 'their-message');
                    div.textContent = msg;
                    document.getElementById('messages').appendChild(div);
                    window.scrollTo(0, document.body.scrollHeight);
                }

                // Загрузка истории
                fetch('/chat_history/{{ other_user_id }}')
                    .then(r => r.json())
                    .then(data => {
                        data.forEach(m => addMessage(m.text, m.sender === user_id));
                    });

                socket.emit('join', {room: chat_key});

                socket.on('message', function(data) {
                    addMessage(data.text, data.sender === user_id);
                });

                document.getElementById('chat-form').onsubmit = function(e) {
                    e.preventDefault();
                    const input = document.getElementById('message-input');
                    const msg = input.value;
                    if (msg.trim()) {
                        socket.emit('send_message', {room: chat_key, text: msg, sender: user_id});
                        input.value = '';
                    }
                };
            </script>
        </body>
        </html>
    ''', other_profile=other_profile, user_id=user_id, chat_key=chat_key, other_user_id=other_user_id)


@app.route('/chat_history/<string:other_user_id>')
def chat_history(other_user_id):
    user_id = request.cookies.get('user_id')
    chat_key = tuple(sorted([user_id, other_user_id]))
    return jsonify(messages[chat_key]) if chat_key in messages else jsonify([])


@socketio.on('join')
def on_join(data):
    join_room(data['room'])


@socketio.on('send_message')
def handle_send_message(data):
    room = data['room']
    text = data['text']
    sender = data['sender']
    user_ids = room.split('_')
    chat_key = tuple(sorted(user_ids))
    messages[chat_key].append({
        'sender': sender,
        'text': text,
        'timestamp': datetime.now()
    })
    emit('message', {'text': text, 'sender': sender}, room=room)


@app.route('/visitors')
def view_visitors():
    user_id = request.cookies.get('user_id')
    other_profiles = [p for p in profiles if p.get('user_id') != user_id]
    liked_ids = set(likes.get(user_id, []))
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Посетители кафе</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                .visitor-card { 
                    background: white; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                    padding: 20px; 
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                }
                .visitor-card img { 
                    max-width: 80px; 
                    border-radius: 10px; 
                    margin-right: 15px;
                    object-fit: cover;
                    height: 80px;
                }
                .visitor-info { flex: 1; }
                .visitor-card h2 { margin: 0 0 5px 0; }
                .visitor-card p { margin: 5px 0; color: #666; }
                .like-btn {
                    background: none;
                    border: none;
                    cursor: pointer;
                    outline: none;
                    font-size: 2em;
                    margin-left: 10px;
                    transition: transform 0.1s;
                }
                .like-btn:active { transform: scale(1.2); }
                .like-heart {
                    color: #bbb;
                    transition: color 0.2s;
                }
                .like-heart.liked {
                    color: #ff6b6b;
                }
                .back-btn {
                    background: linear-gradient(90deg, #6c757d 0%, #495057 100%);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    box-shadow: 0 4px 14px rgba(108,117,125,0.2);
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: box-shadow 0.2s, transform 0.2s;
                    text-decoration: none;
                    display: inline-block;
                    margin-top: 20px;
                }
                .back-btn:hover {
                    box-shadow: 0 8px 24px rgba(108,117,125,0.3);
                    transform: translateY(-2px) scale(1.03);
                }
                .visitor-count {
                    font-size: 0.9em;
                    color: #888;
                    margin-bottom: 10px;
                    text-align: left;
                }
            </style>
            <script>
                function toggleLike(profileId, btn) {
                    fetch('/toggle_like/' + profileId, {method: 'POST'})
                        .then(r => r.json())
                        .then(data => {
                            if (data.liked) {
                                btn.classList.add('liked');
                            } else {
                                btn.classList.remove('liked');
                            }
                        });
                }
            </script>
        </head>
        <body>
            <div class="visitor-count">Посетителей: {{ other_profiles|length }}</div>
            <h1>Посетители кафе</h1>
            {% if other_profiles %}
                {% for profile in other_profiles %}
                    <div class="visitor-card">
                        <img src="{{ url_for('static', filename='uploads/' + profile.photo) }}" alt="Фото">
                        <div class="visitor-info">
                            <h2>{{ profile.name }}, {{ profile.age }}</h2>
                            <p>{{ profile.hobbies[:50] }}{% if profile.hobbies|length > 50 %}...{% endif %}</p>
                            <a href="/profile/{{ profile.id }}">Посмотреть анкету</a>
                        </div>
                        <button class="like-btn" title="Лайк" onclick="toggleLike({{ profile.id }}, this.querySelector('span'))">
                            <span class="like-heart{% if profile.id in liked_ids %} liked{% endif %}">&#10084;</span>
                        </button>
                    </div>
                {% endfor %}
            {% else %}
                <p>Пока нет других посетителей.</p>
            {% endif %}
            <a href="/" class="back-btn">← На главную</a>
        </body>
        </html>
    ''', other_profiles=other_profiles, liked_ids=liked_ids)
@app.route('/toggle_like/<int:profile_id>', methods=['POST'])
def toggle_like(profile_id):
    user_id = request.cookies.get('user_id')
    if not user_id or profile_id >= len(profiles) or profiles[profile_id]['user_id'] == user_id:
        return jsonify({'liked': False})
    if profile_id in likes[user_id]:
        likes[user_id].remove(profile_id)
        profiles[profile_id]['likes'] = max(0, profiles[profile_id]['likes'] - 1)
        liked = False
    else:
        likes[user_id].append(profile_id)
        profiles[profile_id]['likes'] += 1
        check_for_matches(user_id)
        liked = True
    return jsonify({'liked': liked})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)