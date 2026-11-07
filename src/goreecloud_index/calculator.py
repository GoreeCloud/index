"""Sandboxed arithmetic and offline unit conversions. No eval or network I/O."""

from __future__ import annotations

import ast
import math
import operator
import re
from decimal import Decimal, InvalidOperation

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_UNITS = {
    "mm": ("length", 0.001), "cm": ("length", 0.01),
    "m": ("length", 1.0), "km": ("length", 1000.0),
    "in": ("length", 0.0254), "ft": ("length", 0.3048),
    "yd": ("length", 0.9144), "mi": ("length", 1609.344),
    "g": ("mass", 0.001), "kg": ("mass", 1.0),
    "lb": ("mass", 0.45359237), "oz": ("mass", 0.028349523125),
    "b": ("data", 1.0), "kb": ("data", 1000.0),
    "mb": ("data", 1000000.0), "gb": ("data", 1000000000.0),
    "kib": ("data", 1024.0), "mib": ("data", 1048576.0),
    "gib": ("data", 1073741824.0),
    "s": ("duration", 1.0), "min": ("duration", 60.0),
    "h": ("duration", 3600.0), "day": ("duration", 86400.0),
}


def _arithmetic(expression: str) -> float:
    if len(expression) > 128:
        raise ValueError("Expression too long")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid expression") from exc

    def walk(node: ast.AST, depth: int = 0) -> float:
        if depth > 20:
            raise ValueError("Expression too complex")
        if isinstance(node, ast.Expression):
            return walk(node.body, depth + 1)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 1e12:
                raise ValueError("Number too large")
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](walk(node.operand, depth + 1))
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left = walk(node.left, depth + 1)
            right = walk(node.right, depth + 1)
            if type(node.op) is ast.Pow and (abs(right) > 12 or abs(left) > 1e6):
                raise ValueError("Exponent outside safe range")
            try:
                result = _OPS[type(node.op)](left, right)
            except (ArithmeticError, OverflowError) as exc:
                raise ValueError("Invalid arithmetic operation") from exc
            if not math.isfinite(result) or abs(result) > 1e15:
                raise ValueError("Result too large")
            return result
        raise ValueError("Unsupported expression")

    return walk(tree)


def _format(value: float) -> str:
    return f"{value:.12g}"


def calculate(expression: str) -> str | None:
    """Return numeric result or None for ordinary non-calculator search queries."""
    raw = expression.strip()
    if not raw or len(raw) > 128:
        return None
    percent = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*%\s+of\s+([+-]?\d+(?:\.\d+)?)", raw, re.I)
    if percent:
        return _format(float(percent[1]) * float(percent[2]) / 100)

    units = re.fullmatch(
        r"([+-]?\d+(?:\.\d+)?)\s*([a-zA-Z]+)\s+(?:to|in)\s+([a-zA-Z]+)",
        raw, re.I,
    )
    if units:
        amount, from_unit, to_unit = float(units[1]), units[2].lower(), units[3].lower()
        if from_unit in {"c", "f", "k"} and to_unit in {"c", "f", "k"}:
            kelvin = {"c": lambda x: x + 273.15, "f": lambda x: (x - 32) * 5 / 9 + 273.15,
                      "k": lambda x: x}[from_unit](amount)
            final = {"c": kelvin - 273.15, "f": (kelvin - 273.15) * 9 / 5 + 32,
                     "k": kelvin}[to_unit]
            return _format(final) + " " + units[3]
        a, b = _UNITS.get(from_unit), _UNITS.get(to_unit)
        if a and b and a[0] == b[0]:
            return _format(amount * a[1] / b[1]) + " " + units[3]
        return None
    if not re.fullmatch(r"[0-9.\s()+*/%\-]+", raw) or not re.search(r"[+*/%\-]", raw):
        return None
    try:
        return _format(_arithmetic(raw))
    except (ValueError, ZeroDivisionError):
        return None
