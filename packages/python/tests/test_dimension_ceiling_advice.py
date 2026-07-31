"""Do not tell a customer to buy something that does not exist.

AUDIT 2026-07-31: both SDKs refused a matrix above 100x100 with

    "The engine rejects dimension > 100; upgrade plan if you need higher d."

No amount of money follows that advice. 100 is ``BinaryMatrix::MAX_N``, a hard
engine constant, and the request is refused before any plan is consulted. The
most expensive plan, Enterprise XL at $999/mo, grants exactly ``max_d`` 100 -
there is nothing above it to buy at any price.

The sentence conflated two different limits, which is why it read plausibly.
Below 100 the per-plan ceiling - 9 / 16 / 25 / 32 / 48 / 64 / 100 - is real and
upgrading does raise it, and the engine reports that case itself with
"Dimension X exceeds plan limit of Y". The advice was correct for a situation
this message never fires in, and wrong for the only one it does.
"""

from pathlib import Path

from zeropointlogic.utils import validate_matrix

TS_UTILS = Path(__file__).resolve().parents[2] / "typescript" / "src" / "utils.ts"
ENGINE_MATRIX = Path("C:/Proiecte/zpl-engine-source/crates/zpl-core/src/matrix.rs")


def square(n):
    return [[(i + j) % 2 for j in range(n)] for i in range(n)]


def test_over_limit_does_not_suggest_an_upgrade():
    ok, message = validate_matrix(square(101))

    assert not ok, "a 101x101 matrix was accepted - the engine rejects it"
    assert "upgrade" not in message.lower(), (
        "refusing a matrix above the engine ceiling still suggests upgrading. No plan "
        "accepts more than 100 - Enterprise XL at $999/mo grants exactly 100 - so this "
        "sends a paying customer to buy something that does not exist."
    )
    assert "hard maximum" in message, (
        "the message no longer says 100 is the engine's own limit rather than the "
        "caller's plan, which is what makes the refusal actionable"
    )


def test_the_ceiling_matches_the_engine_constant():
    # The number is written into the message, so it can go stale silently.
    if not ENGINE_MATRIX.exists():
        return  # engine repo not checked out beside this one

    import re

    m = re.search(r"const MAX_N:\s*usize\s*=\s*(\d+)", ENGINE_MATRIX.read_text(encoding="utf-8"))
    assert m, "could not read MAX_N from the engine"
    max_n = int(m.group(1))

    ok_at_max, _ = validate_matrix(square(max_n))
    assert ok_at_max, f"a {max_n}x{max_n} matrix is refused locally, but the engine accepts it"

    ok_above, _ = validate_matrix(square(max_n + 1))
    assert not ok_above, (
        f"a {max_n + 1}x{max_n + 1} matrix passes validation, but the engine returns 400"
    )


def test_the_typescript_sdk_gives_the_same_answer():
    src = TS_UTILS.read_text(encoding="utf-8")

    # Strip comments: the audit note above the fix quotes the old sentence, so a
    # raw scan would find "upgrade" in it and report the bug unfixed - or find
    # the new wording in a comment and report it fixed when it is not.
    code = "\n".join(
        line for line in src.splitlines() if not line.lstrip().startswith(("//", "*", "/*"))
    )

    assert "upgrade plan if you need higher d" not in code, (
        "the TypeScript SDK still suggests upgrading past a ceiling no plan exceeds"
    )
    assert "hard maximum, not a plan limit" in code, (
        "the TypeScript SDK no longer explains that 100 is the engine's limit, so the "
        "two languages now answer the same question differently"
    )
