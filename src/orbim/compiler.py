from parser import parse
from lexer import Token, tokenize

# Sample input
if __name__ == "__main__":
    code = """
    contract Token {
        proc transfer(to: address, amount: int): bool {
            let x => msg.sender.balance
            return true
        }
    }
    """
    tokens = tokenize(code)
    print("TOKENS:")
    for t in tokens:
        print(t)
    print("\nAST:")
    tree = parse(tokens)
    print(tree)
