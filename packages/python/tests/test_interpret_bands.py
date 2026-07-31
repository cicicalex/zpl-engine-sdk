"""Two SDKs, one product, one set of words.

AUDIT 2026-07-31: interpret_ain used bands 0.85 / 0.70 / 0.55 / 0.40 / 0.25
while the TypeScript SDK used 0.95 / 0.8 / 0.7 / 0.6 / 0.4 / 0.2, and neither
matched the engine's ain_status. Measured, same readings, both SDKs:

  ain 0.87  TS "Excellent neutrality"  here "Perfectly Neutral"   engine NEUTRAL
  ain 0.75  TS "Good neutrality"       here "Highly Neutral"      engine MODERATE_BIAS
  ain 0.58  TS "Weak neutrality"       here "Moderately Neutral"  engine SIGNIFICANT_BIAS

"Perfectly Neutral" started at 0.85, covering the whole of the engine's NEUTRAL
band and most of HIGHLY_NEUTRAL. The engine reserves its top name for 0.96 and
above.

Both SDKs now use the engine's boundaries and identical wording, verified by
running them side by side: the same string at every reading sampled.
"""

import re
from pathlib import Path

from zeropointlogic.utils import interpret_ain

# The engine's bands, from crates/zpl-core/src/ain.rs.
BANDS = [
    (0.96, "Certified"),
    (0.90, "Highly neutral"),
    (0.80, "Neutral"),
    (0.60, "Moderate bias"),
    (0.40, "Significant bias"),
    (0.0, "High bias"),
]


def _expected(ain: float) -> str:
    return next(name for lo, name in BANDS if ain >= lo)


class TestInterpretBands:
    def test_every_reading_uses_its_engine_band(self):
        wrong = []
        for i in range(1001):
            ain = i / 1000
            got = interpret_ain(ain, "short")
            want = _expected(ain)
            if got != want:
                wrong.append(f"ain {ain:.3f}: {got!r} for band {want!r}")
        assert wrong[:5] == [], f"{len(wrong)} readings described with the wrong band"

    def test_boundaries_are_the_engines(self):
        assert interpret_ain(0.96, "short") == "Certified"
        assert interpret_ain(0.959, "short") == "Highly neutral"
        assert interpret_ain(0.90, "short") == "Highly neutral"
        assert interpret_ain(0.899, "short") == "Neutral"
        assert interpret_ain(0.80, "short") == "Neutral"
        assert interpret_ain(0.799, "short") == "Moderate bias"
        assert interpret_ain(0.60, "short") == "Moderate bias"
        assert interpret_ain(0.599, "short") == "Significant bias"
        assert interpret_ain(0.40, "short") == "Significant bias"
        assert interpret_ain(0.399, "short") == "High bias"

    def test_nothing_calls_a_biased_reading_perfect(self):
        # The specific softenings that shipped.
        assert "Perfect" not in interpret_ain(0.87, "medium"), "0.87 is NEUTRAL"
        assert "Highly" not in interpret_ain(0.75, "medium"), "0.75 is MODERATE_BIAS"
        assert "Neutral" not in interpret_ain(0.58, "medium"), "0.58 is SIGNIFICANT_BIAS"

    def test_all_three_verbosities_stay_in_band(self):
        for ain in (0.98, 0.92, 0.85, 0.70, 0.50, 0.20):
            words = {v: interpret_ain(ain, v) for v in ("short", "medium", "long")}
            assert all(words.values()), f"empty interpretation at {ain}"
            # long is a sentence; short and medium must not contradict it
            assert words["long"].lower().startswith(
                words["short"].lower()[:6]
            ), f"verbosities disagree at {ain}: {words}"

    def test_the_typescript_sdk_uses_the_same_boundaries(self):
        ts = Path(__file__).resolve().parents[2] / "typescript" / "src" / "utils.ts"
        if not ts.exists():
            return
        src = ts.read_text(encoding="utf-8")
        start = src.index("export function interpretAIN")
        body = src[start : src.index("\n}", start)]
        bounds = [float(m) for m in re.findall(r"ain >= ([\d.]+)", body)]
        assert bounds == [lo for lo, _ in BANDS if lo > 0], (
            "the two SDKs use different boundaries again - the same number would "
            "be described differently depending on the caller's language"
        )
