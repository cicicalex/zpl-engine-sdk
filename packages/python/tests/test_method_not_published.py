"""The method stays unpublished.

This package is on PyPI as ``zeropointlogic``. Its source, its README and its
project description are world-readable the moment it is published, and a
release cannot be edited afterwards - a version that ships with the derivation
in it stays downloadable forever.

AUDIT 2026-07-31: the website gained this rule today, and the first version of
it there used a scanner that skipped comment lines. Writing the derivation into
a comment sailed straight past. A comment ships exactly like the code around
it, and it is the likeliest place for something to be parked "just for now", so
nothing is skipped here.

Scanned at the time of writing: nothing in this package, the MCP, the CLI or
the TypeScript SDK carried it. This exists so that stays true rather than being
rechecked by hand.

The package directory only - this file states the patterns it forbids, and a
guard that flags its own documentation is a guard someone deletes.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "zeropointlogic"

# The derivation, in the spellings someone would actually write: code, prose,
# and the unicode multiplication sign a copy-paste from a document brings in.
DERIVATION = re.compile(
    r"1\s*-\s*(?:math\.)?abs\s*\(?\s*2\s*[*×⋅]?\s*[*]?\s*p"
    r"|1\s*-\s*\|\s*2\s*[*×⋅]?\s*p",
    re.IGNORECASE,
)


def _python_files():
    return sorted(PKG.rglob("*.py"))


class TestMethodNotPublished:
    def test_the_package_is_actually_being_read(self):
        files = _python_files()
        assert len(files) > 3, f"only {len(files)} files under {PKG} - this would pass vacuously"

    def test_no_source_file_carries_the_derivation(self):
        offenders = []
        for path in _python_files():
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if DERIVATION.search(line):
                    offenders.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()[:100]}")
        assert offenders == [], (
            "the method must not ship inside a published package:\n" + "\n".join(offenders)
        )

    def test_no_published_surface_carries_it_either(self):
        offenders = []
        scanned = 0
        for name in ("README.md", "pyproject.toml", "setup.py"):
            path = ROOT / name
            if not path.exists():
                continue
            scanned += 1
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if DERIVATION.search(line):
                    offenders.append(f"{name}:{i}: {line.strip()[:100]}")
        assert scanned > 0, "no published files were read - this would pass vacuously"
        assert offenders == [], (
            "PyPI renders these; the method must not be in them:\n" + "\n".join(offenders)
        )

    def test_the_pattern_catches_how_it_would_really_be_written(self):
        assert DERIVATION.search("    # ain = 1 - abs(2 * p_output - 1)"), "comment"
        assert DERIVATION.search("ain = 1 - math.abs(2 * p - 1)"), "code"
        assert DERIVATION.search("ain = 1 - |2p - 1|"), "prose"
        assert DERIVATION.search("AIN = 1 - abs(2 × p_output - 1)"), "pasted from a document"

    def test_the_pattern_leaves_ordinary_arithmetic_alone(self):
        assert not DERIVATION.search("remaining = 1 - used / total")
        assert not DERIVATION.search("pct = 1 - ratio")
        assert not DERIVATION.search(
            "p_output is the balance the engine measured; 0.500 is equilibrium"
        ), "describing the field is allowed - that is documented on purpose"
        assert not DERIVATION.search(
            "ain is symmetric about equilibrium and cannot express direction"
        ), "stating the behaviour is allowed; stating the expression is not"
