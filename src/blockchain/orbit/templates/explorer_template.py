# explorer_template.py

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Orbit Block Explorer</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f4f4f4; }
        h1 { color: #333; }
        .block, .tx { background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 0 8px rgba(0,0,0,0.1); overflow-x: auto; }
        .tx { margin-left: 20px; }
        code { background: #eee; padding: 2px 4px; border-radius: 4px; }
        input[type="text"] { width: 400px; padding: 8px; margin-right: 10px; }
        button { padding: 8px 12px; }
        nav { margin-bottom: 20px; }
        .pagination a {
            padding: 8px 12px;
            margin: 2px;
            text-decoration: none;
            background: #ddd;
            border-radius: 4px;
            color: #000;
        }
        .pagination a.active {
            font-weight: bold;
            background: #bbb;
        }
    </style>
</head>
<body>
    <h1>Orbit Blockchain Explorer</h1>

    <form method="get" action="/">
        <input type="text" name="q" placeholder="Search by address, hash, or block..." value="{{ query }}"/>
        <button type="submit">Search</button>
    </form>

    <nav>
        <a href="/">Home</a> |
        <a href="/validators">Validator Stats</a> |
        <a href="/api/chain">API: Full Chain</a>
    </nav>

    {% if results %}
        <h2>Search Results for "{{ query }}"</h2>
        {% for match in results %}
        <div class="tx">
            <strong>Block:</strong> <a href="/block/{{ match.block }}">{{ match.block }}</a><br>
            <strong>Sender:</strong> <a href="/address/{{ match.tx.sender }}">{{ match.tx.sender }}</a><br>
            <strong>Recipient:</strong> <a href="/address/{{ match.tx.recipient }}">{{ match.tx.recipient }}</a><br>
            <strong>Amount:</strong> {{ match.tx.amount }} Orbit<br>
            <strong>Note:</strong> {{ match.tx.note }}<br>
            <strong>Timestamp:</strong> {{ match.tx.timestamp | ts }}<br>
            <a href="/tx/{{ match.tx.sender }}-{{ match.tx.recipient }}-{{ match.tx.timestamp }}">View Details</a>
        </div>
        {% endfor %}
    {% else %}
        {% for block in blocks %}
        <div class="block">
            <strong>Block #<a href="/block/{{ block.index }}">{{ block.index }}</a></strong><br>
            <strong>Timestamp:</strong> {{ block.timestamp | ts }}<br>
            <strong>Hash:</strong> <code>{{ block.hash }}</code><br>
            <strong>Validator:</strong> {{ block.validator }}<br>
            <strong>Merkle Root:</strong> <code>{{ block.merkle_root }}</code><br>
            <hr>
            <strong>Transactions:</strong>
            {% for tx in block.transactions %}
                <div class="tx">
                    <strong>From:</strong> <a href="/address/{{ tx.sender }}">{{ tx.sender }}</a><br>
                    <strong>To:</strong> <a href="/address/{{ tx.recipient }}">{{ tx.recipient }}</a><br>
                    <strong>Amount:</strong> {{ tx.amount }} Orbit<br>
                    <strong>Note:</strong> {{ tx.note }}<br>
                    <strong>Timestamp:</strong> {{ tx.timestamp | ts }}<br>
                    <a href="/tx/{{ tx.sender }}-{{ tx.recipient }}-{{ tx.timestamp }}">View Details</a>
                </div>
            {% endfor %}
        </div>
        {% endfor %}

        <div class="pagination">
            {% if page > 1 %}
                <a href="/?page={{ page - 1 }}">Previous</a>
            {% endif %}
            {% for p in range(1, total_pages + 1) %}
                <a href="/?page={{ p }}" class="{{ 'active' if p == page else '' }}">{{ p }}</a>
            {% endfor %}
            {% if page < total_pages %}
                <a href="/?page={{ page + 1 }}">Next</a>
            {% endif %}
        </div>
    {% endif %}
</body>
</html>
'''
