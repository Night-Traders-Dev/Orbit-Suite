import json
import requests
import socket
import threading
from core.ioutil import fetch_chain, save_chain, load_nodes
from core.logutil import log_node_activity

def ping_node(address):
    try:
        response = requests.get(f"http://{address}/ping", timeout=3)
        return response.status_code == 200
    except:
        return False

def send_block_to_node(address, block_data):
    try:
        res = requests.post(f"http://{address}/api/receive_block", json=block_data, timeout=5)
        return res.status_code == 200
    except Exception as e:
        print(f"Failed to send block to {address}: {e}")
        return False

def send_block(peer_address, block):
    host, port = peer_address.split(":")
    port = int(port)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))
            payload = {
                "type": "block",
                "data": block.to_dict() if hasattr(block, "to_dict") else block,
            }
            s.sendall((json.dumps(payload) + "\n").encode())
            s.shutdown(socket.SHUT_WR)
    except (ConnectionRefusedError, socket.timeout, socket.error) as e:
        raise RuntimeError(f"Failed to send block to {peer_address}: {e}")

def start_listener(node_id):
    node_data = load_nodes().get(node_id)
    if not node_data:
        log_node_activity(node_id, "Start Listener", f"No config found for node {node_id}")
        return

    address = node_data["address"]
    port = node_data["port"]
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((address, port))
    server.listen()
    log_node_activity(node_id, "Start Listener", f"[Listener] {node_id} listening on {address}:{port}...")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_connection, args=(conn, addr, node_id), daemon=True).start()

def handle_connection(conn, addr, node_id):
    try:
        from blockchain.orbitutil import update_trust, update_uptime

        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in chunk:
                break

        if not data:
            return

        msg = json.loads(data.decode())

        if msg.get("type") == "block":
            block_data = msg["data"]
            chain = fetch_chain()

            if any(b["hash"] == block_data["hash"] for b in chain):
                log_node_activity(node_id, "Handle Connection", f"[{node_id}] Duplicate block {block_data['hash']}, ignoring.")
                update_trust(node_id, success=True)
                update_uptime(node_id, is_online=True)
                return

            if not chain and block_data["index"] == 0:
                log_node_activity(node_id, "Handle Connection", f"[{node_id}] Genesis block accepted.")
                save_chain([block_data])
                return

            if chain and block_data["previous_hash"] == chain[-1]["hash"]:
                log_node_activity(node_id, "Handle Connection", f"[{node_id}] Block accepted at index {block_data['index']}.")
                chain.append(block_data)
                save_chain(chain)
                update_trust(node_id, success=True)
                update_uptime(node_id, is_online=True)
                receive_block(block_data)
                return

            # Attempt backtrack
            for i in range(len(chain) - 1, -1, -1):
                if chain[i]["hash"] == block_data["previous_hash"]:
                    log_node_activity(node_id, "Handle Connection", f"[{node_id}] Block attached after backtracking to index {i}.")
                    new_chain = chain[:i+1] + [block_data]
                    save_chain(new_chain)
                    update_trust(node_id, success=True)
                    update_uptime(node_id, is_online=True)
                    receive_block(block_data)
                    return

            log_node_activity(node_id, "Handle Connection", f"[{node_id}] Rejected block: previous hash mismatch.\n"
                  f"Expected: {chain[-1]['hash'] if chain else 'None'}, "
                  f"got: {block_data['previous_hash']}")
            update_trust(node_id, success=False)
            update_uptime(node_id, is_online=True)

    except Exception as e:
        print(f"[{node_id}] Error handling connection from {addr}: {e}")
    finally:
        conn.close()
