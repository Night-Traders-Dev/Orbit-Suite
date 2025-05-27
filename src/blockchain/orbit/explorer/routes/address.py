@app.route("/address/<address>")
def address_detail(address):
    balance, active_locks = load_balance(address)
    locks = get_user_lockups(address)
    last10 = last_transactions(address)
    pending = [l for l in locks if not l.get("matured")]
    matured = [l for l in locks if l.get("matured")]

    chain = load_chain()
    tx_count = 0
    total_sent = 0
    total_received = 0
    volume_by_day = defaultdict(lambda: {"in": 0, "out": 0})

    for block in chain:
        for tx in block.get("transactions", []):
            ts = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d")
            if tx["sender"] == address:
                total_sent += tx["amount"]
                volume_by_day[ts]["out"] += tx["amount"]
                tx_count += 1
            elif tx["recipient"] == address:
                total_received += tx["amount"]
                volume_by_day[ts]["in"] += tx["amount"]
                tx_count += 1

    avg_tx_size = round((total_sent + total_received) / tx_count, 4) if tx_count else 0
    balance = abs(total_received - total_sent)
    chart_data = []
    today = datetime.datetime.now(datetime.UTC)
    for i in range(14):
        day = today - datetime.timedelta(days=i)
        label = day.strftime("%Y-%m-%d")
        chart_data.append({
            "date": label,
            "in": round(volume_by_day[label]["in"], 4),
            "out": round(volume_by_day[label]["out"], 4)
        })
    chart_data.reverse()

    data = {
        "address": address,
        "balance": balance,
        "lockups": locks,
        "pending_lockups": pending,
        "matured_lockups": matured,
        "claimable": sum(l.get("reward", 0) for l in matured),
        "last10": last10,
        "total_sent": total_sent,
        "total_received": total_received,
        "avg_tx_size": avg_tx_size,
        "tx_count": tx_count,
        "chart_data": chart_data
    }

    if request.args.get("json") == "1":
        return jsonify(data)

    return render_template("address.html", address_data=data)
