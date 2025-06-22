import requests
from collections import defaultdict
from core.ioutil import fetch_chain
import datetime

BASE_PRICE = 0.1
TOKEN = "FUEL"


async def all_tokens_stats(symbol_filter=None):
    """
    Safe, side-effect-free stats over the entire chain.
    Returns: (token_list, wallets, metrics)
    """
    now   = datetime.datetime.now(datetime.timezone.utc)
    t24   = now - datetime.timedelta(days=1)

    if symbol_filter:
        if isinstance(symbol_filter, str):
            symbol_filter = {symbol_filter.upper()}
        else:
            symbol_filter = {s.upper() for s in symbol_filter}

    tokens          = {}   # symbol -> metadata & counters
    wallets         = {}   # address -> {"amount": net_float}
    total_transfers = 0
    transfers_24h   = 0
    new_tokens_24h  = 0

    def parse_ts(ts):
        try:
            if isinstance(ts, str):
                return datetime.datetime.fromisoformat(ts).astimezone(datetime.timezone.utc)
            if isinstance(ts, (int, float)):
                return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
        except:
            pass
        return None

    try:
        chain = fetch_chain()  # assume returns list of blocks
    except Exception:
        print("[WARN] fetch_chain() failed, returning empty stats")
        return [], {}, {
            "total_transfers":  0,
            "transfers_24h":    0,
            "total_tokens":     0,
            "new_tokens_24h":   0
        }

    for block in chain:
        for tx in block.get("transactions", []):
            note = tx.get("note")
            if not isinstance(note, dict):
                continue

            tx_type = note.get("type")
            if not isinstance(tx_type, dict):
                continue

            # Token creation
            if "create_token" in tx_type:
                d = tx_type["create_token"]
                if not isinstance(d, dict):
                    continue
                sym   = d.get("symbol")
                if not sym or (symbol_filter and sym.upper() not in symbol_filter):
                    continue

                name    = d.get("name", "").strip()
                supply  = float(d.get("supply") or 0.0)
                creator = d.get("creator")
                created = parse_ts(d.get("timestamp"))

                if name and sym:
                    tokens[sym] = {
                        "symbol":     sym,
                        "name":       name,
                        "supply":     supply,
                        "creator":    creator,
                        "created_at": created,
                        "age":        "",
                        "transfers":  0,
                        "holders":    set()
                    }
                    if created and (now - created <= datetime.timedelta(days=1)):
                        new_tokens_24h += 1

            for key in ("token_transfer", "buy_token", "sell_token"):
                if key not in tx_type:
                    continue
                d = tx_type[key]
                if not isinstance(d, dict):
                    continue

                sym = d.get("token_symbol") or d.get("symbol")
                if not sym or (symbol_filter and sym.upper() not in symbol_filter):
                    continue

                sender   = d.get("sender")
                receiver = d.get("receiver")
                amt_raw  = d.get("amount", 0)
                try:
                    amount = float(amt_raw)
                except Exception:
                    continue

                # update token‐level counters
                if sym in tokens:
                    tokens[sym]["transfers"] += 1
                    if sender:   tokens[sym]["holders"].add(sender)
                    if receiver: tokens[sym]["holders"].add(receiver)

                # update wallet balances
                if sender:
                    wallets.setdefault(sender, {"amount": 0.0})
                    wallets[sender]["amount"] = max(wallets[sender]["amount"] - amount, 0.0001)
                if receiver:
                    wallets.setdefault(receiver, {"amount": 0.0})
                    wallets[receiver]["amount"] += amount

                ts = parse_ts(tx.get("timestamp"))
                total_transfers += 1
                if ts and (now - ts <= datetime.timedelta(days=1)):
                    transfers_24h += 1

    token_list = []
    for sym, info in tokens.items():
        created = info["created_at"]
        if created:
            age_days = (now - created).days
            info["age"] = f"{age_days} day{'s' if age_days != 1 else ''}"
        else:
            info["age"] = "Unknown"
        info["holders"] = len(info["holders"])
        token_list.append(info)

    token_list.sort(key=lambda x: x["symbol"].lower())

    metrics = {
        "total_transfers": total_transfers,
        "transfers_24h":   transfers_24h,
        "total_tokens":    len(token_list),
        "new_tokens_24h":  new_tokens_24h
    }

    return token_list, wallets, metrics



async def token_stats(token=TOKEN):
    chain = fetch_chain()
    tokens = {}
    filled_stats = {}
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
                    stats["buy_orbit"] += max(orbit_amount, 0.0001)
                    transfer_cnt += 1
                    exchange_only[tok] = True
                elif tx_note == "Token sold to exchange":
                    stats["sell_tokens"] += qty
                    stats["sell_orbit"] += max(orbit_amount, 0.0001)
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
                    fill_stats["buy_orbit"] += qty * max(price, 0.0001)
                    buy_cnt += 1
                    traded_tokens.add(tok)

                    if created_at and qty > 0:
                        history_data[tok].append({
                            "time": created_at,
                            "price": round(price, 4)
                        })
                else:
                    if order_id in filled_order_ids:
                        continue
                    open_order_ids.add(order_id)

                    tokens[tok] = tokens.get(tok, 0) + qty
                    op_stats = await get_stats(open_stats, tok)
                    op_stats["buy_tokens"] += qty
                    op_stats["buy_orbit"] += qty * max(price, 0.0001)
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
                    fill_stats["sell_orbit"] += qty * max(price, 0.0001)
                    sell_cnt += 1
                    traded_tokens.add(tok)

                    if created_at and qty > 0:
                        history_data[tok].append({
                            "time": created_at,
                            "price": round(price, 4)
                        })
                else:
                    if order_id in filled_order_ids:
                        continue
                    open_order_ids.add(order_id)

                    tokens[tok] = tokens.get(tok, 0) - qty
                    op_stats = await get_stats(open_stats, tok)
                    op_stats["sell_tokens"] += qty
                    op_stats["sell_orbit"] += qty * max(price, 0.0001)
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
        net_tokens = fb - fs
        net_orbit = fbo - fso
        avg_buy_price = (net_orbit / net_tokens) if net_tokens else 0.0001
        avg_sell_price = (fso / fs) if fs else 0.0001
        avg_buy_price  = max(avg_buy_price,  0.0001)
        avg_sell_price = max(avg_sell_price, 0.0001)


        raw_price = (
            (avg_buy_price + avg_sell_price) / 2
            if avg_buy_price and avg_sell_price
            else avg_buy_price or avg_sell_price or BASE_PRICE
        )
        current_price = max(raw_price, 0.0001)
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
        open_avg_buy_price = (open_net_orbit / open_net_tokens) if open_net_tokens else 0.0001
        open_avg_sell_price = (oso / os) if os else 0.0001
        open_avg_buy_price  = max(open_avg_buy_price,  0.0001)
        open_avg_sell_price = max(open_avg_sell_price, 0.0001)

        raw_open_price = (
            (open_avg_buy_price + open_avg_sell_price) / 2
            if open_avg_buy_price and open_avg_sell_price
            else open_avg_buy_price or open_avg_sell_price or BASE_PRICE
        )
        open_price = max(raw_open_price, 0.0001)

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
