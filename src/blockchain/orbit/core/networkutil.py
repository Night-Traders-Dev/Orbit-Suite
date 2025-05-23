# networkutil.py
import json
import requests
import socket
import threading

def ping_node(address):
    try:
        response = requests.get(f"http://{address}/ping", timeout=3)
        return response.status_code == 200
    except:
        return False

def send_block_to_node(address, block_data):
    try:
        res = requests.post(f"http://{address}/receive_block", json=block_data, timeout=5)
        return res.status_code == 200
    except Exception as e:
        print(f"Failed to send block to {address}: {e}")
        return False

def send_block(peer_address, block):
    host, port = peer_address.split(":")
    port = int(port)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)  # Avoid hangs on unresponsive nodes
            s.connect((host, port))
            payload = {
                "type": "block",
                "data": block.to_dict() if hasattr(block, "to_dict") else block
            }
            s.sendall(json.dumps(payload).encode())

            s.shutdown(socket.SHUT_WR)
    except (ConnectionRefusedError, socket.timeout, socket.error) as e:
        raise RuntimeError(f"Failed to send block to {peer_address}: {e}")

def start_listener(node_id):
    node_data = load_nodes().get(node_id)
    if not node_data:
        print(f"No config found for node {node_id}")
        return

    address = node_data["address"]
    port = node_data["port"]
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((address, port))
    server.listen()
    print(f"[Listener] {node_id} listening on {address}:{port}...")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_connection, args=(conn, addr, node_id), daemon=True).start()

def handle_connection(conn, addr, node_id):
    try:
        from blockchain.blockutil import load_chain, save_chain
        from blockchain.orbitutil import update_trust, update_uptime
        data = conn.recv(4096)
        if not data:
            return

        msg = json.loads(data.decode())

        if msg.get("type") == "block":
            block_data = msg["data"]
            chain = load_chain()

            if any(b["hash"] == block_data["hash"] for b in chain):
                update_trust(node_id, success=False)
                update_uptime(node_id, is_online=True)
                return

            if not chain and block_data["index"] == 0:
                save_chain([block_data])
                return

            if chain and block_data["previous_hash"] == chain[-1]["hash"]:
                chain.append(block_data)
                save_chain(chain)
                update_trust(node_id, success=True)
                update_uptime(node_id, is_online=True)

    except Exception as e:
        print(f"[{node_id}] Error handling connection from {addr}: {e}")
    finally:
        conn.close()
