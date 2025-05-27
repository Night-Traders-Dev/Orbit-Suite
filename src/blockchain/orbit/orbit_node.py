import time, datetime
import requests
import threading
import json
import os
from flask import Flask, request, jsonify
from config.configutil import TXConfig, NodeConfig
from core.ioutil import load_nodes, save_nodes, fetch_chain, save_chain
from blockchain.blockutil import validate_block
from blockchain.orbitutil import get_node_for_user

FETCH_INTERVAL = 30
NODE_LEDGER = "data/orbit_chain.node"
EXPLORER = "http://127.0.0.1:7000/node_ping"

class OrbitNode:
    def __init__(self, address):
        self.address = address
        self.port = 0
        self.node_id = get_node_for_user(address)
        self.chain = []
        self.running = True
        self.nodes = load_nodes()
        self.register_node()

    def register_node(self):
        self.node_id = get_node_for_user(self.address)

        if not self.node_id:
            existing_ids = [int(n.replace("Node", "")) for n in self.nodes.keys() if n.startswith("Node") and n.replace("Node", "").isdigit()]
            next_id = max(existing_ids, default=0) + 1
            self.node_id = f"Node{next_id}"

        try:
            node_num = int(self.node_id.replace("Node", ""))
        except ValueError:
            node_num = 0
        self.port = 5000 + node_num

        if self.node_id not in self.nodes:
            self.nodes[self.node_id] = {
                "address": "127.0.0.1",
                "port": self.port,
                "quorum_slice": [n for n in list(self.nodes) if n != self.node_id][:2],
                "trust_score": 1.0,
                "uptime_score": 1.0,
                "user": self.address
            }
            save_nodes(self.nodes)
            print(f"Registered new node {self.node_id} for user {self.address}")
        else:
            print(f"Node {self.node_id} already registered for user {self.address}")


    def fetch_latest_chain(self):
        try:
            return fetch_chain()
        except Exception as e:
            print(f"Error fetching chain: {e}")
            return []

    def update_chain(self):
        new_chain = self.fetch_latest_chain()
        if new_chain and len(new_chain) > len(self.chain):
            print(f"New chain received. Updating local ledger ({len(new_chain)} blocks).")
            self.chain = new_chain
            save_chain(self.chain, owner_id=self.node_id, chain_file=NODE_LEDGER)

    def validate_incoming_block(self, block):
        if validate_block(block, self.chain):
            self.chain.append(block)
            save_chain(self.chain, owner_id=self.node_id, chain_file=NODE_LEDGER)
            print(f"Accepted new block: {block['index']}")
            return True
        else:
            print("Invalid block received.")
            return False

    def broadcast_block_to_peers(self, block):
        for node_id, node_data in self.nodes.items():
            if node_id == self.node_id:
                continue
            url = node_data.get("url")
            try:
                res = requests.post(f"{url}/receive_block", json=block, timeout=3)
                if res.status_code == 200:
                    print(f"Block sent to {node_id}")
            except Exception as e:
                print(f"Failed to send block to {node_id}: {e}")

    def start_receiver_server(self):
        app = Flask(__name__)

        @app.route("/receive_block", methods=["POST"])
        def receive_block():
            block = request.get_json()
            if self.validate_incoming_block(block):
                return jsonify({"status": "accepted"}), 200
            return jsonify({"status": "rejected"}), 400

        threading.Thread(
            target=app.run,
            kwargs={"port": 5000 + int(self.node_id[-1]), "debug": False, "use_reloader": False}
        ).start()


    def ping_explorer(self, node_id, EXPLORER, port):
        try:
            requests.post(EXPLORER, json={"node_id": self.node_id, "port": self.port})
        except Exception as e:
            print("Explorer ping failed:", e)


    def get_known_nodes(self, explorer_url="http://127.0.0.1:7000/active_nodes"):
        try:
            response = requests.get(explorer_url)
            return response.json()
        except Exception as e:
            print("Failed to get active nodes:", e)
            return {}

    def run(self):
        print(f"Starting Orbit Node for {self.address} ({self.node_id})")
        self.start_receiver_server()
        while self.running:
            self.ping_explorer(self.node_id, EXPLORER, self.port)
            self.get_known_nodes()
            self.update_chain()
            time.sleep(FETCH_INTERVAL)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start a standalone Orbit Blockchain Node")
    parser.add_argument("--address", required=True, help="User address to associate with this node")
    args = parser.parse_args()

    node = OrbitNode(args.address)
    try:
        node.run()
    except KeyboardInterrupt:
        print("Stopping node...")
        node.stop()
