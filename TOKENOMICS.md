# 📊 Orbit Tokenomics Overview

## 🔢 Total Supply
- **Total Token Supply:** `100,000,000,000 ORBIT`

## 💼 Wallet Allocations
| Wallet | Allocation (ORBIT) | % of Total Supply |
|--------|--------------------|-------------------|
| `system` | 81,900,000,000.0000 | 81.90% |
| `lockup_rewards` | 100,000,000.0000 | 0.10% |
| `mining` | 1,000,000,000.0000 | 1.00% |
| `nodefeecollector` | 0.0000 | 0.00% |
| `community` | 3,000,000,000.0000 | 3.00% |
| `team` | 5,000,000,000.0000 | 5.00% |
| `airdrop` | 1,000,000,000.0000 | 1.00% |
| `foundation` | 2,000,000,000.0000 | 2.00% |
| `partnerships` | 1,000,000,000.0000 | 1.00% |
| `reserve` | 5,000,000,000.0000 | 5.00% |

> 💡 **Note:** The `system` wallet holds the undeployed token pool, often used to fund network incentives and future allocations.

## 🛠️ Mining Pool
- **Designated Mining Supply:** `1,000,000,000 ORBIT`
- **Dynamic Rate Formula:**  
  Mining rate adjusts based on:
  - Total accounts (U)
  - Current mining wallet balance (S)
  - Total block height (B)
  - Node score (trust/performance)

- **Reward Formula:**
```
rate = R_base * (U_target / max(U, U_target))^0.5 * (S / S_max) * 0.5^(B / B_halflife) * (1 + min(Score, 0.10))
```
- `R_base = 0.082`
- `U_target = 10,000`
- `S_max = 1,000,000,000`
- `B_halflife = 100,000`
