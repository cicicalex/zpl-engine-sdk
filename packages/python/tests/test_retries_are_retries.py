"""`max_retries` must count retries, and a request must always be attempted.

AUDIT 2026-08-02. Both Python clients looped over ``range(self.max_retries)``,
which makes the parameter a count of ATTEMPTS while its own name, its
docstring and the TypeScript client all say RETRIES. Measured with a counting
transport, no network and no engine involved:

    max_retries=0  ->  0 requests sent. The function fell off the end of the
                       loop and returned None, and the caller received
                       "AttributeError: 'NoneType' object has no attribute
                       'get'" from the result parser. Someone who asked for no
                       retries got a client that never contacted the engine.

    max_retries=3  ->  3 attempts, where TypeScript makes 4 from the same
                       number. One customer's configuration, two behaviours,
                       depending on which SDK they picked.

Re-measured after the fix: 1 and 4.

These are behavioural. The transport is a stand-in that counts calls; the
retry loop, the client and the parameter are all real. Nothing here reads the
source, so no comment in it can answer for the code.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from zeropointlogic.client import AsyncZPLClient, ZPLClient
from zeropointlogic.exceptions import ZPLNetworkError

KEY = "zpl_u_" + "a" * 48
MATRIX = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]

ANALYZE_BODY = {
    "n": 3,
    "families": [],
    "ones": 0,
    "unanimous": True,
    "input_ones": 0,
    "cells": 9,
    "degenerate": False,
}


class _Response:
    status_code = 200
    headers = {"Content-Type": "application/json"}
    text = "{}"

    def json(self):
        return dict(ANALYZE_BODY)


class _Exceptions:
    Timeout = TimeoutError
    ConnectionError = ConnectionError
    RequestException = OSError


class CountingTransport:
    """Stands in for ``requests``. Counts what actually leaves the client."""

    exceptions = _Exceptions

    def __init__(self, fail: bool = False):
        self.calls = 0
        self.fail = fail

    def _hit(self):
        self.calls += 1
        if self.fail:
            raise ConnectionError("refused")
        return _Response()

    def get(self, *_a, **_k):
        return self._hit()

    def post(self, *_a, **_k):
        return self._hit()


class _AsyncHttpxErrors:
    """The httpx attributes the async client catches on."""

    TimeoutException = TimeoutError
    ConnectError = ConnectionError
    HTTPError = OSError


class CountingAsyncTransport:
    def __init__(self, fail: bool = False):
        self.calls = 0
        self.fail = fail

    async def _hit(self):
        self.calls += 1
        if self.fail:
            raise ConnectionError("refused")
        return _Response()

    async def get(self, *_a, **_k):
        return await self._hit()

    async def post(self, *_a, **_k):
        return await self._hit()


def sync_client(max_retries: int, fail: bool = False):
    client = ZPLClient(api_key=KEY, max_retries=max_retries, backoff_factor=0)
    transport = CountingTransport(fail=fail)
    client._requests = transport
    return client, transport


def async_client(max_retries: int, fail: bool = False):
    client = AsyncZPLClient(api_key=KEY, max_retries=max_retries, backoff_factor=0)
    transport = CountingAsyncTransport(fail=fail)
    client._httpx = _AsyncHttpxErrors
    client._client = transport

    async def _ready():
        return transport

    client._ensure_client = _ready
    return client, transport


# ── No retries still means one try ────────────────────────────────────────


def test_no_retries_still_sends_the_request():
    client, transport = sync_client(0)
    result = client.analyze(MATRIX)
    assert transport.calls == 1, (
        f"max_retries=0 sent {transport.calls} requests. Asking for no retries "
        f"must not mean asking for no request."
    )
    assert result is not None, "the client returned nothing rather than a result"


def test_no_retries_still_sends_the_request_async():
    client, transport = async_client(0)
    result = asyncio.run(client.analyze(MATRIX))
    assert transport.calls == 1, f"max_retries=0 sent {transport.calls} requests (async)"
    assert result is not None


def test_a_negative_setting_cannot_empty_the_loop():
    # Not a supported value, but it must not resurrect the silent None.
    client, transport = sync_client(-5)
    client.analyze(MATRIX)
    assert transport.calls == 1


def test_the_client_never_returns_none():
    # The shape the defect took: no exception, no request, and None handed to
    # the parser. Whatever else changes, a call must end in a result or an
    # error - never in nothing.
    for retries in (0, 1, 3):
        client, _ = sync_client(retries)
        assert client.analyze(MATRIX) is not None, f"None returned at max_retries={retries}"


# ── Retries are retries ───────────────────────────────────────────────────


@pytest.mark.parametrize("retries,expected", [(0, 1), (1, 2), (2, 3), (3, 4)])
def test_attempts_are_one_more_than_retries(retries, expected):
    client, transport = sync_client(retries, fail=True)
    with pytest.raises(ZPLNetworkError):
        client.analyze(MATRIX)
    assert transport.calls == expected, (
        f"max_retries={retries} produced {transport.calls} attempts, not {expected}. "
        f"A retry is an attempt after the first one."
    )


@pytest.mark.parametrize("retries,expected", [(0, 1), (2, 3), (3, 4)])
def test_attempts_are_one_more_than_retries_async(retries, expected):
    client, transport = async_client(retries, fail=True)
    with pytest.raises(ZPLNetworkError):
        asyncio.run(client.analyze(MATRIX))
    assert transport.calls == expected, (
        f"max_retries={retries} produced {transport.calls} attempts (async), not {expected}"
    )


def test_both_python_clients_agree():
    # They are separate implementations of the same parameter. Drift between
    # them is invisible to anyone who only uses one.
    sync_c, sync_t = sync_client(2, fail=True)
    with pytest.raises(ZPLNetworkError):
        sync_c.analyze(MATRIX)
    async_c, async_t = async_client(2, fail=True)
    with pytest.raises(ZPLNetworkError):
        asyncio.run(async_c.analyze(MATRIX))
    assert sync_t.calls == async_t.calls, (
        f"the sync client tried {sync_t.calls} times and the async one "
        f"{async_t.calls} for the same setting"
    )


def test_the_failure_message_reports_the_real_number():
    client, transport = sync_client(2, fail=True)
    with pytest.raises(ZPLNetworkError) as excinfo:
        client.analyze(MATRIX)
    assert str(transport.calls) in str(excinfo.value), (
        f"the error says {excinfo.value!s} after {transport.calls} attempts; a "
        f"count that does not match what happened sends the reader looking in "
        f"the wrong place"
    )


# ── Parity with the other SDK ─────────────────────────────────────────────


def _make_request_bodies() -> list[tuple[str, str]]:
    """The body of each `_make_request`, comments and strings removed.

    Blocks are cut by indentation from the `def` line, so one implementation
    cannot answer for the other. String literals go too: both functions build
    error messages that contain the word `raise` inside them.
    """
    source = (
        Path(__file__).resolve().parents[1] / "zeropointlogic" / "client.py"
    ).read_text(encoding="utf-8")
    lines = source.splitlines()
    out: list[tuple[str, str]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(?:async\s+)?def\s+_make_request\b", line)
        if not m:
            continue
        indent = len(m.group(1))
        body = []
        for nxt in lines[i + 1:]:
            if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                break
            body.append(nxt)
        text = "\n".join(body)
        text = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', "", text)
        text = re.sub(r'"[^"\n]*"|\'[^\'\n]*\'', '""', text)
        text = re.sub(r"#[^\n]*", "", text)
        out.append((("async " if "async" in line else "") + f"_make_request @ line {i + 1}", text))
    return out


def test_neither_request_loop_can_fall_off_its_end():
    """The shape of the original defect, made impossible rather than unlikely.

    A loop that runs zero times let the function end with no return and no
    raise, and Python hands back None for that. The caller then got an
    AttributeError from the result parser, naming nothing about retries.

    The behavioural checks above prove the bound is right today. This one holds
    the property that survives a wrong bound: however the loop is written, the
    function must end in a raise, so a future regression is loud.

    The only check in this file that reads the source, and the one mutation
    that escaped the battery when this file was written - removing that raise
    changes no behaviour today, which is exactly why nothing behavioural can
    see it go.
    """
    bodies = _make_request_bodies()
    assert len(bodies) == 2, (
        f"expected the sync and async implementations, found {len(bodies)}; "
        f"this check no longer knows what it is reading"
    )
    for name, body in bodies:
        lines = [ln for ln in body.splitlines() if ln.strip()]
        assert lines, f"{name} has an empty body"
        # The last STATEMENT, not the last line: the raise spans three lines
        # and its closing bracket is what a naive read lands on. Statements
        # start at the body's own indentation; anything deeper is a
        # continuation or a nested block.
        # A bracket that closes a multi-line call sits at the same indentation
        # as the statement that opened it, so it is dropped too.
        base = min(len(ln) - len(ln.lstrip()) for ln in lines)
        statements = [
            ln.strip()
            for ln in lines
            if len(ln) - len(ln.lstrip()) == base and not ln.strip().startswith((")", "]", "}"))
        ]
        assert statements, f"{name}: no statement found at the body's indentation"
        assert statements[-1].startswith("raise "), (
            f"{name} ends with `{statements[-1]}` instead of a raise. If the loop above "
            f"ever runs zero times, this function returns None and the caller "
            f"gets an AttributeError out of the result parser - the exact defect "
            f"this file was written for."
        )


def test_typescript_counts_the_same_way():
    """The TypeScript client's loop bound, read rather than assumed.

    This is the one check here that reads a file, and it reads the OTHER
    package - so it catches the two drifting apart, which is the failure no
    test inside either package can see on its own.
    """
    ts = Path(__file__).resolve().parents[2] / "typescript" / "src" / "client.ts"
    if not ts.exists():  # pragma: no cover - checked out alone
        pytest.skip(f"the TypeScript package is not beside this one at {ts}")

    source = ts.read_text(encoding="utf-8")
    # Comments stripped: this bound is discussed in prose nearby, and a scan
    # that read the prose would pass with the loop deleted.
    source = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", source)

    loops = re.findall(r"for\s*\([^)]*attempt[^)]*\)", source)
    assert loops, "no retry loop found in the TypeScript client; this check is now blind"
    assert any("<=" in loop and "maxRetries" in loop for loop in loops), (
        "the TypeScript client no longer runs one attempt more than its retry "
        f"count, so the two SDKs disagree about the same setting: {loops}"
    )
