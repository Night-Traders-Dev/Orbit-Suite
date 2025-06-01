import aiohttp, requests
from config import explorer

async def get_user_address(uid):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{explorer}/api/get_orbit_address", json={"uid": uid}) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("address")
        except Exception as e:
            return f"Request failed: {str(e)}"

def get_user_balance(address, host=explorer):
    try:
        response = requests.get(f"{host}/api/balance/{address}")
        if response.status_code == 200:
            data = response.json()
            return data['total_balance'], data['available_balance'], data['locked_balance']
        else:
            print(f"Error {response.status_code}: {response.json().get('error')}")
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

async def send_orbit_api(sender, recipient, amount):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{explorer}/api/send", json={
                "sender": sender, "recipient": recipient, "amount": amount
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
            async with session.post(f"{explorer}/api/lock", json={"user": username, "amount": amount,"duration": duration}) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return "success", data
                else:
                    return "fail", data.get("message", "Unknown error")
    except Exception as e:
        return "fail", str(e)
