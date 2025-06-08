from core.ioutil import fetch_chain

BASE_PRICE = 0.1
TOKEN = "FUEL"

async def get_stats(stats_dict, token):
    return stats_dict.setdefault(token, {
        "buy_tokens": 0,
        "buy_orbit": 0.0,
        "sell_tokens": 0,
        "sell_orbit": 0.0
    })

async def token_stats(token=TOKEN):
    chain = fetch_chain()
    tokens = {}
    filled_stats = {}
    meta_list = []
    open_stats = {}
    stat_list = []
    open_list = []
    open_order_ids = set()
    filled_order_ids = set()
    traded_tokens = set()
    exchange_only = {}
    tx_counts = []
    transfer_cnt = 0
    buy_cnt = 0
    sell_cnt = 0

    for block in reversed(chain):
        for tx in block.get("transactions", []):
            note = tx.get("note")
            orbit_amount = tx.get("amount")
            if not isinstance(note, dict):
                continue

            tx_type = note.get("type", {})

            # Token creation metadata
            if "create_token" in tx_type:
                data = tx_type["create_token"]
                meta_id = data.get("token_id")
                meta_name = data.get("name")
                meta_symbol = data.get("symbol")
                meta_supply = data.get("supply")
                meta_owner = data.get("creator")
                meta_created = data.get("created_at")

                if not meta_id:
                    continue

                meta_list.append({
                    "id": meta_id,
                    "name": meta_name,
                    "symbol": meta_symbol,
                    "supply": meta_supply,
                    "owner": meta_owner,
                    "created_at": meta_created
                })

            # Token transfer
            if "token_transfer" in tx_type:
                data = tx_type["token_transfer"]
                tok = data.get("token_symbol")
                qty = data.get("amount")
                sender = data.get("sender")
                receiver = data.get("receiver")
                tx_note = data.get("note")

                if not tok or not isinstance(qty, (int, float)):
                    continue

                stats = await get_stats(filled_stats, tok)

                tokens[tok] = tokens.get(tok, 0) + qty
                if tx_note == "Token purchased from exchange":
                    stats["buy_tokens"] += qty
                    stats["buy_orbit"] += qty * BASE_PRICE
                    transfer_cnt += 1
                    exchange_only[tok] = True

            # Buy order
            elif "buy_token" in tx_type:
                data = tx_type["buy_token"]
                order_id = data.get("order_id")
                tok = data.get("symbol")
                qty = data.get("amount")
                price = data.get("price", 0)

                if not order_id or not tok or not isinstance(qty, (int, float)):
                    continue

                if data.get("status") == "filled":
                    if order_id in filled_order_ids:
                        continue
                    filled_order_ids.add(order_id)

                    tokens[tok] = tokens.get(tok, 0) + qty
                    fill_stats = await get_stats(filled_stats, tok)
                    fill_stats["buy_tokens"] += qty
                    fill_stats["buy_orbit"] += qty * price
                    buy_cnt += 1
                    traded_tokens.add(tok)
                else:
                    if order_id in filled_order_ids:
                        continue
                    open_order_ids.add(order_id)

                    tokens[tok] = tokens.get(tok, 0) + qty
                    op_stats = await get_stats(open_stats, tok)
                    op_stats["buy_tokens"] += qty
                    op_stats["buy_orbit"] += qty * price
                    buy_cnt += 1
                    traded_tokens.add(tok)

            # Sell order
            elif "sell_token" in tx_type:
                data = tx_type["sell_token"]
                order_id = data.get("order_id")
                tok = data.get("symbol")
                qty = data.get("amount")
                price = data.get("price", 0)

                if not order_id or not tok or not isinstance(qty, (int, float)):
                    continue

                if data.get("status") == "filled":
                    if order_id in filled_order_ids:
                        continue
                    filled_order_ids.add(order_id)

                    fill_stats = await get_stats(filled_stats, tok)
                    fill_stats["sell_tokens"] += qty
                    fill_stats["sell_orbit"] += qty * price
                    sell_cnt += 1
                    traded_tokens.add(tok)
                else:
                    if order_id in filled_order_ids:
                        continue
                    open_order_ids.add(order_id)

                    tokens[tok] = tokens.get(tok, 0) - qty
                    op_stats = await get_stats(open_stats, tok)
                    op_stats["sell_tokens"] += qty
                    op_stats["sell_orbit"] += qty * price
                    sell_cnt += 1
                    traded_tokens.add(tok)

    if not tokens:
        return False

    for tok in sorted(tokens.keys()):
        raw_balance = tokens[tok]

        # Filled stats
        fill_stats = filled_stats.get(tok, {})
        fb = fill_stats.get("buy_tokens", 0)
        fs = fill_stats.get("sell_tokens", 0)
        fbo = fill_stats.get("buy_orbit", 0)
        fso = fill_stats.get("sell_orbit", 0)

        # Open stats
        op_stats = open_stats.get(tok, {})
        ob = op_stats.get("buy_tokens", 0)
        os = op_stats.get("sell_tokens", 0)
        obo = op_stats.get("buy_orbit", 0)
        oso = op_stats.get("sell_orbit", 0)

        # Adjusted balance
        adjusted_balance = raw_balance - fb + ob + os

        # Price calculations
        net_tokens = fb - fs
        net_orbit = fbo - fso
        avg_buy_price = (net_orbit / net_tokens) if net_tokens else 0.0
        avg_sell_price = (fso / fs) if fs else 0.0

        current_price = (
            (avg_buy_price + avg_sell_price) / 2
            if avg_buy_price and avg_sell_price
            else avg_buy_price or avg_sell_price or BASE_PRICE
        )

        stat_list.append({
            "token": tok,
            "adjusted_balance": round(adjusted_balance, 8),
            "buy_tokens": fb,
            "buy_orbit": fbo,
            "sell_tokens": fs,
            "sell_orbit": fso,
            "avg_buy_price": round(avg_buy_price, 4),
            "avg_sell_price": round(avg_sell_price, 4),
            "current_price": round(current_price, 4)
        })

        # Open order price stats
        open_net_tokens = ob - os
        open_net_orbit = obo - oso
        open_avg_buy_price = (open_net_orbit / open_net_tokens) if open_net_tokens else 0.0
        open_avg_sell_price = (oso / os) if os else 0.0

        open_price = (
            (open_avg_buy_price + open_avg_sell_price) / 2
            if open_avg_buy_price and open_avg_sell_price
            else open_avg_buy_price or open_avg_sell_price or BASE_PRICE
        )

        open_list.append({
            "token": tok,
            "adjusted_balance": round(adjusted_balance, 8),
            "buy_tokens": ob,
            "buy_orbit": obo,
            "sell_tokens": os,
            "sell_orbit": oso,
            "avg_buy_price": round(open_avg_buy_price, 4),
            "avg_sell_price": round(open_avg_sell_price, 4),
            "open_price": round(open_price, 4)
        })

        tx_counts.append({
            "token": tok,
            "exchange_cnt": transfer_cnt,
            "buy_cnt": buy_cnt,
            "sell_cnt": sell_cnt
        })
    return stat_list, open_list, meta_list, tx_counts
