# parser/parser.py

def parse_exchange_command(message_content):
    try:
        if message_content.startswith("[ExchangeRequest]"):
            parts = message_content.split()
            cmd_type = parts[1].upper()

            if cmd_type == "BUY":
                symbol = parts[2]
                amount = float(parts[3])
                buyer = parts[4]
                return {
                    "action": "buy",
                    "symbol": symbol,
                    "amount": amount,
                    "buyer": buyer
                }

            elif cmd_type == "BUYEX":
                symbol = parts[2]
                amount = float(parts[3])
                buyer = parts[4]
                return {
                    "action": "buy_from_exchange",
                    "symbol": symbol,
                    "amount": amount,
                    "buyer": buyer
                }

            elif cmd_type == "SELL":
                symbol = parts[2]
                amount = float(parts[3])
                seller = parts[4]
                return {
                    "action": "sell",
                    "symbol": symbol,
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

        return None
    except Exception as e:
        print(f"[ParserError] Failed to parse command: {e}")
        return None
