import os
import json

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def logout_user(user_id, session_file="data/active_sessions.json"):
    if not os.path.exists(session_file):
        return

    with open(session_file, "r") as f:
        sessions = json.load(f)

    if user_id in sessions:
        del sessions[user_id]
        with open(session_file, "w") as f:
            json.dump(sessions, f, indent=4)
    else:
        print(f"User {user_id} was not in active sessions.")
