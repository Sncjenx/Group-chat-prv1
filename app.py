from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_socketio import SocketIO, emit
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape
import random, json, os


APP_SECRET = "change_this_in_production_to_a_strong_random_value"
USERS_FILE = "users.json"
HISTORY_FILE = "chat_history.json"
HISTORY_LIMIT = 200

app = Flask(__name__)
app.secret_key = APP_SECRET
app.permanent_session_lifetime = timedelta(hours=2)
socketio = SocketIO(app, cors_allowed_origins="*")  

connected_users = {}   
users_colors = {}      

def load_json_or_empty(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def load_users():
    return load_json_or_empty(USERS_FILE)

def save_users(users):
    save_json(USERS_FILE, users)

def load_history():
    return load_json_or_empty(HISTORY_FILE).get("messages", [])

def save_history(history):
    save_json(HISTORY_FILE, {"messages": history[-HISTORY_LIMIT:]})

def assign_color(nickname):
    if nickname not in users_colors:
        users_colors[nickname] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    return users_colors[nickname]


_users = load_users()
_history = load_history()


if isinstance(_users, dict):
    for n in _users:
        if isinstance(_users[n], dict) and "color" in _users[n]:
            users_colors[n] = _users[n]["color"]


@app.route("/", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        password = request.form.get("password", "")
        if not nickname or not password:
            message = "Pseudo et mot de passe requis."
        else:
            nickname_safe = escape(nickname)
            users = load_users()
           
            if nickname_safe in users:
                stored = users[nickname_safe]
                if isinstance(stored, dict):
                    stored_hash = stored.get("pwd")
                else:
                    stored_hash = stored
                if stored_hash and check_password_hash(stored_hash, password):
                    session.permanent = True
                    session["nickname"] = nickname_safe
                    flash("Connexion réussie.", "success")
                    return redirect(url_for("chat"))
                else:
                    message = "Mot de passe incorrect."
            else:
                
                hashed = generate_password_hash(password)
                color = assign_color(nickname_safe)
                users[nickname_safe] = {"pwd": hashed, "color": color}
                save_users(users)
                session.permanent = True
                session["nickname"] = nickname_safe
                flash("Compte créé et connexion réussie.", "success")
                return redirect(url_for("chat"))
    return render_template("login.html", message=message)

@app.route("/chat")
def chat():
    if "nickname" not in session:
        return redirect(url_for("login"))
    nickname = session["nickname"]
    history = load_history()
    return render_template("index.html", nickname=nickname, history=history)

@app.route("/logout")
def logout():
    session.pop("nickname", None)
    flash("Déconnecté.", "info")
    return redirect(url_for("login"))

@socketio.on("connect")
def on_connect():
   
    print("Client connected.")

@socketio.on("join")
def on_join(data):
    try:
        nickname = escape(data.get("nickname", ""))
    except Exception:
        nickname = "Anonyme"
    if not nickname:
        nickname = "Anonyme"
    connected_users[request.sid] = nickname
    color = assign_color(nickname)
  
    users = load_users()
    entry = users.get(nickname)
    if isinstance(entry, dict):
        entry["color"] = color
    elif entry:
        users[nickname] = {"pwd": entry, "color": color}
    else:
        users[nickname] = {"pwd": None, "color": color}
    save_users(users)
    
    payload = {"nickname": "", "message": f"🟢 {nickname} a rejoint le chat.", "color": "#ffffff"}
    _history.append(payload)
    save_history(_history)
    emit("message", payload, broadcast=True)

@socketio.on("message")
def on_message(data):
    
    if isinstance(data, dict):
        raw_user = data.get("user", "")
        raw_text = data.get("text", "")
    else:
        
        raw_user = connected_users.get(request.sid, "Anonyme")
        raw_text = str(data)
    user = escape(str(raw_user))
    text = escape(str(raw_text))
    color = assign_color(user)
    payload = {"nickname": user, "message": text, "color": color}
    _history.append(payload)
    save_history(_history)
    emit("message", payload, broadcast=True)

@socketio.on("disconnect")
def on_disconnect():
    nickname = connected_users.pop(request.sid, None)
    if not nickname:
        nickname = "Un utilisateur"
    payload = {"nickname": "", "message": f"🔴 {nickname} a quitté le chat.", "color": "#ffffff"}
    _history.append(payload)
    save_history(_history)
    emit("message", payload, broadcast=True)

# --- Run ---
if __name__ == "__main__":
    print("🚀 Serveur final sur http://127.0.0.1:5000")
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)

### darkmode ###
@app.context_processor
def inject_darkmode():
    return dict(darkmode_enabled=True)
@app.route("/toggle_darkmode")
def toggle_darkmode():
    darkmode = session.get("darkmode", False)
    session["darkmode"] = not darkmode
    return redirect(request.referrer or url_for("chat"))
### end darkmode ###
