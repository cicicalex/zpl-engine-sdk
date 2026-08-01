/**
 * Nothing this package publishes may advertise a version other than the one
 * being published.
 *
 * AUDIT 2026-08-01, measured the morning of the deploy: `package.json` was at
 * 2.1.0 and `package-lock.json` still said 1.0.4 in two places — a whole major
 * behind, because the version bumps across all four packages were hand-edited
 * and cargo/npm never regenerated the locks.
 *
 * Measured before assuming the worst: `npm ci --dry-run` exits 0 with the root
 * version stale, and package-lock is not in `files`, so it never ships. This is
 * the mild surface. It is checked anyway — a guard that exempts the harmless
 * one is where the next drift lands, and the same hand-edit missed the MCP's
 * registry manifest, which was not harmless at all.
 *
 * The constant in the outgoing headers is guarded elsewhere:
 * client-headers.test.mjs compares SDK_VERSION against package.json, which is
 * what caught meta.ts sitting at 2.0.6 while the package moved to 2.1.0. This
 * file covers the surfaces that test does not read.
 *
 * The changelog lives at the monorepo root — both packages release together off
 * one file — so it is two levels up, not beside this package.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const MONOREPO = dirname(dirname(ROOT));

async function readJson(path, label) {
  let raw;
  try {
    raw = await readFile(path, "utf-8");
  } catch (err) {
    assert.fail(`${label} could not be read (${err.code}) — this guard would otherwise check nothing`);
  }
  try {
    return JSON.parse(raw);
  } catch (err) {
    assert.fail(`${label} is not valid JSON: ${err.message}`);
  }
}

const pkg = await readJson(join(ROOT, "package.json"), "package.json");
const VERSION = pkg.version;

/** Three components, or a `v` prefix on two. A bare two-component number is
 *  left alone so ordinary prose ("1.5 seconds") does not read as a release. */
function versionTokens(text) {
  const out = [];
  for (const m of text.matchAll(/(v?)(\d+(?:\.\d+)+)/gi)) {
    const parts = m[2].split(".");
    if (parts.length > 3) continue;
    if (parts.length === 3 || (parts.length === 2 && m[1])) out.push(m[2]);
  }
  return out;
}

test("package.json carries a real semver version", () => {
  assert.match(
    VERSION ?? "",
    /^\d+\.\d+\.\d+(?:-[\w.]+)?$/,
    `package.json version is ${JSON.stringify(VERSION)}; every assertion below compares against it`,
  );
});

test("the npm description does not advertise a different version", () => {
  const desc = pkg.description ?? "";
  assert.ok(desc.length > 0, "package.json has no description");

  const wrong = versionTokens(desc).filter((v) => v !== VERSION);
  assert.deepEqual(
    wrong,
    [],
    `the npm description names ${wrong.join(", ")} while this package publishes as ${VERSION}. ` +
      `npm renders it on the package page and it cannot be edited without publishing again — ` +
      `the CLI's description shipped release notes two minors out of date for exactly this reason.`,
  );
});

test("the lock file's root version matches the manifest", async () => {
  const lock = await readJson(join(ROOT, "package-lock.json"), "package-lock.json");
  assert.equal(lock.version, VERSION, `package-lock.json root version is ${lock.version}, package is ${VERSION}`);
  assert.equal(
    lock.packages?.[""]?.version,
    VERSION,
    `package-lock.json packages[""].version is ${lock.packages?.[""]?.version}, package is ${VERSION}`,
  );
});

test("the monorepo changelog documents the version about to ship", async () => {
  const path = join(MONOREPO, "CHANGELOG.md");
  let changelog;
  try {
    changelog = await readFile(path, "utf-8");
  } catch (err) {
    assert.fail(`${path} could not be read (${err.code})`);
  }

  // Both `## [2.1.0] - date` and `## [2.1.0] — date` occur in this file.
  const headings = [...changelog.matchAll(/^##\s*\[([^\]]+)\]/gm)].map((m) => m[1]);
  assert.ok(
    headings.includes(VERSION),
    `CHANGELOG.md has no "## [${VERSION}]" entry. Headings present: ${headings.slice(0, 6).join(", ")}. ` +
      `Publishing to npm is irreversible, so the notes have to exist before the tag does.`,
  );
});
