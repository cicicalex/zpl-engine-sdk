"""The version this SDK reports must be the version it publishes as.

AUDIT 2026-07-31. Both SDKs carried the identical dead guard: a test asserting
that the ``X-ZPL-Client-Version`` header equals the version constant, where the
header is built *from* that constant. It compares the constant to itself and
passes for any value.

In TypeScript that let real drift ship-shaped: ``package.json`` was bumped to
2.1.0 for this release and ``meta.ts`` still said ``2.0.6``, so every header
from a 2.1.0 install would have reported 2.0.6 - permanently, because npm does
not let you edit a published tarball.

Python is correct today, and has twice the room to drift: the version is
declared in ``pyproject.toml`` **and** in ``zeropointlogic/version.py``, and the
client reads only the latter. Bump one and the package publishes under a number
it never reports.

What that costs, beyond tidiness: adoption dashboards read the new release as
zero uptake, and setting the engine's ``ZPL_MIN_VERSION_SDK_PYTHON`` floor to
the new version would 426 every up-to-date install.

The only assertion that can catch this is one against a source the constant is
not derived from - so this reads pyproject.toml.
"""

import re
import unittest
from pathlib import Path

from zeropointlogic import __version__

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


class TestVersionIsWhatShips(unittest.TestCase):
    def test_reported_version_matches_pyproject(self):
        text = PYPROJECT.read_text(encoding="utf-8")

        # The project version, not the several other `version`-ish keys further
        # down the file (black's target-version, mypy's python_version).
        m = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.M)
        self.assertIsNotNone(m, "no project version found in pyproject.toml")
        declared = m.group(1)

        self.assertEqual(
            __version__,
            declared,
            f"the SDK reports {__version__} and publishes as {declared}. Every "
            f"X-ZPL-Client-Version header and every version gate would carry the "
            f"wrong number, and a published PyPI release cannot be edited.",
        )

    def test_the_two_version_files_agree(self):
        # version.py is what the client imports; pyproject.toml is what PyPI
        # reads. Nothing else ties them together.
        version_py = (
            Path(__file__).resolve().parents[1] / "zeropointlogic" / "version.py"
        ).read_text(encoding="utf-8")

        m = re.search(r'__version__\s*=\s*"([^"]+)"', version_py)
        self.assertIsNotNone(m, "version.py no longer declares __version__")
        self.assertEqual(
            m.group(1),
            __version__,
            "version.py declares a different version than the package exports - "
            "something is re-exporting a stale value.",
        )


if __name__ == "__main__":
    unittest.main()
