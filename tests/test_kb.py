"""Keep the shipped knowledge base clean: no PDFs, no secrets, required files present."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pool
from tools.book_check import EMAIL_RE, SUPPORT_EMAIL

KB = ROOT / "kb"
BINARY_SUFFIXES = {".pdf", ".epub", ".djvu", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip", ".docx"}
EXTRA_SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}\b"),
]


def kb_files():
    return [path for path in KB.rglob("*") if path.is_file()]


def secret_hits(text):
    hits = []
    hits.extend(pool.find_secrets(text))
    for regex in EXTRA_SECRET_PATTERNS:
        if regex.search(text):
            hits.append(regex.pattern)
    return hits


class KnowledgeBaseTest(unittest.TestCase):
    def test_required_files_exist(self):
        for name in ("README.md", "rules.md", "results.md"):
            self.assertTrue((KB / name).is_file(), name)
        self.assertTrue(list((KB / "topics").glob("*.md")))

    def test_no_pdfs_or_binary_documents(self):
        for path in kb_files():
            self.assertNotIn(path.suffix.lower(), BINARY_SUFFIXES, str(path))
            self.assertNotEqual(path.read_bytes()[:5], b"%PDF-", str(path))

    def test_no_secrets_or_personal_emails(self):
        for path in kb_files():
            text = path.read_text(encoding="utf-8")
            self.assertEqual(secret_hits(text), [], str(path))
            self.assertIsNone(EMAIL_RE.search(text.replace(SUPPORT_EMAIL, "")), str(path))

    def test_secret_detector_catches_a_fake_key(self):
        fake = "api_key = " + "A1b2C3d4E5f6G7h8I9j0"
        self.assertTrue(secret_hits(fake))
        self.assertTrue(secret_hits("-----BEGIN " + "PRIVATE KEY-----"))

    def test_rules_and_results_content(self):
        rules = (KB / "rules.md").read_text(encoding="utf-8")
        for needle in ("triple screen", "2% rule", "Wyckoff", "Lo, Mamaysky", "Freeze rules", "Deflate"):
            self.assertIn(needle, rules)
        results = (KB / "results.md").read_text(encoding="utf-8")
        for needle in ("+21,090", "1.89", "2.66%", "+20,099", "2.06", "About 25 rule sets", "Not forward-tested", "Paper only"):
            self.assertIn(needle, results)

    def test_every_topic_cites_a_source(self):
        for path in (KB / "topics").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertRegex(text, r"(19|20)\d\d", str(path))
            self.assertIn(" — ", text, str(path))

    def test_kb_stays_small(self):
        total = sum(path.stat().st_size for path in kb_files())
        self.assertLess(total, 1_000_000)


class BridgesDocTest(unittest.TestCase):
    def test_bridges_walkthrough(self):
        text = (ROOT / "docs" / "bridges.md").read_text(encoding="utf-8")
        for needle in ("MetaAPI", "Windows terminal", "Automated Trading Interface", "webhook",
                       "I'll decide later", "Back to main menu", "Demo check", "off by default",
                       "trading data only", "never pasted into chat"):
            self.assertIn(needle, text)
        setup = (ROOT / "SETUP.md").read_text(encoding="utf-8")
        coordinator = (ROOT / "bots" / "coordinator.md").read_text(encoding="utf-8")
        for doc in (setup, coordinator):
            self.assertIn("Connect my platform for demo fills", doc)
            self.assertIn("kb/rules.md", doc)
            self.assertIn("kb/results.md", doc)


if __name__ == "__main__":
    unittest.main()
