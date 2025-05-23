import os
import time

def log_event(action, username):
    with open("user_activity.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {action} | {username}\n")

def log_node_activity(node_id, action, detail=""):
    with open("node_activity.log", "a") as log:
        log.write(f"{time.time()} | Node {node_id} | {action} | {detail}\n")
