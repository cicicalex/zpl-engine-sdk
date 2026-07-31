"""HTTP error parsing aligned with the ZPL engine MCP client (Cloudflare-safe messages)."""

import re


def parse_engine_http_error(response) -> str:
    """Build a human-readable message for non-JSON or Cloudflare-blocked responses.

    Args:
        response: ``requests.Response``-like object with ``status_code``, ``headers``, ``text``.

    Returns:
        Multi-line explanation suitable for exceptions or logs.
    """
    status = getattr(response, "status_code", 0)
    headers = getattr(response, "headers", {}) or {}
    ct = (headers.get("Content-Type") or "").lower()
    is_html = "text/html" in ct
    cf_ray = headers.get("cf-ray") or headers.get("CF-Ray")
    cf_mitigated = headers.get("cf-mitigated")

    body = ""
    try:
        body = response.text or ""
    except Exception:
        body = ""

    if is_html or cf_mitigated or (cf_ray and status >= 400 and "application/json" not in ct):
        # AUDIT 2026-07-31, reproduced against production, not inferred:
        #
        #   GET /sweep?d=100&samples=50000
        #     -> 504 after 60.2s, server: cloudflare, content-type text/html
        #
        # 60.2s is the engine's own sweep timeout. The engine returns its JSON
        # {"error": "Sweep timeout exceeded 60s", "code": 504}, and Cloudflare
        # replaces the body with its branded HTML page, so the engine's message
        # never reaches the caller and every JSON parse fails.
        #
        # Both halves of what we told them were then wrong. The body carries
        # Cloudflare branding, so the old check reported "Cloudflare blocked the
        # request" - it blocked nothing, the origin ran out of time. And the
        # causes were fixed text printed for every status, so a customer whose
        # computation timed out was advised to change their User-Agent. Bot
        # blocking is 403 and rate limiting is 429; neither yields a 504.
        #
        # d=100 is Enterprise XL's own ceiling and samples=50000 is the
        # documented maximum, so this is the top of the paid ladder pointing its
        # most expensive customer at the wrong thing.
        timed_out = status in (504, 522, 524)

        snippet = "Cloudflare returned an HTML page instead of JSON"
        if re.search(
            r"Just a moment|Checking your browser|cf-browser-verification|cf_chl_",
            body,
            re.I,
        ):
            snippet = "Cloudflare browser challenge intercepted the request"
        elif timed_out:
            # Checked before the branding test: the timeout page is
            # Cloudflare-branded too, and "blocked" is the wrong word for a
            # request that was forwarded, ran, and exceeded the clock.
            snippet = (
                "the engine did not answer in time and Cloudflare returned its timeout page"
            )
        elif re.search(r"Attention Required|cloudflare", body, re.I):
            snippet = "Cloudflare blocked the request"

        if timed_out:
            causes = [
                "  • The computation exceeded the engine's limit — 30s for /compute, 60s for /sweep.",
                "  • Lower `samples` first: it scales the work linearly and costs no extra tokens.",
                "  • Then lower the dimension. /sweep runs 19 passes, so it reaches the ceiling first.",
            ]
        else:
            causes = [
                "  • User-Agent blocked as a bot — use a browser-like User-Agent.",
                "  • Rate limits — wait and retry.",
            ]

        ray = f" (cf-ray: {cf_ray})" if cf_ray else ""
        lines = [
            f"Engine {status} via Cloudflare{ray}: {snippet}.",
            "",
            "Likely causes:",
            *causes,
            "  • Check https://engine.zeropointlogic.io/health",
        ]
        if cf_ray:
            lines.append(f"  • Include cf-ray {cf_ray} in bug reports.")
        return "\n".join(lines)

    try:
        err = response.json()
        if isinstance(err, dict):
            msg = err.get("error") or err.get("message") or str(err)
        else:
            msg = str(err)
    except Exception:
        msg = getattr(response, "reason", None) or "Unknown error"
    return f"Engine error {status}: {msg}"
