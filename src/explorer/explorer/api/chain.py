@app.route("/api/chain")
def api_chain():
    return jsonify(load_chain())
