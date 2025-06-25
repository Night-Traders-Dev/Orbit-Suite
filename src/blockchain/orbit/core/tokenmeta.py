from core.orderutil import token_stats
import datetime
async def get_token_meta(symbol):
    token_sym = symbol.upper()
    token_meta = {}

    try:
        filled, open_orders, metadata, tx_cnt, history_data, price_history_dates, price_history_values, open_book = await token_stats(token_sym)

        filled_dict = {stat["token"]: stat for stat in filled if isinstance(stat, dict)}
        open_dict = {stat["token"]: stat for stat in open_orders if isinstance(stat, dict)}
        meta_dict = {stat["symbol"]: stat for stat in metadata if isinstance(stat, dict)}
        cnt_dict = {stat["token"]: stat for stat in tx_cnt if isinstance(stat, dict)}

        all_tokens = sorted(set(filled_dict.keys()) | set(open_dict.keys()) | set(meta_dict.keys()) | set(cnt_dict.keys()))

        if not all_tokens:
            print("No valid tokens found in stats.")

        for token in all_tokens:
            if token != token_sym:
                continue

            f_stat = filled_dict.get(token, {})
            o_stat = open_dict.get(token, {})
            m_stat = meta_dict.get(token, {})
            c_stat = cnt_dict.get(token, {})

            # 📊 Filled Order Stats
            filled_tokens_bought = f_stat.get("buy_tokens", 0)
            filled_orbit_spent = f_stat.get("buy_orbit", 0)
            filled_tokens_sold = f_stat.get("sell_tokens", 0)
            filled_orbit_earned = f_stat.get("sell_orbit", 0)
            filled_avg_buy_price = f_stat.get("avg_buy_price", 0)
            filled_avg_sell_price = f_stat.get("avg_sell_price", 0)
            net_balance = f_stat.get("adjusted_balance", 0)

            # 📊 Open Order Stats
            open_tokens_bought = o_stat.get("buy_tokens", 0)
            open_orbit_spent = o_stat.get("buy_orbit", 0)
            open_tokens_sold = o_stat.get("sell_tokens", 0)
            open_orbit_earned = o_stat.get("sell_orbit", 0)
            open_avg_buy_price = o_stat.get("avg_buy_price", 0)
            open_avg_sell_price = o_stat.get("avg_sell_price", 0)

            # 🧬 Metadata
            meta_id = m_stat.get("id", "")
            meta_name = m_stat.get("name", "")
            meta_symbol = m_stat.get("symbol", token_sym)
            meta_supply = m_stat.get("supply", net_balance)
            meta_owner = m_stat.get("owner", "")
            meta_created_raw = m_stat.get("created", "")
            meta_created = ""
            if meta_created_raw:
                try:
                    dt = datetime.datetime.strptime(meta_created_raw, "%Y-%m-%d %H:%M:%S")
                    meta_created = dt.strftime("%b %d, %Y")
                except:
                    meta_created = meta_created_raw

            # 📈 Price (fallback to BASE_PRICE or initial price if needed)
            current_price = f_stat.get("current_price") or m_stat.get("initial_price") or 0.1

            # 🔁 Exchange Stats
            exchange_cnt = c_stat.get("exchange_cnt", 0)
            buy_cnt = c_stat.get("buy_cnt", 0)
            sell_cnt = c_stat.get("sell_cnt", 0)

            # 📊 Progress Bar Ratio
            total_volume = filled_tokens_bought + filled_tokens_sold
            buy_ratio = (filled_tokens_bought / total_volume * 100) if total_volume > 0 else 0

            buy_order_book = []
            sell_order_book = []

            for order in open_book:
                price = float(order.get("price", 0))
                type = order.get("type")
                qty = float(order.get("amount", 0))
                if type == "buy":
                    buy_order_book.append({"price": price, "quantity": qty})
                else:
                    sell_order_book.append({"price": price, "quantity": qty})


            buy_order_book = sorted(buy_order_book, key=lambda x: -x["price"])
            sell_order_book = sorted(sell_order_book, key=lambda x: x["price"])

            def cumulative_orders(order_book):
                cum_qty = 0
                cum_data = []
                for entry in order_book:
                    cum_qty += entry["quantity"]
                    cum_data.append({"price": entry["price"], "cum_quantity": cum_qty})
                return cum_data

            token_meta["buy_depth"] = cumulative_orders(buy_order_book)
            token_meta["sell_depth"] = cumulative_orders(sell_order_book)

            # Convert timestamped entries to daily price points
            date_index_map = {date: idx for idx, date in enumerate(price_history_dates)}
            for entry in history_data:
                if isinstance(entry, dict):
                    try:
                        ts = float(entry.get("time", 0))
                        dt = ts.fromtimestamp(datetime.timezone.utc)
                        date_str = dt.strftime("%Y-%m-%d")
                        price = entry.get("price")
                        if date_str in date_index_map:
                            idx = date_index_map[date_str]
                            price_history_values[idx] = price
                    except Exception as e:
                         print(f"⚠️ Failed to parse entry: {entry} — {e}")
                else:
                    pass
#                    print(f"⚠️ Skipping malformed history entry: {entry}")


            token_meta.update({
                "name": meta_name,
                "symbol": token_sym,
                "current_price": current_price,
                "supply": meta_supply,
                "circulating": (round(filled_tokens_bought, 6) - round(filled_tokens_sold, 6)),
                "mc": (current_price * filled_tokens_bought),
                "volume_received": filled_tokens_bought,
                "volume_sent": filled_tokens_sold,
                "orbit_spent_buying": filled_orbit_spent,
                "orbit_earned_selling": filled_orbit_earned,
                "avg_buy_price": filled_avg_buy_price,
                "avg_sell_price": filled_avg_sell_price,
                "creator": meta_owner,
                "created_at": meta_created,
                "exchange_cnt": exchange_cnt,
                "buy_cnt": (buy_cnt + exchange_cnt),
                "sell_cnt": sell_cnt,
                "buy_ratio": round(buy_ratio, 2),
                "price_history_dates": price_history_dates,
                "price_history_values": price_history_values,
                "open_buy_tokens": open_tokens_bought,
                "open_sell_tokens": open_tokens_sold
            })


        token_meta["buy_depth"] = cumulative_orders(buy_order_book)
        token_meta["sell_depth"] = cumulative_orders(sell_order_book)
        return token_meta

    except Exception as e:
        return {"error": e}
#    finally:
#        return token_meta