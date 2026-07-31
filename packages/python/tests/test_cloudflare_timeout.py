"""A gateway timeout must not be reported as a bot block.

AUDIT 2026-07-31, reproduced against production rather than reasoned about::

    GET /sweep?d=100&samples=50000
      -> 504 after 60.2s, server: cloudflare, content-type: text/html, cf-ray set

60.2s is the engine's own sweep timeout, so the engine did answer - with
``{"error": "Sweep timeout exceeded 60s", "code": 504}`` - and Cloudflare
replaced the body with its branded HTML page. The engine's message never
reaches the caller, and every JSON parse fails.

Both SDKs then described it wrongly. The page carries Cloudflare branding, so
the snippet check said "Cloudflare blocked the request"; nothing was blocked,
the request was forwarded, ran, and ran out of clock. And the causes list was
fixed text emitted for every status, so the advice was to change the User-Agent
and wait and retry. Bot blocking is 403 and rate limiting is 429 - neither
produces a 504, so both suggestions were unreachable for the case at hand.

d=100 is Enterprise XL's own ceiling and samples=50000 is the documented
maximum, so this was the top of the paid ladder pointing its most expensive
customer at the wrong thing.

The TypeScript side is checked here too: the two SDKs have drifted before, and
the same production failure must not read differently depending on the language
a team happens to use.
"""

from pathlib import Path

from zeropointlogic.http_errors import parse_engine_http_error

TS_ERRORS = (
    Path(__file__).resolve().parents[2] / "typescript" / "src" / "errors.ts"
)

CF_TIMEOUT_BODY = (
    "<!DOCTYPE html><html lang=\"en-US\"><head>"
    "<title>zeropointlogic.io | 504: Gateway time-out</title></head>"
    "<body><h1>Gateway time-out</h1><p>Error code 504</p>"
    "<p>Ray ID: a23aea752951a63e</p></body></html>"
)


class FakeResponse:
    """Exactly the shape production sent, headers included."""

    def __init__(self, status, body, content_type="text/html; charset=UTF-8",
                 cf_ray="a23aea752951a63e-FRA"):
        self.status_code = status
        self.text = body
        self.headers = {"content-type": content_type}
        if cf_ray:
            self.headers["cf-ray"] = cf_ray

    def json(self):
        raise ValueError("not json")


def test_timeout_is_not_called_a_block_and_does_not_blame_the_user_agent():
    msg = parse_engine_http_error(FakeResponse(504, CF_TIMEOUT_BODY))

    assert "User-Agent" not in msg, (
        "a gateway timeout still advises changing the User-Agent. Bot blocking is "
        "403; that advice cannot apply to a 504."
    )
    assert "blocked the request" not in msg, (
        "a 504 is still called a block. The request was forwarded, ran, and "
        "exceeded the clock - nothing blocked it."
    )
    assert "did not answer in time" in msg, (
        "the message no longer says the engine ran out of time, which is the one "
        "fact that explains the status."
    )
    assert "samples" in msg, (
        "the message no longer names `samples`, the lever that scales the work "
        "linearly at no extra token cost - what the caller should lower first."
    )
    assert "a23aea752951a63e" in msg, "the cf-ray must survive for bug reports"


def test_a_genuine_block_still_gets_the_block_advice():
    # The fix must not swing the other way: fixing one wrong diagnosis by
    # installing another is not an improvement.
    body = "<!DOCTYPE html><html><body>Attention Required! | Cloudflare</body></html>"
    msg = parse_engine_http_error(FakeResponse(403, body, cf_ray="deadbeef-FRA"))

    assert "User-Agent" in msg, "a 403 no longer suggests the User-Agent, which is where it applies"
    assert "did not answer in time" not in msg, "a 403 is now described as a timeout"


def test_522_and_524_are_timeouts_too():
    # 522 is a connection timeout and 524 is an origin that accepted the request
    # and never finished. Both mean to a caller what 504 does, and a fix that
    # only knew 504 would leave the two statuses most specific to a slow origin
    # still advising a User-Agent change.
    for status in (522, 524):
        msg = parse_engine_http_error(FakeResponse(status, CF_TIMEOUT_BODY))
        assert "User-Agent" not in msg, f"{status} still advises a User-Agent change"
        assert "did not answer in time" in msg, f"{status} is not described as a timeout"


def test_the_typescript_sdk_says_the_same_thing():
    src = TS_ERRORS.read_text(encoding="utf-8")

    assert "res.status === 504 || res.status === 524 || res.status === 522" in src, (
        "the TypeScript SDK no longer branches on the timeout statuses, so the two "
        "languages now describe the same production failure differently."
    )
    assert "did not answer in time" in src, (
        "the TypeScript snippet no longer states that the engine ran out of time"
    )
    assert "Lower `samples` first" in src, (
        "the TypeScript advice no longer names `samples` as the first lever"
    )
