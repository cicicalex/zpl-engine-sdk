"""Where the other ZPL repos are, and what to do when they are not there.

AUDIT 2026-08-02. Two tests here read source out of the engine to check that
this package agrees with it. Both located it through an absolute path on one
developer's machine, and one of them turned a missing file into an early
``return`` — which pytest counts as a pass.

Measured on the sibling MCP repo, which had the same shape: the engine's
``ain.rs`` was moved aside and the suite reported 6 passed, 0 skipped, exit 0.
The check that the bands match the engine had not read anything.

Two things wrong, both fixed here.

The path is no longer a machine's. It comes from an environment variable if one
is set, otherwise from the repos' usual layout relative to this one. An absolute
path in a public repo also published the private repos' names.

And absence is visible: a caller that cannot find the engine calls
``pytest.skip`` with a reason naming the variable that would make it run, so a
reader knows what to do rather than assuming the test is broken.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# tests/ -> python/ -> packages/ -> repo root -> the directory repos live in
_REPO = Path(__file__).resolve().parents[3]
_NEIGHBOURS = _REPO.parent

ROOTS = {
    "engine": Path(os.environ.get("ZPL_ENGINE_SOURCE")
                   or _NEIGHBOURS.parent / "zpl-engine-source"),
    "clients": Path(os.environ.get("ZPL_CLIENTS_ROOT") or _NEIGHBOURS),
}

_VARS = {"engine": "ZPL_ENGINE_SOURCE", "clients": "ZPL_CLIENTS_ROOT"}


def sibling(which: str, *parts: str) -> Path:
    """A path inside one of the sibling repos."""
    if which not in ROOTS:
        raise KeyError("unknown sibling repo: %s" % which)
    return ROOTS[which].joinpath(*parts)


def read_sibling(which: str, *parts: str) -> str | None:
    """The file's text, or ``None`` when the repo is not available."""
    path = sibling(which, *parts)
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def why_skipped(which: str, *parts: str) -> str:
    """The sentence a skipped cross-repo check prints."""
    return (
        "%s repo not available at %s - this check compares this package against "
        "it and cannot run. Set %s to where it is checked out."
        % (which, sibling(which, *parts), _VARS[which])
    )


def require_sibling(which: str, *parts: str) -> str:
    """Read it, or skip the test visibly. Never returns ``None``."""
    text = read_sibling(which, *parts)
    if text is None:
        pytest.skip(why_skipped(which, *parts))
    return text
