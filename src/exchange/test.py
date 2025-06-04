from core.ioutil import fetch_chain

def my_tokens_button():
    address = "ORB.B77AC60F52529B834E4DAF21"

    chain = fetch_chain()
    tokens = {}
    token_stats = {}

    for block in reversed(chain):
        for tx in block.get("transactions", []):
            note = tx.get("note")
            orbit_amount = tx.get("amount")

            if not isinstance(note, dict):
                continue

            tx_type = note.get("type", {})

            # === TOKEN TRANSFER ===
            if "token_transfer" in tx_type:
                data = tx_type["token_transfer"]
                token_symbol = data.get("token_symbol")
                token_qty = data.get("amount")
                sender = data.get("sender")
                receiver = data.get("receiver")

                if not token_symbol or not isinstance(token_qty, (int, float)):
                    continue

                # Balance
                if receiver == address:
                    tokens[token_symbol] = tokens.get(token_symbol, 0.0) + token_qty
                    if orbit_amount:
                        stats = token_stats.setdefault(token_symbol, {
                            "buy_tokens": 0, "buy_orbit": 0.0,
                            "sell_tokens": 0, "sell_orbit": 0.0
                        })
                        stats["buy_tokens"] += token_qty
                        stats["buy_orbit"] += orbit_amount
                elif sender == address:
                    tokens[token_symbol] = tokens.get(token_symbol, 0.0) - token_qty
                    if orbit_amount:
                        stats = token_stats.setdefault(token_symbol, {
                            "buy_tokens": 0, "buy_orbit": 0.0,
                            "sell_tokens": 0, "sell_orbit": 0.0
                        })
                        stats["sell_tokens"] += token_qty
                        stats["sell_orbit"] += orbit_amount

            # === BUY TOKEN ===
            elif "buy_token" in tx_type:
                data = tx_type["buy_token"]
                token_symbol = data.get("symbol")
                token_qty = data.get("amount")
                buyer = address
                if data.get("seller") == address:
                    continue  # skip if you're the seller, not the buyer

                if token_symbol:
                    tokens[token_symbol] = tokens.get(token_symbol, 0.0) + token_qty
                    stats = token_stats.setdefault(token_symbol, {
                        "buy_tokens": 0, "buy_orbit": 0.0,
                        "sell_tokens": 0, "sell_orbit": 0.0
                    })
                    stats["buy_tokens"] += token_qty
                    stats["buy_orbit"] += token_qty * data.get("price", 0)

            # === SELL TOKEN ===
            elif "sell_token" in tx_type:
                data = tx_type["sell_token"]
                token_symbol = data.get("symbol")
                token_qty = data.get("amount")
                seller = data.get("seller")
                if seller != address:
                    continue  # skip if you're not the seller

                tokens[token_symbol] = tokens.get(token_symbol, 0.0) - token_qty
                stats = token_stats.setdefault(token_symbol, {
                    "buy_tokens": 0, "buy_orbit": 0.0,
                    "sell_tokens": 0, "sell_orbit": 0.0
                })
                stats["sell_tokens"] += token_qty
                stats["sell_orbit"] += token_qty * data.get("price", 0)

    print("Token Balances:")
    for sym, bal in tokens.items():
        if abs(bal) < 1e-8:
            continue
        print(f" - {sym}: {bal:.2f}")

    print("\nStats:")
    for sym, stats in token_stats.items():
        print(f" - {sym}: Bought {stats['buy_tokens']} for {stats['buy_orbit']} ORB | Sold {stats['sell_tokens']} for {stats['sell_orbit']} ORB")


my_tokens_button()
