@app.route("/api/summary")
def api_summary():
    return jsonify(get_chain_summary())
