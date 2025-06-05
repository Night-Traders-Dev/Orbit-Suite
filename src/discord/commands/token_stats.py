from core.ioutil import fetch_chain

async def token_stats(address):
    chain = fetch_chain()
    tokens = {}
    token_stats = {}
    stat_list = []

    for block in reversed(chain):
        for tx in block.get("transactions", []):
            note = tx.get("note")
            orbit_amount = tx.get("amount")
            if not isinstance(note, dict):
                continue

            tx_type = note.get("type", {})

            if "token_transfer" in tx_type:
                data = tx_type["token_transfer"]
                token = data.get("token_symbol")
                qty = data.get("amount")
                sender = data.get("sender")
                receiver = data.get("receiver")
                is_exchange = data.get("note")
                if not token or not isinstance(qty, (int, float)):
                    continue

                stats = token_stats.setdefault(token, {"buy_tokens": 0, "buy_orbit": 0.0, "sell_tokens": 0, "sell_orbit": 0.0})

                if receiver == address:
                    tokens[token] = tokens.get(token, 0) + qty
                    if is_exchange == "Token purchased from exchange":
                        stats["buy_tokens"] += qty
                        stats["buy_orbit"] += qty * 0.1
                    elif orbit_amount:
                        stats["buy_tokens"] += qty
                        stats["buy_orbit"] += orbit_amount
                elif sender == address:
                    tokens[token] = tokens.get(token, 0) - qty
                    if orbit_amount:
                        stats["sell_tokens"] += qty
                        stats["sell_orbit"] += orbit_amount

            elif "buy_token" in tx_type:
                data = tx_type["buy_token"]
                token = data.get("symbol")
                qty = data.get("amount")
                if not token or data.get("seller") == address:
                    continue
                tokens[token] = tokens.get(token, 0) + qty
                stats = token_stats.setdefault(token, {"buy_tokens": 0, "buy_orbit": 0.0, "sell_tokens": 0, "sell_orbit": 0.0})
                stats["buy_tokens"] += qty
                stats["buy_orbit"] += qty * data.get("price", 0)

            elif "sell_token" in tx_type:
                data = tx_type["sell_token"]
                token = data.get("symbol")
                qty = data.get("amount")
                if not token or data.get("seller") != address:
                    continue
                tokens[token] = tokens.get(token, 0) - qty
                stats = token_stats.setdefault(token, {"buy_tokens": 0, "buy_orbit": 0.0, "sell_tokens": 0, "sell_orbit": 0.0})
                stats["sell_tokens"] += qty
                stats["sell_orbit"] += qty * data.get("price", 0)

    if not tokens:
        return False

    for token, balance in tokens.items():
        if abs(balance) < 1e-8:
            continue
        stats = token_stats.get(token, {})
        buy_tokens = stats.get("buy_tokens", 0)
        buy_orbit = stats.get("buy_orbit", 0)
        sell_tokens = stats.get("sell_tokens", 0)
        sell_orbit = stats.get("sell_orbit", 0)

        avg_buy_price = (buy_orbit / buy_tokens) if buy_tokens else None
        avg_sell_price = (sell_orbit / sell_tokens) if sell_tokens else None
        current_price = (avg_buy_price + avg_sell_price) / 2 if avg_buy_price and avg_sell_price else avg_buy_price or avg_sell_price or 0.0

        stat_list.append((
            token,
            balance,
            buy_tokens,
            buy_orbit,
            sell_tokens,
            sell_orbit,
            avg_buy_price,
            avg_sell_price,
            current_price
        ))

    return stat_list
