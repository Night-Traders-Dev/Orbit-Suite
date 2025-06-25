import requests
from collections import defaultdict
from core.ioutil import fetch_chain
import datetime

BASE_PRICE = 0.1
TOKEN = "FUEL"
meta_list = []

async def all_tokens_stats(symbol_filter=None):
    from datetime import datetime, timedelta, UTC
    from collections import defaultdict
    now = datetime.now(UTC)
    chain = fetch_chain()
    tokens = {}
    total_transfers = 0
    transfers_24h = 0
    new_tokens_24h = 0
    wallets = {}

    if symbol_filter:
        if isinstance(symbol_filter, str):
            symbol_filter = {symbol_filter.upper()}
        else:
            symbol_filter = {s.upper() for s in symbol_filter}

    def parse_ts(ts_raw):
        if isinstance(ts_raw, str):
            return datetime.fromisoformat(ts_raw).replace(tzinfo=UTC)
        elif isinstance(ts_raw, (int, float)):
            return datetime.fromtimestamp(ts_raw, tz=UTC)
        return None

    for block in chain:
        for tx in block.get("transactions", []):
            note = tx.get("note")
            if not isinstance(note, dict):
                continue
            tx_type = note.get("type", {})
            ts = parse_ts(tx.get("timestamp"))

            # Token creation
            if "create_token" in tx_type:
                d = tx_type["create_token"]
                symbol = d.get("symbol")
                if symbol_filter and symbol.upper() not in symbol_filter:
                    continue

                name = d.get("name")
                supply = float(d.get("supply", 0))
                creator = d.get("creator")
                timestamp = d.get("timestamp")

                if name and symbol:
                    tokens[symbol] = {
                        "symbol": symbol,
                        "name": name,
                        "supply": supply,
                        "creator": creator,
                        "created_at": timestamp,
                        "age": "",
                        "transfers": 0,
                        "holders": set()
                    }
                    ts_created = parse_ts(timestamp)
                    if ts_created and (now - ts_created <= timedelta(days=1)):
                        new_tokens_24h += 1

            # Transfer types: update holders and transfers
            for typ in ["buy_token", "sell_token", "token_transfer"]:
                if typ in tx_type:
                    d = tx_type[typ]
                    symbol = d.get("symbol") or d.get("token_symbol")
                    if symbol_filter and symbol.upper() not in symbol_filter:
                        continue

                    sender = d.get("sender")
                    receiver = d.get("receiver")
                    if receiver == "ORB.BURN" or receiver == "ORB.00000000000000000000BURN":
                        tokens[symbol]["supply"] -= d.get("amount", 0)
                        continue
                    amount = d.get("amount")

                    if symbol in tokens:
                        tokens[symbol]["transfers"] += 1
                        if sender:
                            tokens[symbol]["holders"].add(sender)
                        if receiver:
                            tokens[symbol]["holders"].add(receiver)

                    if sender:
                        wallets.setdefault(sender, {"amount": 0})
                        wallets[sender]["amount"] -= amount
                    if receiver:
                        wallets.setdefault(receiver, {"amount": 0})
                        wallets[receiver]["amount"] += amount

                    total_transfers += 1
                    if ts and (now - ts <= timedelta(days=1)):
                        transfers_24h += 1

    # Final formatting
    token_list = []
    for token in tokens.values():
        created_at = parse_ts(token["created_at"])
        if created_at:
            age = now - created_at
            days = age.days
            token["age"] = f"{days} day{'s' if days != 1 else ''}"
        else:
            token["age"] = "Unknown"
        token["holders"] = len(token["holders"])
        token_list.append(token)

    token_list = sorted(token_list, key=lambda x: x["symbol"].lower())

    metrics = {
        "total_transfers": total_transfers,
        "transfers_24h": transfers_24h,
        "total_tokens": len(tokens),
        "new_tokens_24h": new_tokens_24h
    }
    return token_list, wallets, metrics

async def get_stats(stats_dict, token):
    return stats_dict.setdefault(token, {
        "buy_tokens": 0,
        "buy_orbit": 0.0,
        "sell_tokens": 0,
        "sell_orbit": 0.0
    })

async def upsert_token_meta(
    meta_list: list,
    meta_id: str,
    meta_name: str,
    meta_symbol: str,
    meta_supply: float,
    meta_owner: str,
    meta_created: datetime
):
    # look for an existing entry
    for entry in meta_list:
        if entry["id"] == meta_id:
            # found → update only the supply
            entry["supply"] = meta_supply
            return

    # not found → append new
    meta_list.append({
        "id":         meta_id,
        "name":       meta_name,
        "symbol":     meta_symbol,
        "supply":     meta_supply,
        "owner":      meta_owner,
        "created_at": meta_created
    })


async def token_stats(token=TOKEN):
    chain = fetch_chain()
    tokens = {}
    filled_stats = {}
    global meta_list
    if not meta_list:
        # Initialize meta_list if it's empty
        meta_list = []
    open_stats = {}
    stat_list = []
    open_list = []
    open_orders = []
    open_order_ids = set()
    filled_order_ids = set()
    traded_tokens = set()
    exchange_only = {}
    tx_counts = []
    transfer_cnt = 0
    buy_cnt = 0
    sell_cnt = 0
    history_data = defaultdict(list)

    for block in reversed(chain):
        for tx in block.get("transactions", []):
            note = tx.get("note")
            orbit_amount = tx.get("amount")
            if not isinstance(note, dict):
                continue

            tx_type = note.get("type", {})
            created_at = tx.get("timestamp") or block.get("timestamp")

            # Token creation metadata
            if "create_token" in tx_type:
                data = tx_type["create_token"]
                meta_id = data.get("token_id")
                meta_name = data.get("name")
                meta_symbol = data.get("symbol")
                meta_supply = data.get("supply")
                meta_owner = data.get("creator")
                meta_created = created_at

                if not meta_id:
                    continue

                # Avoid duplicate entries for the same token
                if not any(entry["id"] == meta_id for entry in meta_list):
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
                meta_id = meta_list[0]["id"] if meta_list else None
                meta_name = meta_list[0]["name"] if meta_list else None
                meta_symbol = meta_list[0]["symbol"] if meta_list else None
                meta_supply = meta_list[0]["supply"] if meta_list else 0.0
                meta_owner = meta_list[0]["owner"] if meta_list else None
                meta_created = meta_list[0]["created_at"] if meta_list else None
                if receiver == "ORB.BURN" or receiver == "ORB.00000000000000000000BURN":
                    try:
                        print(meta_list)
                        supply = meta_supply - qty
                        print(f"Updating supply for token {tok}: {qty} (burned) → {supply}")
                        meta_list.append({
                            "id": meta_id,
                            "name": meta_name,
                            "symbol": meta_symbol,
                            "supply": meta_supply,
                            "owner": meta_owner,
                            "created_at": meta_created
                        })
                    except Exception as e:
                        print(f"Error updating supply for token {tok}: {e}")
                        continue
                tx_note = data.get("note")

                if not tok or not isinstance(qty, (int, float)):
                    continue

                stats = await get_stats(filled_stats, tok)

                tokens[tok] = tokens.get(tok, 0) + qty
                if tx_note == "Token purchased from exchange":
                    stats["buy_tokens"] += qty
                    stats["buy_orbit"] += max(orbit_amount, 0.000001)
                    transfer_cnt += 1
                    exchange_only[tok] = True
                elif tx_note == "Token sold to exchange":
                    stats["sell_tokens"] += qty
                    stats["sell_orbit"] += max(orbit_amount, 0.000001)
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
                    fill_stats["buy_orbit"] += qty * max(price, 0.000001)
                    buy_cnt += 1
                    traded_tokens.add(tok)

                    if created_at and qty > 0:
                        history_data[tok].append({
                            "time": created_at,
                            "price": round(price, 6)
                        })
                else:
                    if order_id in filled_order_ids:
                        continue
                    open_order_ids.add(order_id)

                    tokens[tok] = tokens.get(tok, 0) + qty
                    op_stats = await get_stats(open_stats, tok)
                    op_stats["buy_tokens"] += qty
                    op_stats["buy_orbit"] += qty * max(price, 0.000001)
                    open_orders.append({"token": tok, "type": "buy", "price": price, "amount": qty})
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
                    fill_stats["sell_orbit"] += qty * max(price, 0.000001)
                    sell_cnt += 1
                    traded_tokens.add(tok)

                    if created_at and qty > 0:
                        history_data[tok].append({
                            "time": created_at,
                            "price": round(price, 6)
                        })
                else:
                    if order_id in filled_order_ids:
                        continue
                    open_order_ids.add(order_id)

                    tokens[tok] = tokens.get(tok, 0) - qty
                    op_stats = await get_stats(open_stats, tok)
                    op_stats["sell_tokens"] += qty
                    op_stats["sell_orbit"] += qty * max(price, 0.000001)
                    open_orders.append({"token": tok, "type": "sell", "price": price, "amount": qty})
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
  #      net_tokens = fb - fs
 #       net_orbit = fbo - fso
#        avg_buy_price = (net_orbit / net_tokens) if net_tokens else 0.000001
#        avg_sell_price = (fso / fs) if fs else 0.000001
        # Price calculations (fixed per‐side)
        avg_buy_price_raw  = (fbo / fb) if fb else BASE_PRICE
        avg_sell_price_raw = (fso / fs) if fs else BASE_PRICE

        # clamp to avoid zero/negative
        avg_buy_price  = max(avg_buy_price_raw,  0.000001)
        avg_sell_price = max(avg_sell_price_raw, 0.000001)

        if avg_buy_price < 0:
            print(f"⚠️ Negative avg_buy_price for {tok}: {avg_buy_price} (fbo={fbo}, fb={fb}, fso={fso}, fs={fs})")
        if avg_sell_price < 0:
            print(f"⚠️ Negative avg_sell_price for {tok}: {avg_sell_price} (fso={fso}, fs={fs})")
            avg_buy_price = (avg_buy_price - avg_buy_price) + avg_buy_price
        avg_buy_price  = max(avg_buy_price,  0.000001)
        avg_sell_price = max(avg_sell_price, 0.000001)


        raw_price = (
            (avg_buy_price + avg_sell_price) / 2
            if avg_buy_price and avg_sell_price
            else avg_buy_price or avg_sell_price or BASE_PRICE
        )
        current_price = max(raw_price, 0.000001)
        stat_list.append({
            "token": tok,
            "adjusted_balance": round(adjusted_balance, 6),
            "buy_tokens": fb,
            "buy_orbit": fbo,
            "sell_tokens": fs,
            "sell_orbit": fso,
            "avg_buy_price": round(avg_buy_price, 6),
            "avg_sell_price": round(avg_sell_price, 6),
            "current_price": round(current_price, 6)
        })

        # Open order price stats
        open_net_tokens = ob - os
        open_net_orbit = obo - oso
        open_avg_buy_price = (open_net_orbit / open_net_tokens) if open_net_tokens else 0.000001
        open_avg_sell_price = (oso / os) if os else 0.000001
        open_avg_buy_price  = max(open_avg_buy_price,  0.000001)
        open_avg_sell_price = max(open_avg_sell_price, 0.000001)

        raw_open_price = (
            (open_avg_buy_price + open_avg_sell_price) / 2
            if open_avg_buy_price and open_avg_sell_price
            else open_avg_buy_price or open_avg_sell_price or BASE_PRICE
        )
        open_price = max(raw_open_price, 0.000001)

        open_list.append({
            "token": tok,
            "adjusted_balance": round(adjusted_balance, 6),
            "buy_tokens": ob,
            "buy_orbit": obo,
            "sell_tokens": os,
            "sell_orbit": oso,
            "avg_buy_price": round(open_avg_buy_price, 6),
            "avg_sell_price": round(open_avg_sell_price, 6),
            "open_price": round(open_price, 6)
        })

        tx_counts.append({
            "token": tok,
            "exchange_cnt": transfer_cnt,
            "buy_cnt": buy_cnt,
            "sell_cnt": sell_cnt
        })


    # Extract time and price lists from history_data
    price_history_values = [None] * 14  # Pre-fill with None
    price_history_dates = [(datetime.datetime.utcnow() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
    date_index_map = {date: idx for idx, date in enumerate(price_history_dates)}
    error = []

    # Ensure we have two items: one for timestamps, one for prices
    if len(history_data) == 2:
        time_entry = history_data[0]
        price_entry = history_data[1]

        try:
            token_key = list(time_entry.keys())[0]
            timestamps = time_entry[token_key]
            prices = price_entry[token_key]

            if len(timestamps) != len(prices):
                error.append(f"⚠️ Mismatched timestamp/price lengths for {token_key}")

            for ts, price in zip(timestamps, prices):
                try:
                    dt = datetime.datetime.utcfromtimestamp(ts)
                    date_str = dt.strftime("%Y-%m-%d")
                    if date_str in date_index_map:
                        idx = date_index_map[date_str]
                        price_history_values[idx] = price
                except Exception as e:
                    error.append(f"⚠️ Failed to convert ts={ts} or price={price}: {e}")

        except Exception as e:
            error.append(f"⚠️ Error parsing history_data: {e}")
    else:
        error.append(f"⚠️ Unexpected history_data format: {history_data}")

    return stat_list, open_list, meta_list, tx_counts, dict(history_data), price_history_dates, price_history_values, open_orders
