import re
# AST structures
class Contract:
    def __init__(self, name, procs):
        self.name = name
        self.procs = procs
    def __repr__(self):
        return f"Contract({self.name}, {self.procs})"

class Procedure:
    def __init__(self, name, params, return_type, body):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body
    def __repr__(self):
        return f"Proc({self.name}, params={self.params}, returns={self.return_type}, body={self.body})"

class LetStatement:
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr
    def __repr__(self):
        return f"Let({self.name} = {self.expr})"

class ReturnStatement:
    def __init__(self, expr):
        self.expr = expr
    def __repr__(self):
        return f"Return({self.expr})"

class Expr:
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"Expr({self.value})"
