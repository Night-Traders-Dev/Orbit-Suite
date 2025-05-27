@app.route("/orbit-stats")
def orbit_stats():
    from collections import defaultdict
    from datetime import datetime
    chain = load_chain()
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
        date = datetime.fromtimestamp(block["timestamp"]).strftime("%Y-%m-%d")
        block_tx_count = 0
        validators[block["validator"]]["blocks"] += 1
        for tx in block.get("transactions", []):
            tx_count += 1
            block_tx_count += 1
            validators[block["validator"]]["orbit_processed"] += tx["amount"]
            validators[block["validator"]]["txs_validated"] += 1
            accounts[tx["recipient"]] += tx["amount"]
            accounts[tx["sender"]] -= tx["amount"]
            tx_volume += tx["amount"]
            orbit_per_day[date] += tx["amount"]
            tx_per_day[date] += 1
        block_sizes.append(block_tx_count)

    total_orbit = sum([v for v in accounts.values() if v > 0])
    avg_block_size = sum(block_sizes) / len(block_sizes) if block_sizes else 0

    return render_template("orbit_stats.html", stats={
        "blocks": len(chain),
        "transactions": tx_count,
        "accounts": len([k for k, v in accounts.items() if v > 0]),
        "supply": round(total_orbit, 4),
        "volume": round(tx_volume, 4),
        "avg_block_size": round(avg_block_size, 2),
        "validators": dict(validators),
        "orbit_per_day": dict(orbit_per_day),
        "tx_per_day": dict(tx_per_day),
    })
