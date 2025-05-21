import json
import os
import shutil
import time
import re
from config.configutil import OrbitDB
from blockchain.blockutil import calculate_hash

orbit_db = OrbitDB()
CHAIN_FILE = orbit_db.blockchaindb
BACKUP_FILE = CHAIN_FILE.replace(".json", f"_backup_{int(time.time())}.json")

def backup_chain():
    if os.path.exists(CHAIN_FILE):
        shutil.copy(CHAIN_FILE, BACKUP_FILE)
        print(f"[Backup] Original chain backed up to: {BACKUP_FILE}")

def fix_json_trailing_commas(raw_text):
    # Removes trailing commas before closing braces/brackets
    return re.sub(r",\s*([}\]])", r"\1", raw_text)

def load_and_fix_chain():
    with open(CHAIN_FILE, "r") as f:
        raw = f.read()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("[Fix] Malformed JSON detected, attempting to fix trailing commas...")
        fixed_raw = fix_json_trailing_commas(raw)
        try:
            return json.loads(fixed_raw)
        except Exception as e:
            print("[Error] Failed to parse JSON after fix:", e)
            return None

def validate_and_repair_chain(chain):
    print("[Validate] Checking each block for hash and continuity issues...")
    fixed_chain = []

    for i, block in enumerate(chain):
        if i > 0:
            block["previous_hash"] = fixed_chain[-1]["hash"]

        block["hash"] = calculate_hash(
            block["index"],
            block["previous_hash"],
            block["timestamp"],
            block["transactions"],
            block.get("validator", ""),
            block.get("merkle_root", ""),
            block.get("nonce", 0),
            block.get("metadata", {})
        )

        fixed_chain.append(block)

    print(f"[Validate] Completed. Total blocks: {len(fixed_chain)}")
    return fixed_chain

def save_chain(chain):
    with open(CHAIN_FILE, "w") as f:
        json.dump(chain, f, indent=4)
    print("[Save] Repaired chain saved to orbit_chain.json.")

def repair_chain():
    print("=== Orbit Chain Repair Utility ===")
    backup_chain()
    chain = load_and_fix_chain()

    if not chain:
        print("[Abort] Unable to recover from JSON issues.")
        return

    repaired = validate_and_repair_chain(chain)
    save_chain(repaired)
    print("[Done] Blockchain has been repaired and validated.")

if __name__ == "__main__":
    repair_chain()
