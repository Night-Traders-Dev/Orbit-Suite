def node_profile(node_id, nodes, chain):
    node_data = nodes.get(node_id)
    if not node_data:
        return "node_not_found.html", [], 0, 0, 0, 0.0, 0.0

    # Filter blocks validated by this node
    blocks_validated = [b for b in chain if b.get("validator") == node_id]
    total_blocks = len(blocks_validated)
    trust = node_data.get("trust_score", 0)
    uptime = node_data.get("uptime_score", 0)

    total_orbit = 0
    total_tx_count = 0
    for block in blocks_validated:
        txs = block.get("transactions", [])
        total_tx_count += len(txs)
        for tx in txs:
            total_orbit += tx.get("amount", 0)

    avg_block_size = round(total_tx_count / total_blocks, 2) if total_blocks else 0

    return (
        "node_profile.html",
        blocks_validated,
        trust,
        uptime,
        total_blocks,
        round(total_orbit, 4),
        avg_block_size
    )
