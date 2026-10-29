"""Role files are platform-aware: an MT5/futures section first, and old meme-coin or
prediction-market terms only inside a labeled optional platform section."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("scan", "vet", "size", "fills", "risk", "load", "book")
OPTIONAL_PREFIX = "Optional platform:"
LEGACY_TERMS = re.compile(
    r"(?i)dexscreener|geckoterminal|bonding|\bsolana\b|\bjupiter\b|\bmeme|\bmints?\b|\brug|"
    r"\bholders?\b|sniper|launchpad|polymarket|kalshi"
)


def role_paths():
    return [ROOT / "bots" / f"{name}.md" for name in ROLES if (ROOT / "bots" / f"{name}.md").is_file()]


def sections(text):
    """Split on level-2 headings. Returns [(heading, body)], with '' for the preamble."""
    out, heading, lines = [], "", []
    for line in text.splitlines():
        if line.startswith("## "):
            out.append((heading, "\n".join(lines)))
            heading, lines = line[3:].strip(), []
        else:
            lines.append(line)
    out.append((heading, "\n".join(lines)))
    return out


class RoleFilesTest(unittest.TestCase):
    def test_required_roles_exist(self):
        for name in ("scan", "size", "fills", "risk", "load", "book"):
            self.assertTrue((ROOT / "bots" / f"{name}.md").is_file(), name)

    def test_mt5_section_first_and_complete(self):
        for path in role_paths():
            heads = [h for h, _ in sections(path.read_text(encoding="utf-8"))]
            platform_heads = [h for h in heads if h.startswith("Platform:") or h.startswith(OPTIONAL_PREFIX)]
            self.assertTrue(platform_heads, path.name)
            self.assertIn("MT5", platform_heads[0], path.name)
            self.assertTrue(any("decide later" in h for h in heads), path.name)
            body = dict(sections(path.read_text(encoding="utf-8")))[platform_heads[0]]
            self.assertRegex(body, r"rules? \d+", f"{path.name}: MT5 section cites kb/rules.md numbers")

    def test_legacy_terms_only_in_optional_sections(self):
        for path in role_paths():
            for heading, body in sections(path.read_text(encoding="utf-8")):
                if heading.startswith(OPTIONAL_PREFIX):
                    continue
                hit = LEGACY_TERMS.search(heading + "\n" + body)
                self.assertIsNone(hit, f"{path.name} [{heading or 'preamble'}]: {hit and hit.group(0)}")

    def test_optional_sections_match_offered_platforms(self):
        platforms = (ROOT / "config" / "platforms.md").read_text(encoding="utf-8")
        offered = [line[3:].strip() for line in platforms.splitlines() if line.startswith("## ")]
        for path in role_paths():
            for heading, _ in sections(path.read_text(encoding="utf-8")):
                if heading.startswith(OPTIONAL_PREFIX):
                    name = heading[len(OPTIONAL_PREFIX):].strip()
                    self.assertTrue(any(o.startswith(name) for o in offered), f"{path.name}: {name}")

    def test_core_rules_present(self):
        for path in role_paths():
            text = path.read_text(encoding="utf-8")
            for needle in ("config/platform.json", "PAPER", "stay idle", "Any stop, pause, or halt",
                           "pool.py submit", "local time zone", "timestamp_et", "<coordinator name>"):
                self.assertTrue(needle in text, f"{path.name}: missing {needle!r}")


if __name__ == "__main__":
    unittest.main()
