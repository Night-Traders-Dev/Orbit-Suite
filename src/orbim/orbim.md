### Orbim: Language Design Overview

## 1. Philosophy

Simplicity: Inspired by Nim—minimal syntax noise, clear semantics.

Web3-first: Smart contracts are first-class, secure and easy to reason about.

General-purpose: Not just for contracts—can build UIs, bots, off-chain logic.

Compiles to WASM: Interoperable, lightweight, portable.



---

## 2. Core Features

# a. Syntax

Indentation-based blocks (Nim/Python style).

Typed variables but with type inference (let, var, const).

Decorators for contract/environment control (@contract, @view, @event).

Explicit contract entry points.

```nim
contract Token:
  let name = "Orbit"
  var total_supply: int = 0

  func mint(to: address, amount: int):
    total_supply += amount
    emit Transfer(None, to, amount)
```

---

# b. Types

Primitives: int, float, bool, string, address, timestamp

Composite: tuple, array, map, struct

Optional (?T) and Nullable types

Native token and gas units: orbit, gas



---

# c. Execution Model

Deterministic runtime, optimized for WASM.

No recursion or dynamic allocation in contract logic.

Storage/global state through state declarations.


state balances: map[address, int]


---

# d. Web3 Integration

Native support for:

Event emission: emit

Cross-contract calls: contract.call()

Gas introspection and limits

Signatures and hashing

Block context (block.timestamp, msg.sender)




---

# e. Modules & Importing

import math
import orbit/token

Built-in module types: cryptography, math, utils, randomness.



---

# f. Toolchain

Compiler: orbimc (Python-based, emits WASM).

Runtime: orbimvm for simulation/testing.

DevKit: CLI tools, formatter, linter, sandbox.




