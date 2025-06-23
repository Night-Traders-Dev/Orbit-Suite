# parser/parser.py

async def parse_exchange_command(message_content):
    try:
        if message_content.startswith("[ExchangeRequest]"):
            parts = message_content.split()
            cmd_type = parts[1].upper()

            if cmd_type == "BUY":
                symbol = parts[2]
                price = float(parts[3])
                amount = float(parts[4])
                buyer = parts[5]
                return {
                    "action": "buy",
                    "symbol": symbol,
                    "price": price,
                    "amount": amount,
                    "buyer": buyer
                }

            elif cmd_type == "BUYEX":
                symbol = parts[2]
                amount = float(parts[3])
                buyer = parts[4]
                return {
                    "action": "buy_token_from_exchange",
                    "symbol": symbol,
                    "amount": amount,
                    "buyer": buyer
                }

            elif cmd_type == "SWAP":
                symbol = parts[2]
                amount = float(parts[3])
                buyer = parts[4]
                return {
                    "action": "swap_token",
                    "amount": amount,
                    "buyer": buyer
                }

            elif cmd_type == "TRADEEX":
                symbol = parts[2]
                amount = float(parts[3])
                owner = parts[4]
                tx_type = parts[5].upper()
                if tx_type == "BUY":
                    return {
                        "symbol": symbol,
                        "amount": amount,
                        "owner": owner,
                        "action": tx_type
                    }
                elif tx_type == "SELL":
                    return {
                        "symbol": symbol,
                        "amount": amount,
                        "owner": owner,
                        "action": tx_type
                    }
                else:
                    print(f"[ParserError] Unknown transaction type: {tx_type}")
                    return None


            elif cmd_type == "SELL":
                symbol = parts[2]
                price = float(parts[3])
                amount = float(parts[4])
                seller = parts[5]
                return {
                    "action": "sell",
                    "symbol": symbol,
                    "price": price,
                    "amount": amount,
                    "seller": seller
                }

            elif cmd_type == "CANCEL":
                order_id = parts[2]
                return {
                    "action": "cancel",
                    "order_id": order_id
                }

            elif cmd_type == "QUOTE":
                symbol = parts[2]
                return {
                    "action": "quote",
                    "symbol": symbol
                }

            elif cmd_type == "CREATE":
                name = parts[2]
                symbol = parts[3]
                supply = int(float(parts[4]))
                creator = parts[5]
                return {
                    "action": "create",
                    "name": name,
                    "symbol": symbol,
                    "supply": supply,
                    "creator": creator
                }
            elif cmd_type == "DEPOSIT":
                symbol = parts[2]
                amount = float(parts[3])
                address = parts[4]
                return {
                    "action": "deposit",
                    "symbol": symbol,
                    "amount": amount,
                    "address": address
                }

            elif cmd_type == "WITHDRAWAL":
                amount = float(parts[2])
                address = parts[3]
                return {
                    "action": "withdrawal",
                    "amount": amount,
                    "address": address
                }

        return None
    except Exception as e:
        print(f"[ParserError] Failed to parse command: {e}")
        return None


