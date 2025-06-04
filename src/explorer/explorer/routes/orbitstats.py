def orbit_stats(chain):
    from collections import defaultdict
    from datetime import datetime

    accounts = defaultdict(float)
    tx_count = 0
    tx_volume = 0.0
    block_sizes = []
    validators = defaultdict(lambda: {
        "blocks": 0,
        "orbit_processed": 0.0,
        "txs_validated": 0,
    })
    orbit_per_day = defaultdict(float)
    tx_per_day = defaultdict(int)

    for block in chain:
        timestamp = block.get("timestamp", 0)
        validator = block.get("validator", "unknown")
        date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        block_tx_count = 0

        validators[validator]["blocks"] += 1

        for tx in block.get("transactions", []):
            amount = float(tx.get("amount", 0))
            sender = tx.get("sender", "")
            recipient = tx.get("recipient", "")

            tx_count += 1
            block_tx_count += 1
            validators[validator]["orbit_processed"] += amount
            validators[validator]["txs_validated"] += 1
            accounts[recipient] += amount
            accounts[sender] -= amount
            tx_volume += amount
            orbit_per_day[date] += amount
            tx_per_day[date] += 1

        block_sizes.append(block_tx_count)

    total_orbit = sum(v for v in accounts.values() if v > 0)
    avg_block_size = sum(block_sizes) / len(block_sizes) if block_sizes else 0
    stats = {
        "blocks": len(chain),
        "transactions": tx_count,
        "accounts": len([k for k, v in accounts.items() if v > 0]),
        "supply": round(total_orbit, 4),
        "volume": round(tx_volume, 4),
        "avg_block_size": round(avg_block_size, 2),
        "validators": dict(validators),
        "orbit_per_day": dict(orbit_per_day),
        "tx_per_day": dict(tx_per_day),
    }

    return "orbit_stats.html", stats
