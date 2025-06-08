# ⛏️ Orbit Dynamic Mining Rate Model

To ensure long-term sustainability and fairness, Orbit adjusts its mining rate based on user growth, remaining mining supply, time decay, and node performance.

---

# 📀 Formula Overview

The mining rate `R_current` is dynamically computed as:

```
R_current = R_base × UserFactor × SupplyFactor × TimeDecay × NodeBoost
```

Where:

* **R_base**: Initial base mining rate (e.g., 0.082 ORBIT/sec)
* **UserFactor**: Reduces reward as users grow
* **SupplyFactor**: Tapers rewards as remaining mining supply depletes
* **TimeDecay**: Gradual halving based on block height
* **NodeBoost**: Multiplier for high-trust, high-uptime nodes

---

# 🦢 Component Breakdown

1. 📉 User-Based Factor

Early adopters receive more:

```
UserFactor = (U_target / max(U, U_target))^0.5
```

* **U**: Active user count
* **U_target**: Target baseline (e.g., 10,000 users)

---

2. 💸 Supply-Based Tapering

Reduces mining as the dedicated mining pool depletes:

```
SupplyFactor = max(0, 1 - (S / S_max))
```

* **S**: Remaining mining supply
* **S_max**: Initial mining allocation (e.g., 1,000,000,000 ORBIT)

---

3. ⏳ Time Decay Factor

Block-based halving curve:

```
TimeDecay = 0.5 ^ (B / B_halflife)
```

* **B**: Current block height
* **B_halflife**: Blocks per mining halving (e.g., 100,000)

---

4. ✅ Node Score Boost

Nodes with high trust and uptime get a small boost:

```
NodeBoost = 1 + min(Score, 0.10)
```

* **Score**: Node trust and uptime score (range 0.00 to 1.00)
* **Boost capped at**: +10%

---

# 🔢 Final Mining Rate Formula

```python
def calculate_mining_rate(U, S, B, Score,
                          R_base=0.082,
                          U_target=10000,
                          S_max=1_000_000_000,
                          B_halflife=100000):
    user_factor = (U_target / max(U, U_target)) ** 0.5
    supply_factor = max(0, 1 - (S / S_max))
    time_decay = 0.5 ** (B / B_halflife)
    node_boost = 1 + min(Score, 0.10)

    return R_base * user_factor * supply_factor * time_decay * node_boost
```

---

# 📊 Example Values

| Users   | Remaining Supply | Blocks  | Score | Mining Rate (ORBIT/sec) |
| ------- | ---------------- | ------- | ----- | ----------------------- |
| 1,000   | 900M             | 10,000  | 0.90  | ~0.073                 |
| 10,000  | 500M             | 50,000  | 0.80  | ~0.031                 |
| 50,000  | 200M             | 100,000 | 0.60  | ~0.008                 |
| 100,000 | 0                | 200,000 | 1.00  | ~0.000                 |

---

# ⚖️ Design Benefits

| Feature           | Benefit                          |
| ----------------- | -------------------------------- |
| Early multiplier  | Rewards initial adoption         |
| Inflation control | Prevents runaway token creation  |
| Halving decay     | Adds Bitcoin-like predictability |
| Node-based boost  | Encourages reliable validation   |
