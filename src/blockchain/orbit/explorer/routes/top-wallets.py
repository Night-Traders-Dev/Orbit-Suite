@app.route("/top-wallets")
def top_wallets():
    chain = load_chain()
    balances = {}

    for block in chain:
        for tx in block.get("transactions", []):
            sender = tx.get("sender")
            recipient = tx.get("recipient")
            amount = tx.get("amount", 0)

            if sender != "genesis":
                balances[sender] = balances.get(sender, 0) - amount
            balances[recipient] = balances.get(recipient, 0) + amount

    top_10 = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:10]
    wallet_data = [{"address": addr, "balance": round(balance, 6)} for addr, balance in top_10]

    return render_template("top_wallets.html", wallets=wallet_data)
