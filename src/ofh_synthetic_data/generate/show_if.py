"""Evaluate questionnaire show_if expressions."""

from __future__ import annotations

import re
from collections.abc import Mapping


def evaluate_show_if(expression: object, context: Mapping[str, object]) -> bool:
    """Return whether a show_if expression is satisfied.

    Unsupported expressions default to True so generation does not lose fields because of a
    parser limitation. The unsupported cases should be documented and tightened over time.
    """

    text = _normalise_expression(expression)
    if not text:
        return True

    try:
        return _evaluate_expression(text, context)
    except (IndexError, TypeError, ValueError, re.error):
        return True


def _evaluate_expression(expression: str, context: Mapping[str, object]) -> bool:
    """Evaluate an expression tree with top-level OR before AND."""
    expression = _strip_wrapping_parentheses(expression.strip())

    or_parts = _split_top_level(expression, "OR")
    if len(or_parts) > 1:
        return any(_evaluate_expression(part, context) for part in or_parts)

    and_parts = _split_top_level(expression, "AND")
    if len(and_parts) > 1:
        return all(_evaluate_expression(part, context) for part in and_parts)

    return _evaluate_atom(expression, context)


def _evaluate_atom(atom: str, context: Mapping[str, object]) -> bool:
    """Evaluate one show_if condition against the current row context."""
    atom = _strip_wrapping_parentheses(atom.strip())

    null_match = re.fullmatch(r"\[([^\]]+)\]\s+is\s+NOT\s+NULL", atom, flags=re.IGNORECASE)
    if null_match:
        return not _is_blank(context.get(null_match.group(1)))

    null_match = re.fullmatch(r"\[([^\]]+)\]\s+is\s+NULL", atom, flags=re.IGNORECASE)
    if null_match:
        return _is_blank(context.get(null_match.group(1)))

    one_of_match = re.fullmatch(r"\[([^\]]+)\]\s+ONE\s+of\s+\[(.*)\]", atom, flags=re.IGNORECASE)
    if one_of_match:
        value = context.get(one_of_match.group(1))
        return _matches_any_token(value, _split_list_tokens(one_of_match.group(2)))

    any_of_match = re.fullmatch(r"\[([^\]]+)\]\s+ANY\s+of\s+\[(.*)\]", atom, flags=re.IGNORECASE)
    if any_of_match:
        values = _as_value_list(context.get(any_of_match.group(1)))
        tokens = _split_list_tokens(any_of_match.group(2))
        return any(_matches_any_token(value, tokens) for value in values)

    equality_match = re.fullmatch(r"\[([^\]]+)\]\s*=\s*(.+)", atom, flags=re.IGNORECASE)
    if equality_match:
        value = context.get(equality_match.group(1))
        token = equality_match.group(2).strip()
        if token.upper() == "NULL":
            return _is_blank(value)
        values = _as_value_list(value)
        return any(_matches_token(item, token) for item in values)

    return True


def _normalise_expression(expression: object) -> str:
    """Clean workbook expression text before parsing."""
    text = str(expression or "").strip()
    if text.lower() == "nan":
        return ""

    while text.count(")") > text.count("(") and text.endswith(")"):
        text = text[:-1].strip()

    return text


def _strip_wrapping_parentheses(expression: str) -> str:
    while expression.startswith("(") and expression.endswith(")"):
        inner = expression[1:-1].strip()
        if not _has_balanced_delimiters(inner):
            break
        if _first_top_level_close(expression) != len(expression) - 1:
            break
        expression = inner
    return expression


def _split_top_level(expression: str, operator: str) -> list[str]:
    """Split on an operator only when outside parentheses and brackets."""
    parts: list[str] = []
    start = 0
    index = 0
    paren_depth = 0
    bracket_depth = 0
    needle = f" {operator} "

    while index < len(expression):
        character = expression[index]
        if character == "(" and bracket_depth == 0:
            paren_depth += 1
        elif character == ")" and bracket_depth == 0:
            paren_depth = max(0, paren_depth - 1)
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth = max(0, bracket_depth - 1)

        if (
            paren_depth == 0
            and bracket_depth == 0
            and expression[index : index + len(needle)] == needle
        ):
            parts.append(expression[start:index].strip())
            start = index + len(needle)
            index = start
            continue

        index += 1

    if parts:
        parts.append(expression[start:].strip())
    return parts


def _split_list_tokens(content: str) -> list[str]:
    """Split list expressions while preserving nested int(...) predicates."""
    tokens: list[str] = []
    start = 0
    paren_depth = 0

    for index, character in enumerate(content):
        if character == "(":
            paren_depth += 1
        elif character == ")":
            paren_depth = max(0, paren_depth - 1)
        elif character == "," and paren_depth == 0:
            tokens.append(content[start:index].strip())
            start = index + 1

    tokens.append(content[start:].strip())
    return [token for token in tokens if token]


def _matches_any_token(value: object, tokens: list[str]) -> bool:
    if _is_blank(value):
        return False
    return any(_matches_token(value, token) for token in tokens)


def _matches_token(value: object, token: str) -> bool:
    token = token.strip()
    if token.lower().startswith("int(") and token.endswith(")"):
        return _matches_int_expression(value, token[4:-1])
    return _normalise_value(value) == _normalise_value(token)


def _matches_int_expression(value: object, expression: str) -> bool:
    """Match a numeric value against an int(...) comparison expression."""
    numeric = _to_float(value)
    if numeric is None:
        return False

    comparisons = [part.strip() for part in expression.split("&")]
    for comparison in comparisons:
        match = re.fullmatch(r"(>=|<=|>|<|=)\s*(-?\d+(?:\.\d+)?)", comparison)
        if not match:
            return False

        operator, expected_text = match.groups()
        expected = float(expected_text)
        if operator == ">=" and not numeric >= expected:
            return False
        if operator == "<=" and not numeric <= expected:
            return False
        if operator == ">" and not numeric > expected:
            return False
        if operator == "<" and not numeric < expected:
            return False
        if operator == "=" and numeric != expected:
            return False

    return True


def _as_value_list(value: object) -> list[object]:
    """Represent scalar and bracketed multi-select values as a list."""
    if _is_blank(value):
        return []

    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        return [item.strip() for item in text[1:-1].split(",") if item.strip()]

    return [value]


def _normalise_value(value: object) -> str:
    text = str(value).strip()
    numeric = _to_float(text)
    if numeric is not None and numeric.is_integer():
        return str(int(numeric))
    return text


def _to_float(value: object) -> float | None:
    if _is_blank(value):
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text.lower() == "nan"


def _has_balanced_delimiters(expression: str) -> bool:
    paren_depth = 0
    bracket_depth = 0
    for character in expression:
        if character == "(" and bracket_depth == 0:
            paren_depth += 1
        elif character == ")" and bracket_depth == 0:
            paren_depth -= 1
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth -= 1
        if paren_depth < 0 or bracket_depth < 0:
            return False
    return paren_depth == 0 and bracket_depth == 0


def _first_top_level_close(expression: str) -> int | None:
    paren_depth = 0
    bracket_depth = 0
    for index, character in enumerate(expression):
        if character == "(" and bracket_depth == 0:
            paren_depth += 1
        elif character == ")" and bracket_depth == 0:
            paren_depth -= 1
            if paren_depth == 0:
                return index
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth -= 1
    return None
