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
                is_exchange = data.get("note")

                if not token_symbol or not isinstance(token_qty, (int, float)):
                    continue

                stats = token_stats.setdefault(token_symbol, {
                    "buy_tokens": 0, "buy_orbit": 0.0,
                    "sell_tokens": 0, "sell_orbit": 0.0
                })

                if receiver == address:
                    tokens[token_symbol] = tokens.get(token_symbol, 0.0) + token_qty

                    if is_exchange == "Token purchased from exchange":
                        stats["buy_tokens"] += token_qty
                        stats["buy_orbit"] += token_qty * 0.1
                    elif orbit_amount:
                        stats["buy_tokens"] += token_qty
                        stats["buy_orbit"] += orbit_amount

                elif sender == address:
                    tokens[token_symbol] = tokens.get(token_symbol, 0.0) - token_qty
                    if orbit_amount:
                        stats["sell_tokens"] += token_qty
                        stats["sell_orbit"] += orbit_amount

            # === BUY TOKEN ===
            elif "buy_token" in tx_type:
                data = tx_type["buy_token"]
                token_symbol = data.get("symbol")
                token_qty = data.get("amount")

                if not token_symbol or data.get("seller") == address:
                    continue

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

                if data.get("seller") != address:
                    continue

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
        buy_tokens = stats['buy_tokens']
        buy_orbit = stats['buy_orbit']
        sell_tokens = stats['sell_tokens']
        sell_orbit = stats['sell_orbit']

        avg_buy_price = (buy_orbit / buy_tokens) if buy_tokens else None
        avg_sell_price = (sell_orbit / sell_tokens) if sell_tokens else None

        if avg_buy_price and avg_sell_price:
            current_price = (avg_buy_price + avg_sell_price) / 2
        else:
            current_price = avg_buy_price or avg_sell_price or 0.0

        print(
            f" - {sym}:\n"
            f"    Bought {buy_tokens:.2f} for {buy_orbit:.4f} ORB (avg {avg_buy_price:.4f} ORB)\n"
            f"    Sold {sell_tokens:.2f} for {sell_orbit:.4f} ORB (avg {avg_sell_price:.4f} ORB)\n"
            f"    → Estimated Current Price: {current_price:.4f} ORB per token"
        )

my_tokens_button()
