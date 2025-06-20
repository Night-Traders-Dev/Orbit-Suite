import time, datetime
import requests
import threading
import json
import os
import random
import argparse
import shutil
import asyncio
from flask import Flask, request, jsonify
from api import send_orbit_api
from configure import EXCHANGE_ADDRESS
from config.configutil import TXConfig, NodeConfig, OrbitDB
from core.ioutil import load_nodes, save_nodes, fetch_chain, save_chain
from blockchain.blockutil import validate_block
from blockchain.orbitutil import simulate_peer_vote
from core.logutil import log_node_activity
from utils.match_orders import match_orders

FETCH_INTERVAL = 30

EXPLORER = os.getenv("ORBIT_EXPLORER", "https://oliver-butler-oasis-builder.trycloudflare.com")

class OrbitNode:
    def __init__(self, address, port=None, tunnel_url=None):
        self.address = address
        self.tunnel_url = tunnel_url or os.getenv("TUNNEL_URL", "").strip()
        self.ip = '127.0.0.1'
        self.port = port or self.get_available_port()
        self.node_id = f"Node{random.randint(0, 9999)}"
        self.running = True
        self.node_ledger = f"node_data/orbit_chain.{self.node_id}"
        self.chain = fetch_chain()
        self.nodes = load_nodes()
        self.users = [address]
        self.heartbeat_min = 10
        self.heartbeat_max = 30
        self.block_timestamps = []
        self.heartbeat_task = None
        self.last_validated_block = self.get_latest_validated_block_index()
        self.block_received_event = threading.Event()
        self.stats_ui_thread = None
        self.peer_discovery_thread = None
        self.quorum_slice = set()

    def get_available_port(self, start=5000, end=5999):
        while True:
            port = random.randint(start, end)
            if not self.is_port_in_use(port):
                return port

    def is_port_in_use(self, port):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def register_node(self):
        raw_nodes = load_nodes()
        self.nodes = {n.get("id"): n for n in raw_nodes if isinstance(n, dict) and "id" in n}
        self.nodes[self.node_id] = {
            "id": self.node_id,
            "address": self.address,
            "host": self.tunnel_url if self.tunnel_url else self.ip,
            "port": self.port,
            "uptime": 1.0,
            "trust": 1.0,
            "last_seen": time.time(),
            "users": self.users
        }
        save_nodes(self.nodes, exclude_id=self.node_id)
        return self.nodes[self.node_id]

    def fetch_latest_chain(self):
        def is_valid_blockchain(chain):
            if not isinstance(chain, list) or not chain:
                return False
            required_fields = ["index", "hash", "timestamp", "transactions"]
            for block in chain:
                if not isinstance(block, dict):
                    return False
                if not all(field in block for field in required_fields):
                    return False
            return True

        try:
            chain = fetch_chain()
            if is_valid_blockchain(chain):
                return chain
            else:
                raise ValueError("Local chain malformed or corrupted.")
        except Exception as e:
            log_node_activity(self.node_id, "[RECOVERY]", f"Local chain failed integrity check: {e}")
            try:
                res = requests.get(f"{EXPLORER}/api/chain", timeout=5)
                if res.status_code == 200:
                    remote_chain = res.json()
                    if is_valid_blockchain(remote_chain):
                        save_chain(remote_chain, owner_id=self.node_id, chain_file=self.node_ledger)
                        log_node_activity(self.node_id, "[RECOVERY]", f"Fetched fresh chain from explorer.")
                        return remote_chain
            except Exception as ex:
                log_node_activity(self.node_id, "[ERROR]", f"Failed to recover chain from explorer: {ex}")
        return []

    def update_chain(self):
        new_chain = self.fetch_latest_chain()
        if new_chain and len(new_chain) > len(self.chain):
            self.chain = new_chain
            save_chain(self.chain, owner_id=self.node_id, chain_file=self.node_ledger)

    def validate_incoming_block(self, block):
        if any(b.get("hash") == block.get("hash") for b in self.chain):
            log_node_activity(self.node_id, "[INFO]", "Block already exists in chain.")
            return False
        log_node_activity(self.node_id, "[INFO]", "Validating Block.")
        if validate_block(block, self.node_id):
            self.chain.append(block)
            save_chain(self.chain, owner_id=self.node_id, chain_file=self.node_ledger)
            self.block_timestamps.append(time.time())
            self.nodes[self.node_id]["trust"] = min(1.0, self.nodes[self.node_id]["trust"] + 0.01)
            self.nodes[self.node_id]["uptime"] = min(1.0, self.nodes[self.node_id]["uptime"] + 0.01)
            save_nodes(self.nodes, exclude_id=self.node_id)
            self.last_validated_block = block.get("index", self.last_validated_block)
            self.broadcast_block_to_peers(block)
            self.block_received_event.set()
            log_node_activity(self.node_id, f"[SUCCESS]", f"Block validated and added at index {block.get('index')}")
            return True
        else:
            self.nodes[self.node_id]["trust"] = max(0.0, self.nodes[self.node_id]["trust"] - 0.02)
            save_nodes(self.nodes, exclude_id=self.node_id)
            log_node_activity(self.node_id, "[FAIL]", "Block failed validation.")
            return False

    def get_latest_validated_block_index(self):
        for block in reversed(self.chain):
            if block.get("validator") == self.node_id:
                return block["index"]
        return -1

    def get_validated_block_count(self):
        return sum(1 for block in self.chain if block.get("validator") == self.node_id)

    def broadcast_block_to_peers(self, block):
        log_node_activity(self.node_id, f"[SYNC]", f"Starting Broadcast")
        for node_id, node_data in self.nodes.items():
            if node_id == self.node_id:
                continue
            host = node_data.get("host")
            port = node_data.get("port")
            if host.startswith("http"):
                url = f"{host}/receive_block"
            else:
                url = f"http://{host}:{port}/receive_block"
            try:
                res = requests.post(url, json=block, timeout=3)
                if res.status_code == 200:
                    log_node_activity(self.node_id, f"[SYNC]", f"Block sent to {node_id}")
            except Exception:
                log_node_activity(self.node_id, f"[SYNC]", f"Block failed to send to {node_id}")
                continue

    def start_receiver_server(self):
        app = Flask(__name__)

        @app.route("/receive_block", methods=["POST"])
        def receive_block():
            block = request.get_json()
            if self.validate_incoming_block(block):
                self.update_chain()
                return jsonify({"status": "accepted"}), 200
            return jsonify({"status": "rejected"}), 400

        threading.Thread(
            target=app.run,
            kwargs={"host": '0.0.0.0', "port": self.port, "debug": False, "use_reloader": False}
        ).start()

    async def heartbeat_loop(self, new_node, new_node_id):
        while self.running:
            try:
                self.update_chain()
                new_node["last_seen"] = time.time()
                latest_block_index = self.get_latest_validated_block_index()
                validated_new_block = latest_block_index > self.last_validated_block
                current_uptime = new_node.get("uptime", 0.0)

                if validated_new_block:
                    new_uptime = min(1.0, current_uptime * 0.95 + 0.05)
                    self.last_validated_block = latest_block_index
                else:
                    new_uptime = max(0.0, current_uptime * 0.995)

                new_node["uptime"] = round(new_uptime, 4)

                await match_orders(self.node_id)

                response = requests.post(
                    f"{EXPLORER}/node_ping",
                    json=new_node,
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                if response.status_code == 200:
                    self.nodes[new_node_id] = new_node
                    save_nodes(self.nodes, exclude_id=self.node_id)

            except Exception as e:
                log_node_activity(self.node_id, "[HEARTBEAT]", f"Exception: {e}")

            if self.block_received_event.is_set():
                self.block_received_event.clear()

            await asyncio.sleep(self.get_dynamic_heartbeat_interval())

    def start_heartbeat_task(self, new_node, new_node_id):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        self.heartbeat_task = loop.create_task(self.heartbeat_loop(new_node, new_node_id))

    def get_dynamic_heartbeat_interval(self):
        cutoff = time.time() - 300
        self.block_timestamps = [t for t in self.block_timestamps if t >= cutoff]
        block_count = len(self.block_timestamps)
        max_blocks = 30
        ratio = min(block_count / max_blocks, 1.0)
        interval = self.heartbeat_max - (self.heartbeat_max - self.heartbeat_min) * ratio
        return max(self.heartbeat_min, min(self.heartbeat_max, int(interval)))

    def discover_and_add_peers(self):
        while self.running:
            try:
                res = requests.get(f"{EXPLORER}/active_nodes", timeout=5)
                if res.status_code == 200:
                    node_dict = res.json()
                    for node_id, node_data in node_dict.items():
                        peer = node_data.get("node", {})
                        if (
                            peer.get("id") != self.node_id
                            and peer.get("id") not in self.nodes
                        ):
                            self.nodes[peer["id"]] = {
                                "host": peer["host"],
                                "port": peer["port"],
                            }
                            log_node_activity(self.node_id, "[DISCOVERY]", f"Added new peer: {peer['id']}")
            except Exception as e:
                log_node_activity(self.node_id, "[DISCOVERY ERROR]", f"{e}")
            time.sleep(10)

    def start_peer_discovery_thread(self):
        self.peer_discovery_thread = threading.Thread(
            target=self.discover_and_add_peers,
            daemon=True
        )
        self.peer_discovery_thread.start()

    def display_stats_loop(self):
        while self.running:
            shutil.get_terminal_size()
            os.system("cls" if os.name == "nt" else "clear")
            validated_count = self.get_validated_block_count()
            uptime = self.nodes.get(self.node_id, {}).get("uptime", 0.0)
            trust = self.nodes.get(self.node_id, {}).get("trust", 0.0)
            print(f"\U0001F517 Orbit Node Dashboard")
            print(f"{'=' * 40}")
            print(f"Node ID       : {self.node_id}")
            print(f"Address       : {self.address}")
            print(f"Port          : {self.port}")
            print(f"Validated     : {validated_count} blocks")
            print(f"Trust         : {trust:.4f}")
            print(f"Uptime        : {uptime:.4f}")
            time.sleep(5)

    def start_stats_ui(self):
        self.stats_ui_thread = threading.Thread(
            target=self.display_stats_loop,
            daemon=True
        )
        self.stats_ui_thread.start()


def main():
    parser = argparse.ArgumentParser(description="Start an Orbit Node")
    parser.add_argument("address", help="Wallet address to assign to this node")
    parser.add_argument("--port", type=int, help="Port to run node on (optional)")
    parser.add_argument("--tunnel", type=str, help="Public tunnel URL (optional)")
    args = parser.parse_args()

    node = OrbitNode(address=args.address, port=args.port, tunnel_url=args.tunnel)
    new_node_info = node.register_node()
    node.start_receiver_server()
    node.start_peer_discovery_thread()
    node.start_heartbeat_task(new_node_info, node.node_id)
    node.start_stats_ui()

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Node is shutting down...")
        node.running = False

if __name__ == "__main__":
    main()
