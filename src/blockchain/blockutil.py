import hashlib
import json
import time
import os
import socket
import threading

from orbitutil import load_nodes, propose_block
from configutil import NodeConfig, LedgerConfig, TXConfig

node_config = NodeConfig()
ledger_config = LedgerConfig()

CHAIN_FILE = ledger_config.blockchaindb
HOST = str(node_config.address)
PORT = node_config.port

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

def calculate_hash(index, previous_hash, timestamp, transactions, validator="", merkle_root="", nonce=0, metadata=None):
    block_content = {
        "index": index,
        "previous_hash": previous_hash,
        "timestamp": timestamp,
        "transactions": transactions,
        "validator": validator,
        "merkle_root": merkle_root,
        "nonce": nonce,
        "metadata": metadata or {}
    }
    block_string = json.dumps(block_content, sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()

def create_genesis_block():
    genesis_block = TXConfig.Block(
        index=0,
        timestamp=time.time(),
        transactions=[],
        previous_hash="0",
        hash="",
        validator="genesis",
        signatures={},
        merkle_root="",
        nonce=0,
        metadata={"note": "genesis block"}
    )
    genesis_block.hash = calculate_hash(
        genesis_block.index,
        genesis_block.previous_hash,
        genesis_block.timestamp,
        [],
        genesis_block.validator,
        genesis_block.merkle_root,
        genesis_block.nonce,
        genesis_block.metadata
    )
    return genesis_block.to_dict()

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

    if block["index"] != last_block["index"] + 1:
        print("Rejected block: invalid index.")
        return False

    if block["previous_hash"] != last_block["hash"]:
        print("Rejected block: previous hash mismatch.")
        print(f"Expected: {last_block['hash']}, got: {block['previous_hash']}")
        return False

    recalculated_hash = calculate_hash(
        block["index"],
        block["previous_hash"],
        block["timestamp"],
        block["transactions"],
        block.get("validator", ""),
        block.get("merkle_root", ""),
        block.get("nonce", 0),
        block.get("metadata", {})
    )

    if recalculated_hash != block["hash"]:
        print("Rejected block: invalid hash.")
        return False

    chain.append(block)
    save_chain(chain)
    print(f"Block {block['index']} received and added to Orbit chain.")
    return True

def send_block(peer_address, block):
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
        port = info.get("port")
        if address and port:
            full_address = f"{address}:{port}"
            try:
                print(f"Block sent to {node_id} at {full_address}")
                send_block(full_address, block)
            except Exception as e:
                print(f"Failed to send block to {node_id}: {e}")


def add_block(transactions, node_id="Node1"):
    chain = load_chain()
    last_block = chain[-1]

    tx_objs = [TXConfig.Transaction.from_dict(tx) for tx in transactions]

    new_block = TXConfig.Block(
        index=len(chain),
        timestamp=time.time(),
        transactions=tx_objs,
        previous_hash=last_block["hash"],
        hash="",
        validator=node_id,
        signatures={},
        merkle_root="",  # Will auto-compute if empty
        nonce=0,
        metadata={"lockup_rewards": [], "version": "1.0"}
    )

    new_block.hash = calculate_hash(
        new_block.index,
        new_block.previous_hash,
        new_block.timestamp,
        [tx.to_dict() for tx in new_block.transactions],
        new_block.validator,
        new_block.merkle_root,
        new_block.nonce,
        new_block.metadata
    )

    block_data = new_block.to_dict()

    if propose_block(node_id, block_data):
        broadcast_block(block_data)
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
            current["transactions"],
            current.get("validator", ""),
            current.get("merkle_root", ""),
            current.get("nonce", 0),
            current.get("metadata", {})
        )
        if current["hash"] != recalculated_hash:
            return False
        if current["previous_hash"] != previous["hash"]:
            return False
    return True
