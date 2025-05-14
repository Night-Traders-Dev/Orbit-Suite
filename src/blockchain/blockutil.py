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

def calculate_hash(index, previous_hash, timestamp, transactions):
    block_string = f"{index}{previous_hash}{timestamp}{json.dumps(transactions, sort_keys=True)}"
    return hashlib.sha256(block_string.encode()).hexdigest()

def create_genesis_block():
    genesis_block = TXConfig.Block(
        index=0,
        timestamp=time.time(),
        transactions=[],  # No transactions in the genesis block
        previous_hash="0",  # No previous hash for the genesis block
        hash=""
    )
    genesis_block.hash = calculate_hash(
        genesis_block.index,
        genesis_block.previous_hash,
        genesis_block.timestamp,
        [tx.to_dict() for tx in genesis_block.transactions]  # Convert transactions to dict
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
                print(f"Block sent to {node_id} at {address}")
                send_block(address, block)
            except Exception as e:
                print(f"Failed to send block to {node_id}: {e}")

def add_block(transactions, node_id="Node1"):
    chain = load_chain()
    last_block = chain[-1]
    
    # Create a new block from the provided transactions
    new_block = TXConfig.Block(
        index=len(chain),  # Index based on the current chain length
        timestamp=time.time(),
        transactions=[TXConfig.Transaction.from_dict(tx) for tx in transactions],
        previous_hash=last_block["hash"],
        hash=""
    )

    # Calculate the hash for the new block
    new_block.hash = calculate_hash(
        new_block.index,
        new_block.previous_hash,
        new_block.timestamp,
        [tx.to_dict() for tx in new_block.transactions]  # Convert transaction to dict for hashing
    )

    block_data = new_block.to_dict()  # Convert block to dict for consistency

    # Check consensus and broadcast the block if valid
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
            current["transactions"]
        )
        if current["hash"] != recalculated_hash:
            return False
        if current["previous_hash"] != previous["hash"]:
            return False
    return True
