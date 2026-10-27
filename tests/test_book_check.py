"""Checklist tests: one pass, each failure, a duplicate, and a secret."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pool
from tools.book_check import extract_json, review_changes, validate_record


def record(**overrides):
    base = {
        "id": "paperrecord01",
        "timestamp_et": "2024-01-15T15:00:00-05:00",
        "source_bot": "unit-test",
        "type": "market_note",
        "symbol": "ES",
        "label": "paper",
        "payload": {"note": "paper observation"},
    }
    base.update(overrides)
    if "payload" in overrides:
        base["payload"] = overrides["payload"]
    return base


class BookCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._old = os.environ.get("NETWORK_POOL_ROOT")
        os.environ["NETWORK_POOL_ROOT"] = str(self.root)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("NETWORK_POOL_ROOT", None)
        else:
            os.environ["NETWORK_POOL_ROOT"] = self._old
        self.tmp.cleanup()

    def check(self, rec):
        return validate_record(rec, self.root)

    def test_pass_market_note(self):
        result = self.check(record())
        self.assertTrue(result["ok"], result["reasons"])
        self.assertEqual(result["id"], "paperrecord01")
        self.assertFalse(result["needs_book_review"])
        self.assertNotIn("needs-book-review", result["record"]["payload"])

    def test_pass_backtest(self):
        result = self.check(record(
            id="backtestrecord1", type="backtest", label="backtest",
            payload={"out_of_sample": {"pnl": 1.2}, "variant_count": 8, "pf": 1.4,
                     "drawdown": 12, "win_rate": 0.55},
        ))
        self.assertTrue(result["ok"], result["reasons"])
        self.assertFalse(result["needs_book_review"])

    def test_schema_unknown_field(self):
        rec = record()
        rec["extra"] = 1
        result = self.check(rec)
        self.assertFalse(result["ok"])
        self.assertTrue(any(reason.startswith("schema:") for reason in result["reasons"]))

    def test_bad_label(self):
        result = self.check(record(label="live"))
        self.assertFalse(result["ok"])
        self.assertIn("label must be backtest, paper, or live-observation", result["reasons"])

    def test_timestamp_not_eastern(self):
        result = self.check(record(timestamp_et="2024-01-15T15:00:00Z"))
        self.assertFalse(result["ok"])
        self.assertIn(result["reasons"][0], result["reasons"])
        self.assertTrue(result["reasons"][0].startswith("timestamp_et"))

    def test_timestamp_wrong_offset_for_date(self):
        result = self.check(record(timestamp_et="2024-01-15T15:00:00-04:00"))
        self.assertFalse(result["ok"])
        self.assertIn("timestamp_et offset does not match US Eastern for that moment", result["reasons"])

    def test_timestamp_in_future(self):
        result = self.check(record(timestamp_et="2099-01-15T15:00:00-05:00"))
        self.assertFalse(result["ok"])
        self.assertIn("timestamp_et is in the future", result["reasons"])

    def test_missing_source_bot(self):
        rec = record()
        del rec["source_bot"]
        result = self.check(rec)
        self.assertFalse(result["ok"])
        self.assertIn("source_bot is required", result["reasons"])

    def test_negative_profit_factor(self):
        result = self.check(record(payload={"note": "x", "pf": -0.1}))
        self.assertFalse(result["ok"])
        self.assertIn("profit factor must be >= 0", result["reasons"])

    def test_drawdown_out_of_range(self):
        result = self.check(record(payload={"note": "x", "drawdown": 140}))
        self.assertFalse(result["ok"])
        self.assertIn("drawdown must be between 0 and 100", result["reasons"])

    def test_win_rate_out_of_range(self):
        result = self.check(record(payload={"note": "x", "win_rate": 1.4}))
        self.assertFalse(result["ok"])
        self.assertIn("win rate must be between 0 and 1", result["reasons"])

    def test_pnl_inconsistent(self):
        result = self.check(record(payload={"trades": [1, 2, 3], "pnl": 10}))
        self.assertFalse(result["ok"])
        self.assertIn("P&L is not consistent with trades", result["reasons"])

    def test_pnl_consistent_when_trades_given(self):
        result = self.check(record(payload={
            "trades": [{"pnl": 1.5}, {"pnl": -0.5}], "pnl": 1, "start_bank": 100, "end_bank": 101,
        }))
        self.assertTrue(result["ok"], result["reasons"])

    def test_duplicate(self):
        folder = self.root / "market_notes"
        folder.mkdir()
        first = record()
        (folder / "records.jsonl").write_text(json.dumps(first) + "\n", encoding="utf-8")
        again = record(id="differentid01", timestamp_et="2024-02-15T15:00:00-05:00")
        result = self.check(again)
        self.assertFalse(result["ok"])
        self.assertTrue(any(reason.startswith("duplicate of ") for reason in result["reasons"]))

    def test_secret(self):
        leaked = "".join(["api", "_key=", "abcDEF123456"])
        result = self.check(record(payload={"note": leaked}))
        self.assertFalse(result["ok"])
        self.assertTrue(any("secret or personal data" in reason for reason in result["reasons"]))
        self.assertNotIn(leaked, " ".join(result["reasons"]))

    def test_email_and_phone(self):
        email = "".join(["user", "@", "example.com"])
        phone = "".join(["555", "-010-0199"])
        email_result = self.check(record(payload={"note": email}))
        phone_result = self.check(record(id="paperrecord02", payload={"note": phone}))
        self.assertIn("personal data: email", email_result["reasons"])
        self.assertNotIn(email, " ".join(email_result["reasons"]))
        self.assertIn("personal data: phone number", phone_result["reasons"])
        self.assertNotIn(phone, " ".join(phone_result["reasons"]))

    def test_backtest_missing_out_of_sample(self):
        result = self.check(record(
            type="backtest", label="backtest", payload={"variant_count": 3, "note": "x"},
        ))
        self.assertFalse(result["ok"])
        self.assertIn("backtest requires out-of-sample results", result["reasons"])

    def test_backtest_missing_variant_count(self):
        result = self.check(record(
            type="backtest", label="backtest", payload={"out_of_sample": {"pnl": 1}, "note": "x"},
        ))
        self.assertFalse(result["ok"])
        self.assertIn("backtest requires a variant count", result["reasons"])

    def test_record_too_large(self):
        result = self.check(record(payload={"note": "x" * 60000}))
        self.assertFalse(result["ok"])
        self.assertIn("record exceeds 50 KB", result["reasons"])

    def test_borderline_pf_and_variants_are_accepted_with_flag(self):
        high_pf = self.check(record(payload={"note": "x", "pf": 6}))
        self.assertTrue(high_pf["ok"], high_pf["reasons"])
        self.assertTrue(high_pf["record"]["payload"]["needs-book-review"])
        many = self.check(record(
            id="backtestrecord2", type="backtest", label="backtest",
            payload={"out_of_sample": {"pnl": 1}, "variant_count": 51},
        ))
        self.assertTrue(many["ok"], many["reasons"])
        self.assertTrue(many["record"]["payload"]["needs-book-review"])
        exact = self.check(record(id="paperrecord03", payload={"note": "x", "pf": 5, "variant_count": 50}))
        # variant_count on a non-backtest is not required; 50 is not over the line.
        self.assertTrue(exact["ok"], exact["reasons"])
        self.assertNotIn("needs-book-review", exact["record"]["payload"])

    def test_append_only_and_other_files(self):
        line = json.dumps(record()) + "\n"
        added = record(id="paperrecord04", payload={"note": "second"})
        good = review_changes([
            ("market_notes/records.jsonl", line, line + json.dumps(added) + "\n"),
        ], self.root)
        self.assertTrue(good["ok"], good["reasons"])
        self.assertEqual(good["code"], 0)
        changed = review_changes([
            ("market_notes/records.jsonl", line, json.dumps(added) + "\n"),
        ], self.root)
        self.assertFalse(changed["ok"])
        self.assertTrue(any("not append-only" in reason for reason in changed["reasons"]))
        other = review_changes([
            ("README.md", "old\n", "new\n"),
        ], self.root)
        self.assertEqual(other["code"], 2)
        self.assertIn("needs the maintainer", other["reasons"][0])

    def test_issue_body_extract(self):
        body = "### JSON record\n\n```json\n" + json.dumps(record()) + "\n```\n"
        self.assertEqual(extract_json(body)["symbol"], "ES")

    def test_cli_exit_codes(self):
        path = self.root / "one.json"
        path.write_text(json.dumps(record()), encoding="utf-8")
        good = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "book_check.py"),
             "--record", str(path), "--pool", str(self.root)],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        path.write_text(json.dumps(record(label="nope")), encoding="utf-8")
        bad = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "book_check.py"),
             "--record", str(path), "--pool", str(self.root)],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(bad.returncode, 1)


class PoolAppendTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._old = os.environ.get("NETWORK_POOL_ROOT")
        os.environ["NETWORK_POOL_ROOT"] = str(self.root)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("NETWORK_POOL_ROOT", None)
        else:
            os.environ["NETWORK_POOL_ROOT"] = self._old
        self.tmp.cleanup()

    def test_append_routes_and_is_idempotent(self):
        rec = record(type="paper_trade", label="paper", symbol="NQ")
        stored = pool.append_checked(rec)
        path = self.root / "paper_trades" / "records.jsonl"
        self.assertTrue(path.exists())
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["symbol"], "NQ")
        again = pool.append_checked(stored)
        self.assertEqual(again["id"], stored["id"])
        self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)
        other = dict(stored)
        other["id"] = "differentid09"
        with self.assertRaises(ValueError):
            pool.append_checked(other)

    def test_local_queue_still_submits(self):
        sid = pool.submit(record())
        self.assertTrue((self.root / "pending" / f"{sid}.json").is_file())
        self.assertEqual(pool.intake()[sid], "valid")


class PlatformConfigTest(unittest.TestCase):
    def test_default_platform_is_paper_and_undecided(self):
        data = json.loads((ROOT / "config" / "platform.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data), {"platform", "mode", "chosen_at"})
        self.assertEqual(data["platform"], "undecided")
        self.assertEqual(data["mode"], "paper")


if __name__ == "__main__":
    unittest.main()
