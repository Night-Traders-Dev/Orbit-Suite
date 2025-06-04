def get_all_tokens(chain=None):
    from flask import g
    import json

    if chain is None:
        chain = g.chain

    tokens = []

    for block in chain:
        for tx in block.get("transactions", []):
            note = tx.get("note")
            if isinstance(note, dict) and note.get("type") == "create_token":
                token = {
                    "symbol": note.get("symbol", ""),
                    "name": note.get("name", ""),
                    "creator": tx.get("sender", ""),
                    "supply": float(note.get("supply", 0)),
                    "token_id": note.get("token_id", ""),
                    "created_at": tx.get("timestamp", "")
                }
                tokens.append(token)

    return tokens
