from core.ioutil import fetch_chain

def token_metrics(symbol):
    symbol = symbol.upper()
    ledger = fetch_chain()
    token_info = None

    total_tokens_received = 0.0
    total_tokens_sent = 0.0
    total_orbit_spent = 0.0  # Orbit used to buy this token
    total_orbit_earned = 0.0  # Orbit earned from selling this token

    unique_receivers = set()
    unique_senders = set()

    for block in ledger:
        for tx in block.get("transactions", []):
            note = tx.get("note", {})
            orbit_amount = tx.get("amount")

            if not isinstance(note, dict) or "type" not in note:
                continue

            tx_type = note["type"]

            # Token creation
            if "create_token" in tx_type:
                data = tx_type["create_token"]
                if data.get("symbol", "").upper() == symbol:
                    token_info = {
                        "token_id": data.get("token_id"),
                        "name": data.get("name"),
                        "symbol": data.get("symbol"),
                        "supply": data.get("supply"),
                        "creator": data.get("creator"),
                        "created_at": data.get("timestamp")
                    }

            # Token transfers
            if "token_transfer" in tx_type:
                data = tx_type["token_transfer"]
                if data.get("token_symbol", "").upper() != symbol:
                    continue

                amount = float(data.get("amount", 0))
                sender = data.get("sender")
                receiver = data.get("receiver")

                if receiver:
                    total_tokens_received += amount
                    unique_receivers.add(receiver)

                if sender:
                    total_tokens_sent += amount
                    unique_senders.add(sender)

                # Buy (receiver got token, orbit_amount is what they paid)
                if receiver and orbit_amount:
                    total_orbit_spent += orbit_amount

                # Sell (sender gave token, orbit_amount is what they earned)
                if sender and orbit_amount:
                    total_orbit_earned += orbit_amount


    token_info.update({
        "volume_received": round(total_tokens_received, 6),
        "volume_sent": round(total_tokens_sent, 6),
        "orbit_spent_buying": round(total_orbit_spent, 6),
        "orbit_earned_selling": round(total_orbit_earned, 6),
        "unique_holders": len(unique_receivers | unique_senders),
        "unique_buyers": len(unique_receivers),
        "unique_sellers": len(unique_senders),
    })

    return token_info
print(token_metrics("CTOKEN"))
