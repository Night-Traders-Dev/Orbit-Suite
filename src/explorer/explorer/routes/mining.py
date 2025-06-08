@app.route("/mining")
def mining_stats():
    from blockchain.tokenutil import get_dynamic_mining_rate
    from config.configutil import MiningConfig

    # Get dynamic rate and breakdown
    rate, breakdown = get_dynamic_mining_rate()

    # Estimate reward for 1 hour (3600s)
    estimated_reward = round(rate * 3600, 6)

    return render_template("mining.html",
                           rate=rate,
                           breakdown=breakdown,
                           reward=estimated_reward,
                           duration=3600)
