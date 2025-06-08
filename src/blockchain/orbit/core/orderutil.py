from core.ioutil import fetch_chain

BASE_PRICE = 0.1

async def get_stats(stats_dict, token):
    return stats_dict.setdefault(token, {
        "buy_tokens": 0, "buy_orbit": 0.0,
        "sell_tokens": 0, "sell_orbit": 0.0
    })

async def token_stats():
    chain = fetch_chain()
    tokens = {}
    filled_stats = {}
    open_stats = {}
    stat_list = []
    open_list = []
    open_order_ids = set()
    filled_order_ids = set()
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

                stats = await get_stats(filled_stats, token)

                tokens[token] = tokens.get(token, 0) + qty
                if tx_note == "Token purchased from exchange":
                    stats["buy_tokens"] += qty
                    stats["buy_orbit"] += qty * BASE_PRICE
                    exchange_only[token] = True

            elif "buy_token" in tx_type:
                data = tx_type["buy_token"]
                order_id = data.get("order_id")

                if not order_id or order_id in filled_order_ids:
                    continue

                token = data.get("symbol")
                qty = data.get("amount")
                price = data.get("price", 0)
                if not token or not isinstance(qty, (int, float)):
                    continue

                if data.get("status") == "filled":
                    filled_order_ids.add(order_id)
                    tokens[token] = tokens.get(token, 0) + qty

                    fill_stats = await get_stats(filled_stats, token)
                    fill_stats["buy_tokens"] += qty
                    fill_stats["buy_orbit"] += qty * price
                    traded_tokens.add(token)
                else:
                    open_order_ids.add(order_id)
                    if not order_id or order_id in filled_order_ids:
                        continue
                    tokens[token] = tokens.get(token, 0) + qty
                    op_stats = await get_stats(open_stats, token)
                    op_stats["buy_tokens"] += qty
                    op_stats["buy_orbit"] += qty * price
                    traded_tokens.add(token)

            elif "sell_token" in tx_type:
                data = tx_type["sell_token"]
                order_id = data.get("order_id")

                token = data.get("symbol")
                qty = data.get("amount")
                price = data.get("price", 0)
                if not token or not isinstance(qty, (int, float)):
                    continue

                if data.get("status") == "filled":
                    filled_order_ids.add(order_id)

                    fill_stats = await get_stats(filled_stats, token)
                    fill_stats["sell_tokens"] += qty
                    fill_stats["sell_orbit"] += qty * price
                    traded_tokens.add(token)
                else:
                    open_order_ids.add(order_id)
                    if not order_id or order_id in filled_order_ids:
                        continue
                    tokens[token] = tokens.get(token, 0) - qty
                    op_stats = await get_stats(open_stats, token)
                    op_stats["sell_tokens"] += qty
                    op_stats["sell_orbit"] += qty * price
                    traded_tokens.add(token)

    if not tokens:
        return False

    for token in tokens:
        raw_balance = tokens[token]

        # Filled order stats
        fill_stats = filled_stats.get(token, {})
        filled_buy_tokens = fill_stats.get("buy_tokens", 0)
        filled_sell_tokens = fill_stats.get("sell_tokens", 0)
        filled_buy_orbit = fill_stats.get("buy_orbit", 0)
        filled_sell_orbit = fill_stats.get("sell_orbit", 0)

        # Open order stats
        op_stats = open_stats.get(token, {})
        open_buy_tokens = op_stats.get("buy_tokens", 0)
        open_sell_tokens = op_stats.get("sell_tokens", 0)
        open_buy_orbit = op_stats.get("buy_orbit", 0)
        open_sell_orbit = op_stats.get("sell_orbit", 0)

        # Adjusted balance
        adjusted_balance = raw_balance - filled_buy_tokens + open_buy_tokens + open_sell_tokens

        # Filled price stats
        net_tokens = filled_buy_tokens - filled_sell_tokens
        net_orbit = filled_buy_orbit - filled_sell_orbit
        avg_buy_price = (net_orbit / net_tokens) if net_tokens else 0.0
        avg_sell_price = (filled_sell_orbit / filled_sell_tokens) if filled_sell_tokens else 0.0

        current_price = (
            (avg_buy_price + avg_sell_price) / 2
            if avg_buy_price and avg_sell_price
            else avg_buy_price or avg_sell_price or BASE_PRICE
        )

        stat_list.append((
            token,
            round(adjusted_balance, 8),
            filled_buy_tokens,
            filled_buy_orbit,
            filled_sell_tokens,
            filled_sell_orbit,
            round(avg_buy_price, 4),
            round(avg_sell_price, 4),
            round(current_price, 4)
        ))

        # Open order price stats
        open_net_tokens = open_buy_tokens - open_sell_tokens
        open_net_orbit = open_buy_orbit - open_sell_orbit
        open_avg_buy_price = (open_net_orbit / open_net_tokens) if open_net_tokens else 0.0
        open_avg_sell_price = (open_sell_orbit / open_sell_tokens) if open_sell_tokens else 0.0

        open_price = (
            (open_avg_buy_price + open_avg_sell_price) / 2
            if open_avg_buy_price and open_avg_sell_price
            else open_avg_buy_price or open_avg_sell_price or BASE_PRICE
        )

        open_list.append((
            token,
            round(adjusted_balance, 8),
            open_buy_tokens,
            open_buy_orbit,
            open_sell_tokens,
            open_sell_orbit,
            round(open_avg_buy_price, 4),
            round(open_avg_sell_price, 4),
            round(open_price, 4)
        ))

    return stat_list, open_list
