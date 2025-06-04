# exchangeutil.py
import json
import os
import time
from blockchain.tokenutil import send_orbit
from core.ioutil import fetch_chain
from core.tx_util.tx_types import TXExchange


def send_token_transaction(sender, receiver, amount, token_symbol, note=""):

    unsigned_tx = TXExchange.create_token_transfer_tx(
        sender=sender,
        receiver=receiver,
        amount=amount,
        token_symbol=token_symbol,
        note=note,
        signature=""
    )

    tx_type = list(unsigned_tx["type"].keys())[0]
    tx_data = unsigned_tx["type"][tx_type]
    unsigned_tx["type"][tx_type] = tx_data

    if validate_token_transfer(unsigned_tx):
        send_orbit(sender, "mining", 0.1, order=unsigned_tx)


def get_user_token_balance(address, token_symbol):
    chain = fetch_chain()
    balance = 0

    for block in chain:
        for tx in block.get("transactions", []):
            if "type" not in tx or "token_transfer" not in tx["type"]:
                continue

            data = tx["type"]["token_transfer"]
            if data["token_symbol"] != token_symbol:
                continue
            if data["receiver"] == address:
                balance += data["amount"]
            if data["sender"] == address:
                balance -= data["amount"]

    return balance

def get_all_user_token_holdings(address):
    chain = fetch_chain()
    holdings = {}

    for block in chain:
        for tx in block.get("transactions", []):
            if "type" not in tx or "token_transfer" not in tx["type"]:
                continue

            data = tx["type"]["token_transfer"]
            symbol = data["token_symbol"]

            if data["receiver"] == address:
                holdings[symbol] = holdings.get(symbol, 0) + data["amount"]
            if data["sender"] == address:
                holdings[symbol] = holdings.get(symbol, 0) - data["amount"]

    return {sym: amt for sym, amt in holdings.items() if amt > 0}


def validate_token_transfer(tx, chain=None):
    if "type" not in tx or "token_transfer" not in tx["type"]:
        return False, "Invalid transaction type"

    data = tx["type"]["token_transfer"]
    required_fields = ["sender", "receiver", "amount", "token_symbol", "timestamp", "signature"]
    if not all(field in data for field in required_fields):
        return False, "Missing required fields"

    if data["amount"] <= 0:
        return False, "Invalid amount"

    # Signature verification
    signature_valid = verify_signature(data, data["signature"], data["sender"])
    if not signature_valid:
        return False, "Invalid signature"

    # Balance check
    if chain is None:
        chain = fetch_chain()
    balance = get_user_token_balance(data["sender"], data["token_symbol"])
    if balance < data["amount"]:
        return False, "Insufficient balance"

    return True, "Valid token transfer"


def get_token_id(symbol):
    """
    Search the blockchain ledger for a token creation transaction with the given symbol
    and return its token_id.
    """
    for block in reversed(fetch_chain()):  # Iterate from latest to oldest
        for tx in block["transactions"]:
            if "create_token" in tx.get("type", {}):
                token_data = tx["type"]["create_token"]
                if token_data.get("symbol") == symbol:
                    return token_data.get("token_id")
    return None  # Token not found
