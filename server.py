from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

console_colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF5", "#F5FF33", "#FFFFFF"]
users_colors = {}

chat_history = []

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    for msg in chat_history:
        emit('message', msg)

@socketio.on('message')
def handle_message(msg):

    if ": " in msg:
        nickname, content = msg.split(": ", 1)
        if nickname not in users_colors:
            users_colors[nickname] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        data = {'nickname': nickname, 'message': content, 'color': users_colors[nickname]}
    else:
        data = {'nickname': '', 'message': msg, 'color': '#ffffff'}

    chat_history.append(data)
    if len(chat_history) > 100:
        chat_history.pop(0)

    emit('message', data, broadcast=True)

if __name__ == '__main__':
    print("🚀 Serveur en ligne sur http://127.0.0.1:5000")
    socketio.run(app, debug=True)
