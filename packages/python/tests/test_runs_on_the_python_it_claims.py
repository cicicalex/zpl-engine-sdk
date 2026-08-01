"""The package must import on the oldest Python it advertises.

AUDIT 2026-08-01. ``pyproject.toml`` declares ``requires-python = ">=3.9"`` and
carries a ``Programming Language :: Python :: 3.9`` classifier, and ``setup.py``
repeats ``python_requires=">=3.9"``. Four modules — client, exceptions, models,
utils — used PEP 604 unions (``BiasLevel | None``) with no
``from __future__ import annotations``.

Those annotations are evaluated at definition time before 3.10, so on 3.9 the
import raises ``TypeError: unsupported operand type(s) for |``. Not a runtime
edge case: it fires on ``import zeropointlogic``, so the package is unusable on
a version PyPI is being told it supports.

Measured with ``ast`` before fixing: 27 unions, every one in annotation
position, none in a type alias or a call. So the floor was salvageable —
lazy annotations keep 3.9 working — rather than something that had to be
narrowed to ``>=3.10``.

This cannot be caught by running the suite, because the suite runs on whatever
interpreter is installed, and here that is well past 3.10. It has to be a
structural check.

The rule: either every module using PEP 604 defers its annotations, or the
declared floor is 3.10 and up. Both are correct; disagreeing with yourself is
not, and a published ``requires-python`` cannot be edited.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = PKG_ROOT / "zeropointlogic"


def declared_python_floor() -> tuple[int, int]:
    """The (major, minor) floor from pyproject's requires-python."""
    text = (PKG_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'requires-python\s*=\s*"[^0-9]*(\d+)\.(\d+)', text)
    assert m, "pyproject.toml declares no requires-python floor"
    return int(m.group(1)), int(m.group(2))


def _is_typeish(node: ast.AST) -> bool:
    """A `|` operand that could be a type rather than an integer."""
    return isinstance(node, (ast.Name, ast.Subscript, ast.Attribute)) or (
        isinstance(node, ast.Constant) and node.value is None
    )


def modules_using_pep604() -> dict[str, list[int]]:
    """Module name -> line numbers of `X | Y` unions that look like types.

    Numeric bit-or is legal on every version, so operands that cannot be types
    are skipped; otherwise an ordinary `flags | MASK` would be reported as a
    version problem.
    """
    found: dict[str, list[int]] = {}
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        lines = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.BitOr)
            and _is_typeish(node.left)
            and _is_typeish(node.right)
        ]
        if lines:
            found[path.name] = sorted(lines)
    return found


def defers_annotations(module: str) -> bool:
    tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


class TestRunsOnThePythonItClaims(unittest.TestCase):
    def test_modules_were_actually_scanned(self):
        # A scan that finds nothing would make every assertion below vacuous.
        self.assertGreaterEqual(
            len(list(PACKAGE.glob("*.py"))),
            4,
            "fewer than four modules found — the package layout changed and this guard "
            "would pass over almost nothing",
        )

    def test_pep604_unions_are_deferred_or_the_floor_is_310(self):
        major, minor = declared_python_floor()
        if (major, minor) >= (3, 10):
            return  # unions are native from 3.10; nothing to defer

        offenders = {
            module: lines
            for module, lines in modules_using_pep604().items()
            if not defers_annotations(module)
        }

        self.assertEqual(
            offenders,
            {},
            f"pyproject declares requires-python >= {major}.{minor}, but these modules use "
            f"PEP 604 unions without `from __future__ import annotations`: "
            f"{ {m: ls[:5] for m, ls in offenders.items()} }. On {major}.{minor} the "
            f"annotation is evaluated at definition time and `import zeropointlogic` raises "
            f"TypeError, so the package cannot be imported at all on a version PyPI is being "
            f"told it supports. Add the future import, or raise the floor to 3.10 and drop the "
            f"older classifiers.",
        )

    def test_setup_py_and_pyproject_agree_on_the_floor(self):
        # Two files declare the floor and only one of them is read by modern
        # tooling, so they can disagree silently until someone builds with the
        # other.
        setup_py = PKG_ROOT / "setup.py"
        if not setup_py.exists():
            return
        text = setup_py.read_text(encoding="utf-8")
        m = re.search(r'python_requires\s*=\s*"[^0-9]*(\d+)\.(\d+)', text)
        if not m:
            return
        self.assertEqual(
            (int(m.group(1)), int(m.group(2))),
            declared_python_floor(),
            "setup.py and pyproject.toml declare different minimum Python versions",
        )

    def test_classifiers_do_not_advertise_below_the_floor(self):
        text = (PKG_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        major, minor = declared_python_floor()
        advertised = [
            (int(a), int(b))
            for a, b in re.findall(r"Programming Language :: Python :: (\d+)\.(\d+)", text)
        ]
        below = [f"{a}.{b}" for a, b in advertised if (a, b) < (major, minor)]
        self.assertEqual(
            below,
            [],
            f"classifiers advertise Python {below} while requires-python is >= {major}.{minor}. "
            f"PyPI renders the classifiers on the project page; installers read requires-python. "
            f"Neither can be edited after upload.",
        )


if __name__ == "__main__":
    unittest.main()
