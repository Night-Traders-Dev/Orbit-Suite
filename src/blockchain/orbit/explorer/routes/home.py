@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    if query:
        return search_chain(query)

    page = int(request.args.get("page", 1))
    chain = load_chain()
    total_pages = max(1, math.ceil(len(chain) / PAGE_SIZE))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    blocks = chain[::-1][start:end]
    summary = get_chain_summary()

    return render_template("home.html",
                           chain=chain,
                           query=query,
                           page=page,
                           total_pages=total_pages,
                           blocks=blocks,
                           summary=summary)
