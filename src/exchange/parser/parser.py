# --- Command Parser ---
def parse_exchange_command(message_content):
    try:
        parts = message_content.strip().split()
        if parts[0] != "[ExchangeRequest]":
            return None

        action = parts[1].lower()
        symbol = parts[2]
        amount = float(parts[3])
        addr = parts[4]

        return {
            "action": action,
            "symbol": symbol,
            "amount": amount,
            "address": addr
        }
    except Exception as e:
        print(f"Failed to parse command: {e}")
        return None
