# client.py
import socketio, threading
from getpass import getpass

sio = socketio.Client(reconnection=True)
nickname = input("Pseudo: ").strip()

@sio.event
def connect():
    print("[+] Connecté au serveur")
    sio.emit('join', {'nickname': nickname})

@sio.event
def message(data):
    # data is dict { nickname, message, color } or system { nickname:"", message: "..."}
    if isinstance(data, dict) and 'message' in data:
        if data.get('nickname'):
            print(f"{data['nickname']}: {data['message']}")
        else:
            print(f"* {data['message']}")
    else:
        print(data)

@sio.event
def disconnect():
    print("[-] Déconnecté du serveur")

def send_loop():
    while True:
        try:
            txt = input()
            if txt.strip():
                sio.emit('message', {'user': nickname, 'text': txt})
        except (KeyboardInterrupt, EOFError):
            break

if __name__ == "__main__":
    try:
        sio.connect("http://127.0.0.1:5000")
        threading.Thread(target=send_loop, daemon=True).start()
        # keep main alive
        sio.wait()
    except Exception as e:
        print("Erreur de connexion:", e)
