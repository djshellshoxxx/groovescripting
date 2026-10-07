"""Safe event predicate grammar shared by groovdebug and groovtest.

Grammar (no eval, attribute access, indexing or calls):
    expr    := or
    or      := and ("or" and)*
    and     := unary ("and" unary)*
    unary   := "not" unary | "(" expr ")" | compare
    compare := FIELD OP VALUE
    OP      := == != < <= > >=
    VALUE   := number | "string" | 'string' | true | false
"""

import math
import re

FIELDS = {
    "track": str,
    "voice": str,
    "instrument": str,
    "section": str,
    "origin": str,
    "event_id": str,
    "bar": float,
    "beat": float,
    "note": float,
    "velocity": float,
    "probability": float,
    "duration": float,
    "frame": float,
    "accepted": bool,
    "accent": bool,
}
TOKEN = re.compile(
    r"\s*(?:(?P<num>-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)|(?P<str>\"[^\"]*\"|'[^']*')"
    r"|(?P<op>==|!=|<=|>=|<|>)|(?P<paren>[()])|(?P<word>[A-Za-z_][A-Za-z0-9_]*))"
)


class ExpressionError(ValueError):
    pass


def _tokens(text):
    position = 0
    out = []
    while position < len(text):
        if text[position:].strip() == "":
            break
        match = TOKEN.match(text, position)
        if not match or match.end() == position:
            raise ExpressionError(f"unexpected character at column {position + 1}: {text[position]!r}")
        kind = match.lastgroup
        start = match.start(kind)
        out.append((kind, match.group(kind), start + 1))
        position = match.end()
    return out


def field_values(record, field):
    """Return every value a record exposes for a field (notes may be several)."""
    if field == "note":
        return [float(n) for n in record.get("notes", []) if not isinstance(n, dict)]
    if field == "section":
        return [record["source"]["section"]]
    if field == "origin":
        return [record["source"]["origin"]]
    if field == "frame":
        frame = record["timing"]["frame"]
        return [] if frame is None else [float(frame)]
    value = record.get(field)
    return [] if value is None else [value]


def compile_expression(text):
    """Parse an expression into a predicate(record) -> bool. Errors name the column."""
    if not isinstance(text, str) or not text.strip():
        raise ExpressionError("expression must be a nonempty string")
    tokens = _tokens(text)
    index = 0

    def peek():
        return tokens[index] if index < len(tokens) else (None, None, len(text) + 1)

    def take(kind=None, value=None):
        nonlocal index
        token = peek()
        if token[0] is None or (kind and token[0] != kind) or (value and token[1] != value):
            want = value or kind or "token"
            raise ExpressionError(f"expected {want} at column {token[2]}")
        index += 1
        return token

    def literal():
        kind, value, column = take()
        if kind == "num":
            number = float(value)
            if not math.isfinite(number):
                raise ExpressionError(f"number must be finite at column {column}")
            return number
        if kind == "str":
            return value[1:-1]
        if kind == "word" and value in ("true", "false"):
            return value == "true"
        raise ExpressionError(f"expected a literal value at column {column}")

    def compare():
        _, name, column = take("word")
        if name not in FIELDS:
            raise ExpressionError(f"unknown field {name!r} at column {column}; allowed: {', '.join(FIELDS)}")
        _, op, op_column = take("op")
        value = literal()
        expected = FIELDS[name]
        if expected is bool and not isinstance(value, bool):
            raise ExpressionError(f"{name} compares with true or false (column {op_column})")
        if expected is str and not isinstance(value, str):
            raise ExpressionError(f"{name} compares with a quoted string (column {op_column})")
        if expected is float and (isinstance(value, (bool, str))):
            raise ExpressionError(f"{name} compares with a number (column {op_column})")
        if expected is not float and op not in ("==", "!="):
            raise ExpressionError(f"{name} supports only == and != (column {op_column})")
        ops = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
        }[op]
        if op == "!=":
            return lambda r: not any(v == value for v in field_values(r, name))
        return lambda r: any(ops(v, value) for v in field_values(r, name))

    def unary():
        kind, value, _ = peek()
        if kind == "word" and value == "not":
            take()
            inner = unary()
            return lambda r: not inner(r)
        if kind == "paren" and value == "(":
            take()
            inner = disjunction()
            take("paren", ")")
            return inner
        return compare()

    def conjunction():
        parts = [unary()]
        while peek()[0] == "word" and peek()[1] == "and":
            take()
            parts.append(unary())
        return parts[0] if len(parts) == 1 else lambda r: all(p(r) for p in parts)

    def disjunction():
        parts = [conjunction()]
        while peek()[0] == "word" and peek()[1] == "or":
            take()
            parts.append(conjunction())
        return parts[0] if len(parts) == 1 else lambda r: any(p(r) for p in parts)

    predicate = disjunction()
    if index != len(tokens):
        raise ExpressionError(f"unexpected {tokens[index][1]!r} at column {tokens[index][2]}")
    return predicate
