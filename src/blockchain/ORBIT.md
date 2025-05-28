## Orbit Blockchain Whitepaper

# Overview

Orbit Blockchain is a modular, Python-based blockchain framework designed for lightweight, decentralized applications. Powered by Enhanced Prime Cryptography (EPC) and featuring the novel Proof of Insight (PoI) consensus, Orbit is built for experimentation, education, and scalable community-driven validation.

It runs efficiently on local infrastructure with minimal dependencies and includes both a CLI and a full-featured Web UI.


---

## Vision

Orbit aims to build a decentralized ecosystem where users can:

* Earn Orbit tokens through time-based simulated mining

* Lock tokens to passively earn daily rewards

* Participate in validation via a trust-based consensus model

* Interact through local CLI or web dashboards for full wallet/node control

* Explore real-time network metrics via the integrated Orbit Explorer



---

## Core Components

# 1. Ledger Architecture

Orbit uses a local JSON ledger (data/orbit_chain.json) that stores all chain activity.

Structure Includes:

* Genesis Block: Auto-generated if the ledger is missing

* Transactions: Transfer, mining, reward, and lockup claim types

* Blocks: Include index, timestamp, transactions, hash, validator, merkle_root, signatures, and metadata

* Merkle Tree: Root is computed per block for transaction integrity



---

# 2. Mining System: Proof-of-Time

Orbit supports a simulated mining model:

* Users choose a mining duration

* Reward rate: 0.082 ORBIT/sec (simulated rate)

* Mining transaction is added to a new block

* No resource-intensive computation required



---

# 3. Lockups and Claimable Rewards

Orbit features lockups for passive earning:

* Tokens locked for n days receive daily rewards (~5% APR)

* Rewards can be claimed daily, based on full intervals

* Prevents duplicate claims via claim_until field

* Rewards appear as special reward transactions


## Sample Lockup:
```json
{
  "amount": 100.0,
  "lock_start": 1747200000,
  "lock_duration": 2592000,
  "claim_until": 1747200000
}
```

---

# 4. Consensus: Proof of Insight (PoI)

Orbit replaces PoW/PoS with a trust-weighted consensus system:

* Proposal: Node proposes block

* Voting: Peers validate and sign based on proposer’s trust and uptime history

* Finalization: On quorum, signatures are aggregated and block is added


Trust is influenced by:

* Uptime (session duration and frequency)

* Correct block proposals

* Participation in consensus

* Security Circle inclusion



---

# 5. Security Circle

Optional peer trust layer:

* Users define trusted nodes

* Boosts consensus weight during validation

* Acts as a Web-of-Trust for identity anchoring and Sybil resistance



---

# Key Data Structures

## Transactions
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
## Reward Transaction
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
## Block
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
    "lockup_rewards": [...],
    "block_size": 1024
  }
}
```

---

## Node Network & Communication

* Nodes listed on explorer

* TCP socket-based broadcasting

* Node sessions assigned dynamically if not active

* Block proposals and votes are broadcast over the network

* Retry logic implemented for consensus failures



---

## User Interface

# CLI

Full wallet control: send, receive, mine, lock, claim

* Ledger viewing and transaction history

* Node/validator stats and trust management

* Security circle setup


## Web UI (Orbit Explorer)

* Block explorer: rich views for transactions, blocks, and addresses

* Node explorer: validator uptime, trust scores, block count, tx count

* Real-time analytics: block/day chart, top 10 wallets, inflow/outflow charts

* Responsive dashboard for wallet status, balances, and lockups



---

## Security & Wallet Management

* Encrypted private key storage (AES-based)

* Session-aware login/logout with active node assignment

* Backup and recovery system (JSON-based wallet export/import)

* Local-first design: users maintain full control over keys and data



---

## Unique Features

* Auto-generated genesis block

* Merkle root validation per block

* Daily lockup rewards with maturity tracking

* Claim-only-after-full-interval enforcement

* Local node session logic

* Web-based visualizations (Chart.js) for inflow/outflow

* Lightweight, portable, and low dependency footprint

* Network node reputation and voting-based trust



---

## Future Roadmap

* [x] Lockup reward mechanism

* [x] Claim logic with interval tracking

* [x] Merkle root generator

* [x] Encrypted private key storage

* [x] Dynamic node session assignment

* [x] Node trust/uptime persistence

* [x] Modular Orbit Explorer

* [x] Block/tx validator stats and analytics

* [ ] Gossip-based peer discovery

* [ ] Token governance (proposals + voting)

* [ ] Off-chain data anchoring (IPFS or anchor hashes)

* [ ] Smart contract scripting layer (EPC-based)

* [ ] Embedded/minimal node versions



---

## License

MIT License
Open-source, modifiable, and community-driven.


---

### Author: Orbit Blockchain Core, 2025


