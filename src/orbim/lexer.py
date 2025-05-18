# Directory layout suggestion:
# orbim/
#   __init__.py
#   lexer.py         # handles tokenization
#   parser.py        # handles AST parsing
#   ast.py           # defines AST classes
#   compiler.py      # ties everything together (entry point)

# === lexer.py ===
import re

KEYWORDS = {
    "contract", "proc", "let", "var", "return", "if", "else",
    "true", "false", "int", "bool", "address", "msg", "block"
}
SYMBOLS = {"{", "}", "(", ")", ":", ",", ".", "=", "=>", "+", "-", "*", "/", "==", "!="}

class Token:
    def __init__(self, kind, value, line):
        self.kind = kind
        self.value = value
        self.line = line
    def __repr__(self):
        return f"<{self.kind.upper()}: {self.value}>"

def tokenize(code):
    tokens, lineno, i = [], 1, 0
    while i < len(code):
        ch = code[i]
        if ch in " \t\r": i += 1
        elif ch == "\n": lineno += 1; i += 1
        elif ch == "#":
            while i < len(code) and code[i] != "\n": i += 1
        elif ch.isalpha() or ch == "_":
            start = i
            while i < len(code) and (code[i].isalnum() or code[i] == "_"): i += 1
            word = code[start:i]
            kind = "KEYWORD" if word in KEYWORDS else "IDENTIFIER"
            tokens.append(Token(kind, word, lineno))
        elif ch.isdigit():
            start = i
            while i < len(code) and code[i].isdigit(): i += 1
            tokens.append(Token("NUMBER", code[start:i], lineno))
        elif code[i:i+2] in SYMBOLS:
            tokens.append(Token("SYMBOL", code[i:i+2], lineno))
            i += 2
        elif ch in SYMBOLS:
            tokens.append(Token("SYMBOL", ch, lineno))
            i += 1
        else:
            raise SyntaxError(f"Unexpected character {ch} on line {lineno}")
    return tokens
