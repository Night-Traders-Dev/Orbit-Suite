@app.route("/api/docs")
def api_docs():
    return render_template("api_docs.html")
