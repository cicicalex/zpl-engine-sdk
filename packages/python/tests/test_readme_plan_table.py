"""The PyPI landing page must not advertise numbers the system does not honour.

AUDIT 2026-07-31. The plan table in README.md was wrong four ways, and a PyPI
release cannot be edited after publish:

  Free listed at 100 tokens/month. It is 5,000 - 100 is the dormant
       tokens_per_day field. Line 43 of the same README already said 5,000, so
       the file contradicted itself.
  XL listed as "Unlimited". It is 50,000,000, enforced in
       crates/zpl-security/src/plans.rs. The same false word is enumerated as a
       known-false claim on the website's pricing page.
  "1 token = 1 compute operation". The price of a call is a step band from 1 to
       2000. Understating by up to 2000x, in the direction that makes a buyer
       overcommit and then hit a wall.
  A "Price EUR" column. No EUR pricing exists anywhere: not in the website
       constants, not in the engine plan table, not in the /plans response. The
       SDK's own price_eur reads `.get("price_eur", 0.0)` from a payload that
       never carries the key, which is why every paid plan prints EUR 0.00. The
       column was removed rather than corrected - inventing replacement numbers
       would repeat the original mistake with more confidence.

Checked against the engine's plans.rs, which is the enforcing side, so this
guard fails if the README drifts OR if the plans themselves change without the
page being revisited.
"""

import re
import unittest
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"
ENGINE_PLANS = Path("C:/Proiecte/zpl-engine-source/crates/zpl-security/src/plans.rs")

VARIANT_TO_ROW = {
    "Free": "Free",
    "Basic": "Basic",
    "Pro": "Pro",
    "GamePro": "GamePro",
    "Studio": "Studio",
    "Agent": "Agent",
    "Enterprise": "Enterprise",
    "EnterpriseXl": "Enterprise XL",
}


def engine_plans():
    """max_d, tokens_per_month, max_keys and price, from the enforcing side."""
    text = ENGINE_PLANS.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(
        r"Plan::(\w+)\s*=>\s*PlanLimits\s*\{\s*max_d:\s*(\d+),\s*"
        r"tokens_per_month:\s*([\d_]+),\s*tokens_per_day:\s*[\d_]+,\s*"
        r"max_keys:\s*(\d+),\s*price_usd:\s*(\d+)",
        text,
    ):
        row = VARIANT_TO_ROW.get(m.group(1))
        if not row:
            continue
        out[row] = {
            "maxD": int(m.group(2)),
            "tokens": int(m.group(3).replace("_", "")),
            "keys": int(m.group(4)),
            "price": int(m.group(5)),
        }
    return out


def readme_plans():
    text = README.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(
        r"^\|\s*([\w ]+?)\s*\|\s*([\d,]+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*\$([\d,]+)\s*\|",
        text,
        re.M,
    ):
        out[m.group(1)] = {
            "tokens": int(m.group(2).replace(",", "")),
            "maxD": int(m.group(3)),
            "keys": int(m.group(4)),
            "price": int(m.group(5).replace(",", "")),
        }
    return out


class TestReadmePlanTable(unittest.TestCase):
    def setUp(self):
        if not ENGINE_PLANS.exists():
            self.skipTest("engine repo not checked out beside this one")

    def test_every_plan_row_matches_what_the_engine_enforces(self):
        engine = engine_plans()
        readme = readme_plans()

        self.assertEqual(
            len(engine), 8, f"parsed {len(engine)} plans from the engine, expected 8"
        )
        self.assertEqual(
            len(readme),
            8,
            f"parsed {len(readme)} plan rows from README.md, expected 8. If the table "
            f"changed shape this guard is now checking a subset and would not say so.",
        )

        drift = []
        for plan, want in engine.items():
            got = readme.get(plan)
            if got is None:
                drift.append(f"{plan}: enforced by the engine, absent from the README")
                continue
            for field in ("tokens", "maxD", "keys", "price"):
                if got[field] != want[field]:
                    drift.append(
                        f"{plan}.{field}: README says {got[field]}, the engine enforces {want[field]}"
                    )

        self.assertEqual(
            drift,
            [],
            "the PyPI landing page advertises something other than what the engine "
            "grants:\n  " + "\n  ".join(drift) + "\n\nA published release cannot be edited.",
        )

    def test_no_plan_is_called_unlimited(self):
        text = README.read_text(encoding="utf-8")
        table_at = text.find("## API Plans and Pricing")
        self.assertNotEqual(table_at, -1, "the plan section is gone")
        table = text[table_at : table_at + 2000]

        self.assertNotIn(
            "Unlimited",
            table,
            "a plan is described as Unlimited again. Enterprise XL is enforced at "
            "50,000,000 tokens/month - the word is false and the same claim is already "
            "tracked as a known-false item on the website's pricing page.",
        )

    def test_the_cost_of_a_call_is_not_described_as_one_token(self):
        text = README.read_text(encoding="utf-8")

        self.assertNotIn(
            "1 token = 1 compute operation",
            text,
            "the README says one call costs one token. A call costs between 1 and 2000 "
            "depending on dimension, so this understates by up to 2000x - in the "
            "direction that makes a buyer overcommit.",
        )
        self.assertIn(
            "2000",
            text,
            "the README no longer states the top of the cost band, so a reader cannot "
            "tell what an expensive call costs.",
        )

    def test_no_invented_currency(self):
        text = README.read_text(encoding="utf-8")
        # Nothing in the website constants, the engine plan table, or the /plans
        # response carries a EUR price. A column of them is fabricated.
        self.assertNotIn(
            "Price EUR",
            text,
            "the EUR price column is back. No EUR pricing exists in any source of "
            "truth - the SDK's own price_eur reads a key /plans never sends, which is "
            "why it prints 0.00 for every paid plan.",
        )


if __name__ == "__main__":
    unittest.main()
