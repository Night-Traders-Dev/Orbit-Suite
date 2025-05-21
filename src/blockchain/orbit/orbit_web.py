from flask import Flask, render_template, request, redirect, session, url_for, flash
from core.userutil import web_login, web_logout, web_register
from blockchain.miningutil import start_mining
from blockchain.tokenutil import send_orbit
from core.walletutil import load_balance
from blockchain.stakeutil import get_user_lockups, claim_lockup_rewards
from blockchain.orbitutil import load_nodes
from blockchain.ledgerutil import view_user_transactions
from blockchain.blockutil import load_chain
from core.userutil import load_users, save_users
from datetime import datetime



def last_transactions(address, limit=10):
    txs = []
    for block in reversed(load_chain()):
        for tx in block.get("transactions", []):
            if tx["sender"] == address or tx["recipient"] == address:
                txs.append(tx)
                if len(txs) >= limit:
                    return txs
    return txs

app = Flask(__name__)
app.secret_key = "super_secure_key"


@app.template_filter("ts")
def format_timestamp(value):
    try:
        return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "N/A"

@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def do_login():
    result = web_login(username=request.form["username"], password=request.form["password"])
    if result:
        session["user"], session["node_id"] = result
        return redirect(url_for("dashboard"))
    flash("Login failed")
    return redirect(url_for("home"))

@app.route("/register", methods=["GET", "POST"])
def do_register():
    if request.method == "POST":
        if web_register(username=request.form["username"], password=request.form["password"]):
            return redirect(url_for("home"))
        flash("Registration failed")
    return render_template("register.html")

@app.route("/dashboard")
def wallet_dashboard():
    username = session.get("user")
    balance, locked = load_balance(username)
    locks = get_user_lockups(username)
    last10 = last_transactions(username)
    claimable = sum(l.get("reward", 0) for l in locks if l.get("matured"))

    sent = received = 0
    for block in load_chain():
        for tx in block.get("transactions", []):
            if tx["sender"] == username:
                sent += tx["amount"]
            if tx["recipient"] == username:
                received += tx["amount"]

    return render_template("dashboard.html", user_data={
        "username": username,
        "balance": balance,
        "locked": locked,
        "claimable": claimable,
        "sent": sent,
        "received": received,
        "last10": last10
    })


@app.route("/wallet")
def wallet():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))
    available, locked = load_balance(user)
    return render_template("wallet.html", available=available, locked=locked)

@app.route("/mine")
def mine():
    if "user" not in session:
        return redirect(url_for("home"))
    start_mining(session["user"])
    flash("Mining session started")
    return redirect(url_for("wallet"))

@app.route("/send", methods=["POST"])
def send():
    if "user" not in session:
        return redirect(url_for("home"))
    recipient = request.form["recipient"]
    amount = float(request.form["amount"])
    send_orbit(session["user"], recipient, amount)
    return redirect(url_for("wallet"))

@app.route("/logout")
def do_logout():
    web_logout(session.get("user"))
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True, port=10000)
