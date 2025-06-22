# tokenmeta.py

import datetime
from types import SimpleNamespace
from core.orderutil import token_stats

# clamp helper
def ensure_min(val, min_val=0.000001):
    try:
        v = float(val)
    except Exception:
        return min_val
    return v if v >= min_val else min_val

async def get_token_meta(symbol):
    token_sym = symbol.upper()
    print(token_sym)

    # ALWAYS include symbol so SimpleNamespace.symbol exists
    token_meta = {"symbol": token_sym}

    try:
        # 1) fetch raw stats
        filled, open_orders, metadata, tx_cnt, history_data, \
        price_history_dates, price_history_values, open_book = await token_stats(token_sym)

        # 2) index by symbol/token
        filled_dict = {s["token"]: s for s in filled if isinstance(s, dict)}
        open_dict   = {s["token"]: s for s in open_orders if isinstance(s, dict)}
        meta_dict   = {m["symbol"]: m for m in metadata   if isinstance(m, dict)}
        cnt_dict    = {c["token"]: c for c in tx_cnt      if isinstance(c, dict)}
        all_tokens  = sorted(set(filled_dict) | set(open_dict) | set(meta_dict) | set(cnt_dict))

        if token_sym not in all_tokens:
            # no data for this token
            token_meta["error"] = f"No stats found for '{token_sym}'"
            return SimpleNamespace(**token_meta)

        # 3) pull the one record we care about
        f = filled_dict.get(token_sym, {})
        o = open_dict.get(token_sym,   {})
        m = meta_dict.get(token_sym,   {})
        c = cnt_dict.get(token_sym,    {})

        # Filled stats
        fb  = f.get("buy_tokens",  0.000001)
        fbo = f.get("buy_orbit",   0.000001)
        fs  = f.get("sell_tokens", 0.)
        fso = f.get("sell_orbit",  0.000001)
        avg_buy  = ensure_min(f.get("avg_buy_price",  0.000001))
        avg_sell = ensure_min(f.get("avg_sell_price", 0.))

        # Open stats
        ob  = o.get("buy_tokens",  0.000001)
        obo = o.get("buy_orbit",   0.000001)
        os_ = o.get("sell_tokens", 0.000001)
        oso = o.get("sell_orbit",  0.000001)
        open_avg_buy  = ensure_min(o.get("avg_buy_price",  0))
        open_avg_sell = ensure_min(o.get("avg_sell_price", 0))

        # Metadata
        name    = m.get("name", "")
        supply  = m.get("supply", fb - fs)
        owner   = m.get("owner", "")
        raw_dt  = m.get("created", "")
        created = ""
        if raw_dt:
            try:
                dt = datetime.datetime.strptime(raw_dt, "%Y-%m-%d %H:%M:%S")
                created = dt.strftime("%b %d, %Y")
            except:
                created = raw_dt

        # Current price
        raw_price     = f.get("current_price") or m.get("initial_price") or 0.000001
        current_price = ensure_min(raw_price)

        # Counters
        exch_cnt = c.get("exchange_cnt", 0)
        buy_cnt  = c.get("buy_cnt",      0)
        sell_cnt = c.get("sell_cnt",     0)

        # Buy ratio
        total_vol = fb + fs
        buy_ratio = (fb / total_vol * 100) if total_vol else 0

        # Build depth books
        buy_book, sell_book = [], []
        for order in open_book:
            p = ensure_min(order.get("price", 0))
            q = float(order.get("amount", 0))
            if order.get("type") == "buy":
                buy_book.append({"price": p, "quantity": q})
            else:
                sell_book.append({"price": p, "quantity": q})
        buy_book  = sorted(buy_book,  key=lambda e: -e["price"])
        sell_book = sorted(sell_book, key=lambda e:  e["price"])
        def cum(book):
            csum, out = 0, []
            for e in book:
                csum += e["quantity"]
                out.append({"price": e["price"], "cum_quantity": csum})
            return out

        # Populate token_meta
        token_meta.update({
            "name":                name,
            "current_price":       round(current_price, 6),
            "supply":              supply,
            "circulating":         fb - fs,
            "mc":                  round(current_price * fb, 6),
            "volume_received":     fb,
            "volume_sent":         fs,
            "orbit_spent_buying":  fbo,
            "orbit_earned_selling": fso,
            "avg_buy_price":       round(avg_buy, 6),
            "avg_sell_price":      round(avg_sell, 6),
            "creator":             owner,
            "created_at":          created,
            "exchange_cnt":        exch_cnt,
            "buy_cnt":             buy_cnt + exch_cnt,
            "sell_cnt":            sell_cnt,
            "buy_ratio":           round(buy_ratio, 2),
            "price_history_dates":  price_history_dates,
            "price_history_values": price_history_values,
            "open_buy_tokens":      ob,
            "open_sell_tokens":     os_,
            "open_avg_buy_price":   round(open_avg_buy, 6),
            "open_avg_sell_price":  round(open_avg_sell, 6),
            "buy_depth":            cum(buy_book),
            "sell_depth":           cum(sell_book)
        })

        return SimpleNamespace(**token_meta)

    except Exception as exc:
        # on any error still return symbol + error
        token_meta["error"] = str(exc)
        return SimpleNamespace(**token_meta)