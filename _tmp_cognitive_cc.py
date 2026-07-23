"""Approximate Sonar-style cognitive complexity for Python functions.

Scoring (aligned with Sonar Cognitive Complexity / G. Ann Campbell):
- +1 for if / for / while / except / with / assert / match case / ternary
- +1 nesting increment for nested structural nodes above
- +1 for each boolean sequence break (and/or chains)
- elif adds +1 (does not increase nesting beyond the if nest)
- else does not add +1
- nested function definitions reset nesting for their body
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


class _CC(ast.NodeVisitor):
    def __init__(self) -> None:
        self.score = 0
        self._nest = 0

    def _bump(self, amount: int = 1) -> None:
        self.score += amount + self._nest

    def _visit_body(self, nodes: list[ast.stmt]) -> None:
        for n in nodes:
            self.visit(n)

    def visit_If(self, node: ast.If) -> None:
        # count if / elif chain
        self._bump()
        self.visit(node.test)
        self._nest += 1
        self._visit_body(node.body)
        self._nest -= 1
        orelse = node.orelse
        while len(orelse) == 1 and isinstance(orelse[0], ast.If):
            # elif
            elif_node = orelse[0]
            self.score += 1  # elif +1, no extra nest from keyword
            self.visit(elif_node.test)
            self._nest += 1
            self._visit_body(elif_node.body)
            self._nest -= 1
            orelse = elif_node.orelse
        if orelse:
            # else: no +1
            self._nest += 1
            self._visit_body(orelse)
            self._nest -= 1

    def visit_For(self, node: ast.For) -> None:
        self._bump()
        self.visit(node.target)
        self.visit(node.iter)
        self._nest += 1
        self._visit_body(node.body)
        self._nest -= 1
        if node.orelse:
            self._nest += 1
            self._visit_body(node.orelse)
            self._nest -= 1

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit_For(node)  # type: ignore[arg-type]

    def visit_While(self, node: ast.While) -> None:
        self._bump()
        self.visit(node.test)
        self._nest += 1
        self._visit_body(node.body)
        self._nest -= 1
        if node.orelse:
            self._nest += 1
            self._visit_body(node.orelse)
            self._nest -= 1

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._bump()
        self._nest += 1
        self._visit_body(node.body)
        self._nest -= 1

    def visit_With(self, node: ast.With) -> None:
        self._bump()
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self.visit(item.optional_vars)
        self._nest += 1
        self._visit_body(node.body)
        self._nest -= 1

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.visit_With(node)  # type: ignore[arg-type]

    def visit_Assert(self, node: ast.Assert) -> None:
        self._bump()
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._bump()
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self._bump()
        self._nest += 1
        self.visit(node.target)
        self.visit(node.iter)
        for iff in node.ifs:
            self._bump()
            self.visit(iff)
        self._nest -= 1

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # +1 for the whole boolean sequence
        self.score += 1
        for v in node.values:
            self.visit(v)

    def visit_Match(self, node: ast.Match) -> None:
        self.visit(node.subject)
        for case in node.cases:
            self._bump()
            self._nest += 1
            if case.guard is not None:
                self.score += 1
                self.visit(case.guard)
            self._visit_body(case.body)
            self._nest -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # nested function: analyze independently (caller handles top-level)
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


def function_cc(node: ast.AST) -> int:
    visitor = _CC()
    # visit defaults/decorators? only body for Sonar-like function complexity
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for n in node.body:
            visitor.visit(n)
    return visitor.score


def scan_file(path: Path, threshold: int = 15) -> list[tuple[int, int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rows: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            score = function_cc(node)
            if score > threshold:
                rows.append((score, node.lineno, node.name))
    rows.sort(reverse=True)
    return rows


def main(argv: list[str]) -> int:
    threshold = 15
    paths = [Path(a) for a in argv if not a.startswith("-")]
    if not paths:
        return 1
    total = 0
    for path in paths:
        if not path.exists():
            print(f"MISSING {path}")
            continue
        if path.is_dir():
            files = sorted(path.rglob("*.py"))
        else:
            files = [path]
        for f in files:
            if "__pycache__" in f.parts:
                continue
            try:
                rows = scan_file(f, threshold=threshold)
            except SyntaxError as exc:
                print(f"SYNTAX {f}: {exc}")
                continue
            if not rows:
                continue
            print(f"== {f}")
            for score, line, name in rows:
                print(f"  CC={score:3d}  L{line}  {name}")
                total += 1
    print(f"TOTAL_OVER_THRESHOLD={total}")
    return 0 if total == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
