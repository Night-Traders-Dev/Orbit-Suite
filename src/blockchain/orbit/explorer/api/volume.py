@app.route("/api/orbit_volume_14d")
def orbit_volume_14d():
    chain = load_chain()
    now = datetime.datetime.utcnow()
    volume_by_day = {}

    # Initialize the last 14 days with zero volume
    for i in range(14):
        day = (now - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        volume_by_day[day] = 0.0

    for block in chain:
        for tx in block.get("transactions", []):
            ts = tx.get("timestamp", block.get("timestamp", None))
            if ts:
                dt = datetime.datetime.utcfromtimestamp(ts)
                day_str = dt.strftime("%Y-%m-%d")
                if day_str in volume_by_day:
                    try:
                        volume_by_day[day_str] += float(tx.get("amount", 0.0))
                    except:
                        continue

    # Return sorted ascending
    result = [{"date": day, "volume": round(volume_by_day[day], 4)} for day in sorted(volume_by_day)]
    return jsonify(result)


@app.route("/api/tx_volume_14d")
def tx_volume_14d():
    from collections import defaultdict
    import time

    chain = load_chain()
    now = int(time.time())
    one_day = 86400

    tx_by_day = defaultdict(int)
    for block in chain:
        for tx in block.get("transactions", []):
            day = (tx.get("timestamp", block["timestamp"])) // one_day
            tx_by_day[day] += 1

    recent_days = [(now // one_day) - i for i in range(13, -1, -1)]
    data = []
    for day in recent_days:
        date_str = datetime.datetime.fromtimestamp(day * one_day).strftime("%b %d")
        data.append({
            "date": date_str,
            "count": tx_by_day.get(day, 0)
        })

    return jsonify(data)


@app.route("/api/block_volume_14d")
def block_volume_14d():
    chain = load_chain()
    now = datetime.datetime.utcnow()
    counts = {}

    # Initialize past 14 days
    for i in range(14):
        day = (now - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        counts[day] = 0

    for block in chain:
        ts = block.get("timestamp")
        if ts:
            dt = datetime.datetime.utcfromtimestamp(ts)
            day_str = dt.strftime("%Y-%m-%d")
            if day_str in counts:
                counts[day_str] += 1

    # Return sorted by date ascending
    result = [{"date": day, "count": counts[day]} for day in sorted(counts)]
    return jsonify(result)
