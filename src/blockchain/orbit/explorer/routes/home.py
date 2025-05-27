from explorer.util.util import get_chain_summary, search_chain
from flask import request
import math

PAGE_SIZE = 5

def home(chain):
    query = request.args.get("q", "").strip()
    if query:
        return search_chain(query)

    page = int(request.args.get("page", 1))
    total_pages = max(1, math.ceil(len(chain) / PAGE_SIZE))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    blocks = chain[::-1][start:end]
    summary = get_chain_summary()

    return (
        "home.html",
        chain,
        query,
        page,
        total_pages,
        blocks,
        summary
    )
