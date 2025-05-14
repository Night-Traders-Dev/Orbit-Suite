# blockutil.py

import hashlib
import json
import time
import os
import socket
import threading
from orbitutil import load_nodes, propose_block

CHAIN_FILE = "data/orbit_chain.json"
HOST = '0.0.0.0'  # Listen on all available interfaces
PORT = 5000       # Default port to listen on


def handle_client(conn, addr):
    try:
        data = conn.recv(4096).decode()
        if not data:
            return
        message = json.loads(data)
        if message.get("type") == "block":
            block = message.get("data")
            print(f"Received block from {addr}")
            receive_block(block)
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        conn.close()


def start_listener():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Listening for incoming blocks on port {PORT}...")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

def calculate_hash(index, previous_hash, timestamp, transactions):
    block_string = f"{index}{previous_hash}{timestamp}{json.dumps(transactions, sort_keys=True)}"
    return hashlib.sha256(block_string.encode()).hexdigest()

def create_genesis_block():
    genesis_block = {
        "index": 0,
        "timestamp": time.time(),
        "transactions": [],
        "previous_hash": "0",
        "hash": "",
    }
    genesis_block["hash"] = calculate_hash(
        genesis_block["index"],
        genesis_block["previous_hash"],
        genesis_block["timestamp"],
        genesis_block["transactions"]
    )
    return genesis_block

def load_chain():
    if not os.path.exists(CHAIN_FILE):
        return [create_genesis_block()]
    with open(CHAIN_FILE, "r") as f:
        return json.load(f)

def save_chain(chain):
    with open(CHAIN_FILE, "w") as f:
        json.dump(chain, f, indent=4)

def get_last_block():
    chain = load_chain()
    return chain[-1]

def receive_block(block):
    chain = load_chain()
    last_block = chain[-1]

    if block["previous_hash"] != last_block["hash"]:
        print("Rejected block: previous hash mismatch.")
        return False

    recalculated_hash = calculate_hash(
        block["index"],
        block["previous_hash"],
        block["timestamp"],
        block["transactions"]
    )

    if recalculated_hash != block["hash"]:
        print("Rejected block: invalid hash.")
        return False

    chain.append(block)
    save_chain(chain)
    print(f"Block {block['index']} received and added to Orbit chain.")
    return True

def send_block(peer_address, block):
    receive_block(block)
    host, port = peer_address.split(":")
    port = int(port)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        data = json.dumps({"type": "block", "data": block})
        s.sendall(data.encode())
        print(f"Block sent to {peer_address}")

def broadcast_block(block, sender_id="Node1"):
    print(f"Broadcasting block {block['index']} to peers...")
    nodes = load_nodes()
    for node_id, info in nodes.items():
        if node_id == sender_id:
            continue
        address = info.get("address")
        if address:
            try:
                send_block(address, block)
                print(f"Block sent to {node_id} at {address}")
            except Exception as e:
                print(f"Failed to send block to {node_id}: {e}")


def add_block(transactions, node_id="Node1"):
    chain = load_chain()
    last_block = chain[-1]
    new_block = {
        "index": len(chain),
        "timestamp": time.time(),
        "transactions": transactions,
        "previous_hash": last_block["hash"],
        "hash": ""
    }

    new_block["hash"] = calculate_hash(
        new_block["index"],
        new_block["previous_hash"],
        new_block["timestamp"],
        new_block["transactions"]
    )

    # Check consensus
    if propose_block(node_id, new_block):
#        chain.append(new_block)
#        save_chain(chain)
#        print(f"Block {new_block['index']} added to Orbit chain.")
        broadcast_block(new_block)
    else:
        print("Block rejected due to failed consensus.")

def is_chain_valid():
    chain = load_chain()
    for i in range(1, len(chain)):
        current = chain[i]
        previous = chain[i - 1]
        recalculated_hash = calculate_hash(
            current["index"],
            current["previous_hash"],
            current["timestamp"],
            current["transactions"]
        )
        if current["hash"] != recalculated_hash:
            return False
        if current["previous_hash"] != previous["hash"]:
            return False
    return True


