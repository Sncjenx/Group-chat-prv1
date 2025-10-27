
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape
from datetime import timedelta
import json, os, random

BASE_DIR = os.path.dirname(__file__)
USERS_FILE = os.path.join(BASE_DIR, "users.json")
HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


_users = load_json(USERS_FILE, {})
_history = load_json(HISTORY_FILE, {"messages": []})
HISTORY_LIMIT = 500

def assign_color(nick):
    # stable-ish color by hash
    h = abs(hash(nick)) % 0xFFFFFF
    return "#{:06x}".format(h)


app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "change_this_to_a_strong_secret_in_prod"
app.permanent_session_lifetime = timedelta(hours=6)
socketio = SocketIO(app, cors_allowed_origins="*")

connected = {}  # sid -> nickname

@app.route("/", methods=["GET", "POST"])
def login():
    message = None
    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        password = request.form.get("password", "")

        if not nickname or not password:
            message = "Veuillez fournir un pseudo et un mot de passe."
        else:
            nickname_safe = escape(nickname)
            user = _users.get(nickname_safe)
            if user:
                ## login
                if check_password_hash(user.get("pwd", ""), password):
                    session.permanent = True
                    session["nickname"] = nickname_safe
                    flash("Connexion réussie.", "success")
                    return redirect(url_for("chat"))
                else:
                    message = "Mot de passe incorrect."
            else:
                ## register
                hashed = generate_password_hash(password)
                color = assign_color(nickname_safe)
                _users[nickname_safe] = {"pwd": hashed, "color": color}
                save_json(USERS_FILE, _users)
                session.permanent = True
                session["nickname"] = nickname_safe
                flash("Compte créé et connecté.", "success")
                return redirect(url_for("chat"))

    return render_template("login.html", message=message)

@app.route("/chat")
def chat():
    if "nickname" not in session:
        return redirect(url_for("login"))
    nickname = session["nickname"]
    ## pass history messages (list of dicts)
    history = _history.get("messages", [])[-200:]
    return render_template("index.html", nickname=nickname, history=history)

@app.route("/logout")
def logout():
    session.clear()
    flash("Déconnecté.", "info")
    return redirect(url_for("login"))

## Socket events
@socketio.on("connect")
def on_connect():
    ## nothing special; client will emit join
    print("Client connected")

@socketio.on("join")
def on_join(data):
    nick = escape(data.get("nickname") or session.get("nickname") or "Anonyme")
    connected[request.sid] = nick
    color = _users.get(nick, {}).get("color") or assign_color(nick)

    ## system message
    sys_msg = {"nickname": "", "message": f"🟢 {nick} a rejoint le chat.", "color": "#aaaaaa"}
    _history["messages"].append(sys_msg)
    if len(_history["messages"]) > HISTORY_LIMIT:
        _history["messages"] = _history["messages"][-HISTORY_LIMIT:]
    save_json(HISTORY_FILE, _history)

    emit("message", sys_msg, broadcast=True)

@socketio.on("message")
def on_message(data):
   
    if isinstance(data, dict):
        nick = escape(data.get("nickname") or data.get("user") or connected.get(request.sid) or "Anonyme")
        text = data.get("message") or data.get("text") or ""
    else:
        nick = connected.get(request.sid, session.get("nickname", "Anonyme"))
        text = str(data)

    text = escape(text)
    color = _users.get(nick, {}).get("color") or assign_color(nick)

    payload = {"nickname": nick, "message": text, "color": color}
    _history["messages"].append(payload)
    if len(_history["messages"]) > HISTORY_LIMIT:
        _history["messages"] = _history["messages"][-HISTORY_LIMIT:]
    save_json(HISTORY_FILE, _history)

    emit("message", payload, broadcast=True)

@socketio.on("disconnect")
def on_disconnect():
    nick = connected.pop(request.sid, None) or session.get("nickname")
    if nick:
        sys_msg = {"nickname": "", "message": f"🔴 {nick} a quitté le chat.", "color": "#aaaaaa"}
        _history["messages"].append(sys_msg)
        if len(_history["messages"]) > HISTORY_LIMIT:
            _history["messages"] = _history["messages"][-HISTORY_LIMIT:]
        save_json(HISTORY_FILE, _history)
        emit("message", sys_msg, broadcast=True)
    print("Client disconnected")

if __name__ == "__main__":
    print("🚀 Serveur (dark theme + comptes) en local: http://127.0.0.1:5000")
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
