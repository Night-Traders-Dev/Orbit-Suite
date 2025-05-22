# Orbit Blockchain Whitepaper

## Overview

**Orbit Blockchain** is a lightweight, modular, Python-based blockchain framework that enables secure, decentralized transaction processing and mining using **Enhanced Prime Cryptography (EPC)**. Designed for experimentation, education, and efficient distributed consensus, Orbit is capable of running on minimal infrastructure.


---

## Vision

Orbit aims to create a decentralized ecosystem where users can:

- Earn Orbit tokens through time-based mining,

- Lock tokens for passive rewards,

- Participate in network validation and governance via a trust-weighted consensus model,

- Interact through a local-first, CLI or web-based interface with full control over wallets and nodes.



---

# 2 Core Components

### 1. Ledger Architecture

Orbit maintains a persistent JSON ledger (data/orbit_chain.json) that stores all blocks and transactions. This local file is the canonical state on each node.

**Key Elements:**

- Genesis Block: Created automatically with no transactions and a static validator.

- Transactions: Include fields such as sender, recipient, amount, note, timestamp.

- Blocks: Contain metadata like index, timestamp, transactions, previous_hash, validator, merkle_root, nonce, and optional signatures and metadata.



---

### 2. Mining System

Orbit features Proof-of-Time Simulated Mining:

- Users simulate mining by choosing a time duration.

- Rewards are time-based (e.g., 0.082 Orbit/sec).

- Each mining session is recorded as a transaction and included in a new block.

-  Mining is lightweight and does not require high-performance hardware.



---

### 3. Lockups and Rewards

Orbit supports token Lockups to earn time-based rewards:

- Users may lock any amount of Orbit tokens for a chosen duration (in days).

- Locked tokens generate daily rewards (e.g., 5% APR).

- Rewards are only claimable after full reward intervals (daily).

- Lockups have a claim_until field to prevent duplicate reward claims.

- Once matured, tokens can be withdrawn from the lock.


#### Example Lockup Entry:
```json
{
  "amount": 100.0,
  "lock_start": 1747200000,
  "lock_duration": 2592000,
  "claim_until": 1747200000
}
```

Claimed rewards are recorded as reward transactions and added to the wallet balance.


---

### 4. Consensus Protocol – Proof of Insight (PoI)

Orbit introduces a trust-based consensus system:

- Block Proposal: A node proposes a block.

- Validation Quorum: Other nodes validate and vote based on block integrity and proposer trust score.

- Finalization: If quorum is met, signatures are added and the block is committed.


This system encourages long-term good behavior, uptime, and accurate validation.


---

### 5. Security Circle

Users can define a Security Circle of trusted peers:

- Helps bootstrap node trust.

- Will be integrated into PoI for weighing votes.

- Represents a web-of-trust layer for lightweight sybil resistance.



---

### Data Structures

#### Transaction
```json
{
  "type": "transfer",
  "sender": "alice",
  "recipient": "bob",
  "amount": 5,
  "note": "Service payment",
  "timestamp": 1747271826.12
}
```
#### Reward Transaction
```json
{
  "type": "reward",
  "sender": "orbit_rewards",
  "receiver": "alice",
  "amount": 0.082,
  "timestamp": 1747271826.12,
  "lock_ref": 1747200000
}
```
#### Block
```json
{
  "index": 1,
  "timestamp": 1747272826.8236349,
  "transactions": [...],
  "previous_hash": "...",
  "hash": "...",
  "validator": "Node3",
  "signatures": {
    "Node5": "sig...",
    "Node6": "sig..."
  },
  "merkle_root": "...",
  "nonce": 0,
  "metadata": {
    "version": "1.1",
    "lockup_rewards": [],
    "block_size": 1024
  }
}
```

---

## Node Network & Communication

- Nodes are listed in nodes.json.

- Communication uses socket-based broadcasting.

- Each node listens on a local TCP port.

- New blocks are broadcast to all known peers.

- Consensus responses are relayed with vote signatures.



---

## User Interface

### Terminal CLI

- Access wallet, ledger, mining, lockups, and node management.

- Fully local and file-based, with optional networking.


## Web UI (in progress)

- Integrated dashboard (wallet view, staking, mining, block explorer).

- Explorer features include block/tx search, validator stats, and rich address analytics.



---

## Unique Features

- Lightweight Genesis: Auto-generates genesis block if chain is missing.

- Daily Reward Claiming: Based on full-day lockup intervals.

- Matured Lockup Recognition: Withdrawals only allowed after full lock duration.

- Standalone Mode: Functions without internet, purely as a local ledger.

- Low-dependency: Pure Python, no blockchain libraries required.



---

## Future Roadmap

[x] Implement lockup reward mechanism

[x] Improve transaction validation logic

[x] Create Orbit Block Explorer (HTML modularized)

[x] Add validator stats and node profile pages

[ ] Implement gossip-based peer discovery

[ ] Add IPFS or anchor hashes for off-chain state anchoring

[ ] Introduce token governance (proposals + voting)

[ ] Enable smart contract scripting layer (EPC-based logic)

[ ] Mobile and lightweight embedded node versions



---

## License

### MIT License
Use freely, modify, and contribute to Orbit Blockchain’s continued evolution.


---

## Author: Orbit Blockchain Core – 2025


