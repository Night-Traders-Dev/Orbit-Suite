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
    token_meta = {}

    try:
        filled, open_orders, metadata, tx_cnt, history_data, \
        price_history_dates, price_history_values, open_book = await token_stats(token_sym)

        # build your lookup dicts…
        filled_dict = {s["token"]: s for s in filled if isinstance(s, dict)}
        open_dict   = {s["token"]: s for s in open_orders if isinstance(s, dict)}
        meta_dict   = {m["symbol"]: m for m in metadata   if isinstance(m, dict)}
        cnt_dict    = {c["token"]: c for c in tx_cnt      if isinstance(c, dict)}
        all_tokens  = sorted(set(filled_dict) | set(open_dict) | set(meta_dict) | set(cnt_dict))

        if not all_tokens:
            print("No valid tokens found in stats.")

        # find the one we care about
        for tok in all_tokens:
            if tok != token_sym:
                continue

            f_stat = filled_dict.get(tok, {})
            o_stat = open_dict.get(tok, {})
            m_stat = meta_dict.get(tok, {})
            c_stat = cnt_dict.get(tok, {})

            # --- Filled order stats ---
            fb  = f_stat.get("buy_tokens",  0)
            fbo = f_stat.get("buy_orbit",   0)
            fs  = f_stat.get("sell_tokens", 0)
            fso = f_stat.get("sell_orbit",  0)

            # clamp averages
            avg_buy  = ensure_min(f_stat.get("avg_buy_price",  0))
            avg_sell = ensure_min(f_stat.get("avg_sell_price", 0))

            # --- Open order stats ---
            ob  = o_stat.get("buy_tokens",  0)
            obo = o_stat.get("buy_orbit",   0)
            os_ = o_stat.get("sell_tokens", 0)
            oso = o_stat.get("sell_orbit",  0)

            open_avg_buy  = ensure_min(o_stat.get("avg_buy_price",  0))
            open_avg_sell = ensure_min(o_stat.get("avg_sell_price", 0))

            # --- Metadata ---
            name    = m_stat.get("name", "")
            supply  = m_stat.get("supply", fb - fs)
            owner   = m_stat.get("owner", "")
            raw_dt  = m_stat.get("created", "")
            created = ""
            if raw_dt:
                try:
                    dt = datetime.datetime.strptime(raw_dt, "%Y-%m-%d %H:%M:%S")
                    created = dt.strftime("%b %d, %Y")
                except:
                    created = raw_dt

            # --- Current price (clamped) ---
            raw_price     = f_stat.get("current_price") \
                            or m_stat.get("initial_price") \
                            or BASE_PRICE
            current_price = ensure_min(raw_price)

            # --- Counters ---
            exch_cnt = c_stat.get("exchange_cnt", 0)
            buy_cnt  = c_stat.get("buy_cnt",      0)
            sell_cnt = c_stat.get("sell_cnt",     0)

            # --- Progress bar ratio ---
            total_vol = fb + fs
            buy_ratio = (fb / total_vol * 100) if total_vol else 0

            # --- Build depth charts ---
            buy_book, sell_book = [], []
            for o in open_book:
                p = ensure_min(o.get("price", 0))
                q = float(o.get("amount", 0))
                if o.get("type") == "buy":
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

            token_meta["buy_depth"]  = cum(buy_book)
            token_meta["sell_depth"] = cum(sell_book)

            # --- Fill price history (clamped) ---
            idx_map = {d:i for i,d in enumerate(price_history_dates)}
            for h in history_data:
                if not isinstance(h, dict):
                    continue
                try:
                    ts    = float(h.get("time", 0))
                    ds    = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                    pr    = ensure_min(h.get("price", 0))
                    if ds in idx_map:
                        price_history_values[idx_map[ds]] = pr
                except Exception as err:
                    print("History parse error:", err)

            # --- Finally pack up ---
            token_meta.update({
                "name": name,
                "symbol": token_sym,
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
                "open_avg_sell_price":  round(open_avg_sell, 6)
            })

        # wrap into an object for Jinja dot‐access
        return SimpleNamespace(**token_meta)

    except Exception as e:
        # always return an object
        return SimpleNamespace(error=str(e))