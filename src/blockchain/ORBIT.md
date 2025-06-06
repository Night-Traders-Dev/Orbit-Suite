
# Orbit Blockchain Whitepaper

## Overview

Orbit Blockchain is a modular, Python-based blockchain framework designed for lightweight, decentralized applications. Powered by Enhanced Prime Cryptography (EPC) and featuring the novel Proof of Insight (PoI) consensus, Orbit is built for experimentation, education, and scalable community-driven validation.

It runs efficiently on local infrastructure with minimal dependencies and includes both a Discord-integrated UI and a full-featured Web UI.

---

## Vision

Orbit aims to build a decentralized ecosystem where users can:

- Earn Orbit tokens through time-based simulated mining  
- Lock tokens to passively earn daily rewards  
- Participate in validation via a trust-based consensus model  
- Interact through a Web UI or Discord bot for full wallet/node control  
- Explore real-time network metrics via the integrated Orbit Explorer  
- Trade tokens via a decentralized, node-powered exchange

---

## Core Components

### 1. Ledger Architecture

Orbit uses a local JSON ledger (`data/orbit_chain.json`) that stores all chain activity.

**Structure Includes:**

- **Genesis Block**: Auto-generated if the ledger is missing  
- **Transactions**: `transfer`, `mining`, `reward`, `lockup_claim`, and `exchange` types  
- **Blocks**: Include index, timestamp, transactions, hash, validator, Merkle root, signatures, and metadata  
- **Merkle Tree**: Root is computed per block for transaction integrity  

---

### 2. Mining System: Proof-of-Time

Orbit supports a simulated mining model:

- Users choose a mining duration  
- Reward rate: `0.082 ORBIT/sec` (simulated rate)  
- Mining transaction is added to a new block  
- No resource-intensive computation required  

---

### 3. Lockups and Claimable Rewards

Orbit features token lockups for passive earning:

- Tokens locked for *n* days receive daily rewards (~5% APR)  
- Rewards can be claimed after full 24h intervals  
- Claim tracking via `claim_until` field  
- Rewards are issued as special `reward` transactions  

#### Example Lockup Entry:

```json
{
  "amount": 100.0,
  "lock_start": 1747200000,
  "lock_duration": 2592000,
  "claim_until": 1747200000
}
```

---

### 4. Consensus: Proof of Insight (PoI)

Orbit replaces PoW/PoS with a trust-weighted consensus system:

- **Proposal**: Node proposes a block  
- **Voting**: Peers validate/sign based on proposer's trust and uptime  
- **Finalization**: Quorum reached â†’ block added  

**Trust is influenced by:**

- Session-based uptime tracking  
- Correct proposal history  
- Consensus participation  
- Security Circle relationships  

---

### 5. Security Circle

Optional peer trust layer:

- Users define trusted nodes  
- Boosts consensus weight during validation  
- Web-of-Trust style Sybil resistance  

---

### 6. Node Network

Orbit operates a lightweight mesh of validator nodes with:

- Dynamic session-based assignment (one node per active user)  
- Retry logic for failed block proposals  
- Trust/uptime tracking per session  
- Broadcast-based consensus messaging  
- Nodes listed publicly on the Orbit Explorer  
- Nodes can serve as validators **and** exchange agents  

---

### 7. Automated Exchange & Order Matching

Orbit includes a built-in, node-based decentralized exchange (DEX):

- Users can submit buy/sell orders via `/exchange` command  
- Orders are broadcast and matched automatically via node logic  
- Matching engine runs across active validator nodes  
- Orders matched based on price, timestamp, and quantity  
- Matching results are finalized in `exchange` transaction types  
- All trades are visible on the blockchain and in the Orbit Explorer  

---

### 8. Exchange Bot

The exchange is also accessible through a Discord-integrated bot:

- `/exchange` opens a trading panel  
- Users can view the order book, submit limit orders, or cancel orders  
- Node agents continuously monitor and match orders in real time  
- Order matching is trust-aware: orders are prioritized by honest node track record and uptime  

---

## Key Data Structures

### Transaction

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

### Reward Transaction

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

### Exchange Transaction

```json
{
  "type": "exchange",
  "sender": "alice",
  "order_type": "sell",
  "amount": 50,
  "price": 1.2,
  "matched_with": "bob",
  "timestamp": 1747279999.12
}
```

### Block

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

## User Interfaces

### Discord Bot Interface

Orbit integrates a full-featured Discord bot with these slash commands:

- `/register` â€“ Register your account  
- `/wallet` â€“ View balances, lockups, rewards  
- `/exchange` â€“ Access trading panel and submit orders  

The bot provides a social, real-time interface ideal for collaborative mining, staking, and trading.

---

### Web UI (Orbit Explorer)

- **Block Explorer**: Rich views of transactions, blocks, addresses, and validators  
- **Address Profiles**: Balance, lockups, tx history, inflow/outflow charts  
- **Validator Stats**: Uptime, trust, blocks proposed, processed volume  
- **Order Book View**: Live trading orders and matches  
- **Smart Search**: Navigate via tx hash, block ID, or address  
- **API Access**: JSON endpoints for block/tx/address/order lookup  
- **Live Charts**: Block production, wallet distribution, tx volume  
- **Security Circle View**: Web-of-trust node graph visualizations  

---

## Developer & Community Goals

- Open-source on GitHub (MIT License)  
- Encourages community validator nodes  
- Simple Python modules for rapid extension  
- Ideal for research, learning, and gamified economic experiments  

---

## Future Roadmap

- Smart contract support via simplified sandbox  
- On-chain governance system using trust scores  
- Decentralized naming service (OrbitDNS)  
- Real-time messaging layer using the node mesh  

---

## Conclusion

Orbit Blockchain offers a lightweight, modular platform for building a user-centric, trust-powered decentralized economy. Whether you're a developer, validator, or curious learner, Orbit provides the tools and transparency to explore the future of distributed systems.
