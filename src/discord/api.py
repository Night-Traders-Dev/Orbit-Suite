import aiohttp, requests
from configure import explorer
from core.ioutil import fetch_chain

async def get_user_address(uid):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{explorer}/api/get_orbit_address", json={"uid": uid}) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("address")
        except Exception as e:
            return f"Request failed: {str(e)}"


async def get_user_balance(address, host=explorer):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{host}/api/balance/{address}") as response:
                if response.status == 200:
                    data = await response.json()
                    return data['total_balance'], data['available_balance'], data['locked_balance']
                else:
                    error_data = await response.json()
                    print(f"Error {response.status}: {error_data.get('error')}")
                    return None
        except Exception as e:
            print(f"Request failed: {e}")
            return None

async def create_2fa_api(address):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{explorer}/api/create_2fa", json={"address": address}) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("message")
        except Exception as e:
            return f"Request failed: {str(e)}"

async def verify_2fa_api(address, totp):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{explorer}/api/verify_2fa", json={"address": address, "totp": totp}) as response:
                return response.status == 200
        except Exception:
            return False

async def send_orbit_api(sender, recipient, amount, order=None):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{explorer}/api/send", json={
                "sender": sender,
                "recipient": recipient,
                "amount": amount,
                "order": order
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, data.get("message", "Transaction successful.")
                else:
                    data = await response.json()
                    return False, data.get("error", "Unknown error.")
        except Exception as e:
            return False, f"Request failed: {str(e)}"


async def mine_orbit_api(address):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{explorer}/api/mine", json={"address": address}) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return "success", data
                else:
                    return "fail", data.get("message", "Unknown error")
    except Exception as e:
        return "fail", str(e)

async def lock_orbit_api(address, amount, duration):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{explorer}/api/lock", json={"address": address, "amount": amount,"duration": duration}) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return "success", data
                else:
                    return "fail", data.get("message", "Unknown error")
    except Exception as e:
        return "fail", str(e)

async def claim_rewards_api(address):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{explorer}/api/claim", json={"address": address}) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return "success", data
                else:
                    return "fail", data.get("message", "Unknown error")
    except Exception as e:
        return "fail", str(e)



async def claim_check_api(address):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{explorer}/api/claim_check", json={"address": address}) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return "success", data
                else:
                    return "fail", data.get("message", "Unknown error")
    except Exception as e:
        return "fail", str(e)


async def mine_check_api(address):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{explorer}/api/mine_check", json={"address": address}) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return "success", data
                else:
                    return "fail", data.get("message", "Unknown error")
    except Exception as e:
        return "fail", str(e)





def get_user_tokens(address):
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
