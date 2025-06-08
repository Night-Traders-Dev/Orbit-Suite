from core.ioutil import fetch_chain

BASE_PRICE = 0.1
async def token_stats(address):
    chain = fetch_chain()
    tokens = {}
    token_stats = {}
    stat_list = []
    seen_order_ids = set()
    traded_tokens = set()
    exchange_only = {}

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
                tx_note = data.get("note")

                if not token or not isinstance(qty, (int, float)):
                    continue

                stats = token_stats.setdefault(token, {
                    "buy_tokens": 0, "buy_orbit": 0.0,
                    "sell_tokens": 0, "sell_orbit": 0.0
                })

                # Bought from exchange
                if receiver == address:
                    tokens[token] = tokens.get(token, 0) + qty
                    if tx_note == "Token purchased from exchange":
                        stats["buy_tokens"] += qty
                        stats["buy_orbit"] += qty * BASE_PRICE
                        exchange_only[token] = True

            elif "buy_token" in tx_type:
                data = tx_type["buy_token"]
                order_id = data.get("order_id")

                if not order_id or order_id in seen_order_ids:
                    continue
                if data.get("status") != "filled":
                    continue

                seen_order_ids.add(order_id)

                token = data.get("symbol")
                qty = data.get("amount")
                price = data.get("price", 0)
                if not token or data.get("seller") == address:
                    continue

                tokens[token] = tokens.get(token, 0) + qty
                stats = token_stats.setdefault(token, {
                    "buy_tokens": 0, "buy_orbit": 0.0,
                    "sell_tokens": 0, "sell_orbit": 0.0
                })

                stats["buy_tokens"] += qty
                stats["buy_orbit"] += qty * price
                traded_tokens.add(token)

            elif "sell_token" in tx_type:
                data = tx_type["sell_token"]
                order_id = data.get("order_id")

                if not order_id or order_id in seen_order_ids:
                    continue
                if data.get("status") != "filled":
                    continue

                seen_order_ids.add(order_id)

                token = data.get("symbol")
                qty = data.get("amount")
                price = data.get("price", 0)
                if not token or data.get("seller") != address:
                    continue

                tokens[token] = tokens.get(token, 0) - qty
                stats = token_stats.setdefault(token, {
                    "buy_tokens": 0, "buy_orbit": 0.0,
                    "sell_tokens": 0, "sell_orbit": 0.0
                })

                stats["sell_tokens"] += qty
                stats["sell_orbit"] += qty * price
                traded_tokens.add(token)

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

        avg_buy_price = ((buy_orbit - sell_orbit) / (buy_tokens - sell_tokens)) if buy_tokens else None
        avg_sell_price = (sell_orbit / sell_tokens) if sell_tokens else None

        if token in traded_tokens:
            current_price = (avg_buy_price + avg_sell_price) / 2 if avg_buy_price and avg_sell_price else avg_buy_price or avg_sell_price or BASE_PRICE
        else:
            current_price = BASE_PRICE

        stat_list.append((
            token,
            (balance - sell_tokens),
            (buy_tokens - sell_tokens),
            (buy_orbit - sell_orbit),
            sell_tokens,
            sell_orbit,
            round(avg_buy_price, 4) if avg_buy_price else None,
            round(avg_sell_price, 4) if avg_sell_price else None,
            round(current_price, 4)
        ))

    return stat_list

