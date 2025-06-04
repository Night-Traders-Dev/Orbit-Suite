from blockchain.stakeutil import get_user_lockups
from flask import request
import json, time

def locked():
    now = time.time()
    user_filter = request.args.get("user", "").strip().lower()
    min_amount = float(request.args.get("min_amount", 0))
    min_days = int(request.args.get("min_days", 0))
    sort = request.args.get("sort", "date")

    if user_filter:
        raw_lockups = get_user_lockups(user_filter)
    else:
        raw_lockups = get_user_lockups("all")

    locks = []
    total_claimed = 0.0

    for lock in raw_lockups:
        try:
            username = lock.get("user", "unknown")
            amount = float(lock["amount"])
            duration = int(lock["days"])
            end = lock["end"]
            days_remaining = max(0, int((end - now) / 86400))
            timestamp = lock["start"]

            if (
                (not user_filter or user_filter in username.lower()) and
                amount >= min_amount and
                duration >= min_days
            ):
                locks.append({
                    "username": username,
                    "amount": amount,
                    "duration": duration,
                    "days_remaining": days_remaining,
                    "timestamp": timestamp
                })
        except Exception:
            continue

    if sort == "amount":
        locks.sort(key=lambda x: -x["amount"])
    elif sort == "user":
        locks.sort(key=lambda x: x["username"])
    else:
        locks.sort(key=lambda x: x["timestamp"])

    totals = {
        "total_locked": sum(lock["amount"] for lock in locks),
        "count": len(locks),
        "avg_days": round(sum(lock["duration"] for lock in locks) / len(locks), 1) if locks else 0,
        "total_claimed": round(total_claimed, 4)
    }

    return "locked.html", locks, totals, sort
