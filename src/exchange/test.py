from core.ioutil import fetch_chain


def get_user_tokens():
    address = "ORB.B77AC60F52529B834E4DAF21"
    tokens = {}
    chain = fetch_chain()

    for block in reversed(chain):
        for tx in block.get("transactions", []):
            note = tx.get("note")
            tx_type = note.get("type") if isinstance(note, dict) else None

            if isinstance(tx_type, dict):
                data = (
                    tx_type.get("token_transfer") or
                    tx_type.get("buy_token") or
                    tx_type.get("sell_token")
                )
                if data:
                    token = data.get("token_symbol") or data.get("symbol")
                    qty = data.get("amount")
                    if not token or not isinstance(qty, (int, float)):
                        continue

                    sender = data.get("sender")
                    receiver = data.get("receiver")

                    if receiver == address:
                        tokens[token] = tokens.get(token, 0) + qty
                    elif sender == address:
                        tokens[token] = tokens.get(token, 0) - qty
                continue

            # Handle ORBIT transfer (basic transaction)
            orbit_amount = tx.get("amount")
            if isinstance(orbit_amount, (int, float)):
                if tx.get("receiver") == address:
                    tokens["ORBIT"] = tokens.get("ORBIT", 0) + orbit_amount
                elif tx.get("sender") == address:
                    tokens["ORBIT"] = tokens.get("ORBIT", 0) - orbit_amount

    valid_tokens = ["ORBIT"] + sorted(
    [k for k, v in tokens.items() if v > 0 and k != "ORBIT"]
    )
    return valid_tokens


tokens = get_user_tokens()
print(tokens)
