"""
tools/calculator.py

Calculator Tool for LangChain Agent
"""

from __future__ import annotations

import ast
import operator as op
from langchain_core.tools import tool

# 허용되는 연산자
_ALLOWED = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
}


def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Num):  # Python <3.8 호환
        return node.n

    if isinstance(node, ast.BinOp):
        return _ALLOWED[type(node.op)](
            _eval(node.left),
            _eval(node.right),
        )

    if isinstance(node, ast.UnaryOp):
        return _ALLOWED[type(node.op)](
            _eval(node.operand),
        )

    raise TypeError("지원하지 않는 수식입니다.")


def calculate(expression: str):
    """
    Safely evaluate a mathematical expression.
    """
    tree = ast.parse(expression, mode="eval")
    return _eval(tree.body)


@tool
def calculator(expression: str) -> str:
    """
    수학 계산을 수행합니다.

    Examples
    --------
    calculator("100+200")
    calculator("1500000/1.1")
    calculator("(30*12)+100")
    """
    try:
        result = calculate(expression)
        return f"계산 결과 : {result}"
    except Exception as e:
        return f"계산 오류 : {e}"


if __name__ == "__main__":
    print(calculator.invoke({"expression": "100+250*3"}))
    print(calculator.invoke({"expression": "(1500000/1.1)"}))
