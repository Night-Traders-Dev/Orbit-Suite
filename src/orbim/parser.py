from ast import Contract, Procedure, LetStatement, ReturnStatement, Expr
# Parser
def parse(tokens):
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def expect(kind, value=None):
        nonlocal pos
        token = peek()
        if not token:
            raise SyntaxError("Unexpected end of input")
        if token.kind != kind or (value and token.value != value):
            raise SyntaxError(f"Expected {kind} {value}, got {token.kind} {token.value}")
        pos += 1
        return token

    def parse_contract():
        expect("KEYWORD", "contract")
        name = expect("IDENTIFIER").value
        expect("SYMBOL", "{")
        procs = []
        while peek() and peek().value != "}":
            procs.append(parse_proc())
        expect("SYMBOL", "}")
        return Contract(name, procs)

    def parse_proc():
        expect("KEYWORD", "proc")
        name = expect("IDENTIFIER").value
        expect("SYMBOL", "(")
        params = []
        while peek() and peek().value != ")":
            pname = expect("IDENTIFIER").value
            expect("SYMBOL", ":")
            ptype_tok = expect("KEYWORD")  # now accept KEYWORD for types like int, address
            params.append((pname, ptype_tok.value))
            if peek() and peek().value == ",":
                expect("SYMBOL", ",")
        expect("SYMBOL", ")")
        expect("SYMBOL", ":")
        ret_type_tok = expect("KEYWORD")  # accept KEYWORD return type
        expect("SYMBOL", "{")
        body = []
        while peek() and peek().value != "}":
            if peek().value == "let":
                body.append(parse_let())
            elif peek().value == "return":
                body.append(parse_return())
            else:
                raise SyntaxError(f"Unexpected token in proc body: {peek()}")
        expect("SYMBOL", "}")
        return Procedure(name, params, ret_type_tok.value, body)

    def parse_let():
        expect("KEYWORD", "let")
        name = expect("IDENTIFIER").value
        expect("SYMBOL", "=>")
        expr = parse_expr()
        return LetStatement(name, expr)

    def parse_return():
        expect("KEYWORD", "return")
        return ReturnStatement(parse_expr())

    def parse_expr():
        parts = []
        while peek() and peek().value not in {"\n", "}", "}"}:
            t = peek()
            if t.kind in {"IDENTIFIER", "KEYWORD", "NUMBER"} or t.value in {".", "+", "-", "*", "/", "==", "!="}:
                parts.append(expect(t.kind, t.value).value)
            else:
                break
        return Expr(" ".join(parts))

    return parse_contract()
