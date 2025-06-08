# 🌌 Orbit Blockchain

**Orbit** is a lightweight, modular blockchain framework written in Python. It features a trust-based consensus model, dynamic mining, integrated exchange, and multi-platform interfacesâ€”all designed for experimentation, decentralization, and community-driven economics.

---

## 🚀 Key Components

| Component     | Description |
|---------------|-------------|
| **Blockchain** | Core blockchain engine using Enhanced Prime Cryptography (EPC) and Proof of Insight (PoI). Manages ledger, consensus, mining, and validation. |
| **Bridge** | Module for bridging assets and data between Orbit and external networks (future roadmap). |
| **Contracts** | Smart contract sandbox (under development) for lightweight on-chain logic execution. |
| **DiscordBot** | Full-featured Discord interface for wallet access, mining, trading, and staking using slash commands like `/wallet` and `/exchange`. |
| **ExchangeBot** | Decentralized exchange agent that matches buy/sell orders across active validator nodes. Accessible via Web and Discord. |
| **Explorer** | Flask-based web UI to explore blocks, transactions, addresses, validators, and token flows. Includes charts, smart search, and JSON API. |
| **Node** | Mesh network node system with trust/uptime-based block validation, message relay, and exchange matching. Each user session controls a live node. |
| **Orbim** | Smart Contract Language, inspired by Nim. Web3 First, General-purpose, Compiles to WASM |

---

## ⛏️ Mining System

Orbit uses **Proof-of-Time**, a simulated mining model where:

- Mining is time-based, not energy-intensive.
- Reward rates are dynamically adjusted via:
  - User growth (early adopters earn more)
  - Supply decay
  - Block-based halving
  - Node uptime/trust

📄 See [`MINING.md`](./MINING.md) for full formula and examples.

---

## 🔐 Token Lockups & Rewards

Users can lock ORBIT for passive rewards:

- ~5% APR, claimable after 24h intervals
- Rewards issued as `reward` transactions
- Lockups include `lock_start`, `lock_duration`, and `claim_until` metadata

---

## 🤝 Consensus: Proof of Insight (PoI)

A social-trust consensus model:

- Nodes propose and vote on blocks
- Votes weighted by **trust score** and **uptime**
- Enhanced by user-defined **Security Circles**

---

## 🌐 Interfaces

- **Web UI** (Explorer): Visualize the network, search addresses, view charts, and trade
- **Discord Bot**: Slash-command driven interface for wallets, mining, and trading
- **CLI (Orbin)**: Terminal-based wallet, node, and mining access

---

## 🛠️ Developer Friendly

- MIT Licensed
- JSON-based ledger
- Modular Python design
- Customizable consensus, mining, and trading logic

---

## 📚 Documentation

- [`ORBIT.md`](./ORBIT.md): Full technical whitepaper
- [`MINING.md`](./MINING.md): Dynamic mining algorithm details

---

## 🗺️ Roadmap Highlights

- OrbitDNS (decentralized naming)
- Smart contracts via sandbox
- On-chain governance with trust-weighted voting
- Interchain bridges (Orbit ⇄  Ethereum, etc.)

---

## 💫 Get Involved

Whether you're a researcher, builder, or community validator—Orbit is an open playground for decentralized innovation.
