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
            self.assertTrue(" — " in text or "http" in text, str(path))

    def test_kb_stays_small(self):
        total = sum(path.stat().st_size for path in kb_files())
        self.assertLess(total, 2_000_000)


class FuturesPackTest(unittest.TestCase):
    NEW = (
        "futures-stats.md",
        "data/futures_stats.json",
        "data/contract_specs.json",
        "topics/futures-contracts-and-sessions.md",
        "topics/futures-papers.md",
        "topics/quant-validation-toolkit.md",
    )

    def test_new_files_exist(self):
        for name in self.NEW:
            self.assertTrue((KB / name).is_file(), name)

    def test_no_raw_datasets_shipped(self):
        for path in kb_files():
            self.assertNotIn(path.suffix.lower(), {".csv", ".parquet", ".feather", ".h5"}, str(path))
            self.assertLess(path.stat().st_size, 300_000, str(path))

    def test_futuresclock_attribution(self):
        import json
        specs = json.loads((KB / "data" / "contract_specs.json").read_text(encoding="utf-8"))
        self.assertIn("futuresclock.com", specs["attribution"])
        self.assertEqual(specs["count"], len(specs["contracts"]))
        self.assertGreaterEqual(specs["count"], 70)
        es = next(c for c in specs["contracts"] if c["code"] == "ES")
        self.assertEqual(es["tick_value"], "$12.50")
        self.assertTrue(es["sessions"][0]["et_jan"])
        for name in ("README.md", "topics/futures-contracts-and-sessions.md"):
            self.assertIn("futuresclock.com", (KB / name).read_text(encoding="utf-8"), name)

    def test_mit_attribution(self):
        toolkit = (KB / "topics" / "quant-validation-toolkit.md").read_text(encoding="utf-8")
        self.assertIn("MIT License", toolkit)
        self.assertIn("Copyright (c) 2025 Yimin Du", toolkit)
        helper = (ROOT / "tools" / "validation_checks.py").read_text(encoding="utf-8")
        self.assertIn("MIT License", helper)
        self.assertIn("Yimin Du", helper)

    def test_stats_are_labelled_and_sourced(self):
        import json
        stats_md = (KB / "futures-stats.md").read_text(encoding="utf-8")
        for needle in ("not signals", "License unverified", "not** shipped", "Truncated: yes"):
            self.assertIn(needle, stats_md)
        stats = json.loads((KB / "data" / "futures_stats.json").read_text(encoding="utf-8"))
        self.assertIn("not signals", stats["label"].lower())
        self.assertIn("license unverified", stats["daily"]["source"])
        self.assertTrue(stats["nq_1min"]["gap_check"]["hits_excel_row_limit"])
        self.assertEqual(len(stats["daily"]["contracts"]), 24)

    def test_papers_cover_all_eleven(self):
        text = (KB / "topics" / "futures-papers.md").read_text(encoding="utf-8")
        for needle in ("Retail Traders in Futures Markets", "Hong", "Kyle & Obizhaeva", "Quarter-Hour",
                       "2505.05595", "2407.01577", "2512.23773", "2509.09995", "2507.07107", "2609.16930", "2610.25495"):
            self.assertIn(needle, text)

    def test_new_rules_cited(self):
        rules = (KB / "rules.md").read_text(encoding="utf-8")
        for needle in ("Retail Traders in Futures Markets", "Quarter-Hour Effect", "opening-range break", "futuresclock.com"):
            self.assertIn(needle, rules)

    def test_setup_loads_futures_pack(self):
        for doc in ("SETUP.md", "bots/coordinator.md"):
            text = (ROOT / doc).read_text(encoding="utf-8")
            for needle in ("kb/futures-stats.md", "kb/data/contract_specs.json", "quant-validation-toolkit.md"):
                self.assertIn(needle, text, doc)

    def test_validation_helper_self_audit(self):
        from tools.validation_checks import check_lag_alignment, run_self_audit
        self.assertTrue(run_self_audit()["ok"])
        self.assertFalse(check_lag_alignment([1, 1], [0.0, 0.5], [0.0, 0.0]))


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
