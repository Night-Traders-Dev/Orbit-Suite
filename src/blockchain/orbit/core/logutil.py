import os
import time

def log_event(username, action, detail=""):
    with open("user_activity.log", "a") as log:
        log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | Address {username} | {action} | {detail}\n")

def log_node_activity(node_id, action, detail=""):
    with open("node_activity.log", "a") as log:
        log.write(f"{time.time()} | Node {node_id} | {action} | {detail}\n")
