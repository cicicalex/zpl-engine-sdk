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
        snippet = "Cloudflare returned an HTML page instead of JSON"
        if re.search(
            r"Just a moment|Checking your browser|cf-browser-verification|cf_chl_",
            body,
            re.I,
        ):
            snippet = "Cloudflare browser challenge intercepted the request"
        elif re.search(r"Attention Required|cloudflare", body, re.I):
            snippet = "Cloudflare blocked the request"
        ray = f" (cf-ray: {cf_ray})" if cf_ray else ""
        lines = [
            f"Engine {status} via Cloudflare{ray}: {snippet}.",
            "",
            "Likely causes:",
            "  • User-Agent blocked as a bot — use a browser-like User-Agent.",
            "  • Rate limits — wait and retry.",
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
