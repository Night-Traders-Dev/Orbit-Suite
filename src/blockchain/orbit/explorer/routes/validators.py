@app.route("/validators")
def validators():
    stats = get_validator_stats()
    return render_template("validators.html", validator_data=stats)
