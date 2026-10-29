"""Pre-demo hardening: broken files and bad command-line input never crash a tool,
MT5 broker identity stays private, and the expected fresh-MT5 warning is never sent as a bug."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pool
from tools.book_check import main as book_main
from tools.book_check import privacy_reasons
from tools.health_check import (
    EXPECTED_BOTS,
    apply_safe_fixes,
    bug_record_from_health,
    default_desk_state,
    run_desk_health,
)
from tools.health_check import main as health_main

NY = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=NY)


def run_cli(args, env_root, cwd=ROOT):
    env = dict(os.environ, NETWORK_POOL_ROOT=str(env_root))
    return subprocess.run([sys.executable] + args, cwd=cwd, env=env, capture_output=True, text=True)


class Desk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "bots").mkdir()
        for name in EXPECTED_BOTS:
            (self.root / "bots" / f"{name}.md").write_text("# " + name + "\n", encoding="utf-8")
        (self.root / "config").mkdir()
        self.platform("undecided")
        (self.root / "config" / "user_settings.json").write_text(json.dumps({
            "share_data": False, "share_bugs": False, "upstream_confirmed": False}), encoding="utf-8")
        self._old = os.environ.get("NETWORK_POOL_ROOT")
        os.environ["NETWORK_POOL_ROOT"] = str(self.root)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("NETWORK_POOL_ROOT", None)
        else:
            os.environ["NETWORK_POOL_ROOT"] = self._old
        self.tmp.cleanup()

    def platform(self, value, **extra):
        data = {"platform": value, "mode": "paper", "chosen_at": None}
        data.update(extra)
        (self.root / "config" / "platform.json").write_text(json.dumps(data), encoding="utf-8")

    def check(self, code, **kw):
        result = run_desk_health(self.root, now=NOW, **kw)
        return result, next(item for item in result["checks"] if item["code"] == code)

    def health(self, *args):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = health_main(["--pool", str(self.root)] + list(args))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()


class FreshMt5Test(Desk):
    def test_fresh_mt5_desk_warns_only_on_demo_login(self):
        self.platform("mt5")
        result, login = self.check("demo-login")
        self.assertEqual(result["status"], "warn")
        self.assertEqual(login["status"], "warn")
        self.assertTrue(login.get("expected"))
        self.assertEqual([c["code"] for c in result["checks"] if c["status"] != "pass"], ["demo-login"])

    def test_expected_demo_warning_is_never_a_bug_report(self):
        self.platform("mt5")
        result = run_desk_health(self.root, now=NOW)
        record = bug_record_from_health(self.root, result)
        self.assertIsNone(record)
        self.assertTrue(record is None or "demo-login" not in json.dumps(record))

    def test_uppercase_platform_gets_a_safe_fix(self):
        self.platform(" MT5 ")
        _, item = self.check("platform")
        self.assertEqual((item["status"], item["safe_fix"]), ("fail", "normalize-platform"))
        apply_safe_fixes(self.root, ["normalize-platform"], now=NOW)
        data = json.loads((self.root / "config" / "platform.json").read_text(encoding="utf-8"))
        self.assertEqual(data["platform"], "mt5")
        self.assertEqual(self.check("platform")[1]["status"], "pass")

    def test_platform_list_value_fails_cleanly_with_reset(self):
        self.platform(["mt5"])
        _, item = self.check("platform")
        self.assertEqual((item["status"], item["safe_fix"]), ("fail", "write-platform-default"))
        self.assertIn(self.check("demo-login")[1]["status"], ("pass", "warn"))

    def test_extra_platform_fields_can_be_stripped(self):
        self.platform("mt5", server="Broker-Demo")
        _, item = self.check("platform")
        self.assertEqual(item["safe_fix"], "strip-platform-extras")
        apply_safe_fixes(self.root, ["strip-platform-extras"], now=NOW)
        data = json.loads((self.root / "config" / "platform.json").read_text(encoding="utf-8"))
        self.assertEqual(data, {"platform": "mt5", "mode": "paper", "chosen_at": None})


class BrokenFilesTest(Desk):
    def test_binary_config_files_fail_with_safe_fixes(self):
        for name, code, fix in (("demo_connection.json", "demo-login", "strip-demo-connection"),
                                ("platform.json", "platform", "write-platform-default"),
                                ("telegram_status.json", "telegram", "strip-telegram-status")):
            path = self.root / "config" / name
            old = path.read_bytes() if path.exists() else None
            path.write_bytes(b"\xff\xfe\x00")
            _, item = self.check(code)
            self.assertEqual((item["status"], item.get("safe_fix")), ("fail", fix), name)
            if old is None:
                path.unlink()
            else:
                path.write_bytes(old)

    def test_corrupt_and_non_object_records_lines_do_not_crash(self):
        folder = self.root / "market_notes"
        folder.mkdir()
        (folder / "records.jsonl").write_text('not json\n[1, 2]\n"text"\n', encoding="utf-8")
        result, item = self.check("pool")
        self.assertEqual(item["status"], "fail")
        self.assertEqual(pool.counts()["market_notes"], 0)
        self.assertEqual(pool.query(type="market_note"), [])

    def test_pending_file_with_naive_timestamp(self):
        (self.root / "pending").mkdir()
        (self.root / "pending" / "sub_1.json").write_text(json.dumps({
            "submission_id": "sub_1", "submitted_at_et": "2026-10-27T03:00:00", "status": "submitted", "record": {}}),
            encoding="utf-8")
        self.assertIn(self.check("pending-queue")[1]["status"], ("pass", "warn", "fail"))

    def test_desk_state_variants(self):
        _, bots = self.check("bots", desk_state={"desk": "paused", "bots": {"Scan": "Paused"}, "routines": "recap"})
        self.assertEqual(bots["status"], "pass")
        _, bots = self.check("bots", desk_state={"desk": "stopped", "bots": ["scan"]})
        self.assertEqual((bots["status"], bots.get("safe_fix")), ("warn", "reset-desk-state"))
        _, bots = self.check("bots", desk_state=["scan"])
        self.assertEqual(bots.get("safe_fix"), "reset-desk-state")

    def test_desk_state_cli_inputs(self):
        bad = self.root / "bad.json"
        for content in ("[1]", "{bad"):
            bad.write_text(content, encoding="utf-8")
            code, out, _ = self.health("--mode", "desk", "--desk-state", str(bad))
            result = json.loads(out)
            bots = next(item for item in result["checks"] if item["code"] == "bots")
            self.assertEqual(bots.get("safe_fix"), "reset-desk-state", content)
        code, out, _ = self.health("--mode", "desk", "--desk-state", str(self.root / "nope.json"))
        self.assertEqual(json.loads(out)["status"], "pass")

    def test_reset_desk_state_and_write_desk_state(self):
        state = self.root / "config" / "desk_state.json"
        state.write_text('{"bots": []}', encoding="utf-8")
        apply_safe_fixes(self.root, ["reset-desk-state"], now=NOW)
        self.assertEqual(json.loads(state.read_text(encoding="utf-8")), default_desk_state())
        state.unlink()
        self.health("--write-desk-state", "stopped")
        data = json.loads(state.read_text(encoding="utf-8"))
        self.assertEqual(data["desk"], "stopped")
        self.assertEqual(set(data["bots"]), set(EXPECTED_BOTS))
        self.assertTrue(all(v == "idle" for v in data["bots"].values()))
        self.assertEqual(data["routines"], [])

    def test_bad_cli_input_gives_a_message_not_a_traceback(self):
        bad = self.root / "bad.json"
        bad.write_text("{bad", encoding="utf-8")
        listed = self.root / "list.json"
        listed.write_text("[1]", encoding="utf-8")
        for flag in ("--report-to-dev", "--save-local-bug"):
            for path in (str(self.root / "nope.json"), str(bad), str(listed)):
                code, _, err = self.health(flag, path)
                self.assertEqual(code, 2, (flag, path))
                self.assertIn("Nothing was changed or sent", err)
                self.assertNotIn("Traceback", err)
        code, _, err = self.health("--json-out", str(self.root / "no" / "dir" / "x.json"))
        self.assertEqual(code, 2)
        code, _, err = self.health("--mark-telegram", "yes", "no")
        self.assertEqual(code, 2)


class PoolCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_bad_input_is_rejected_cleanly(self):
        cases = {
            ("submit",): "usage",
            ("submit", "[1]"): "must be a JSON object",
            ("add", "[1]"): "must be a JSON object",
            ("submit", '{"timestamp_et": 123}'): "timestamp_et must be a string",
            ("append", str(self.root / "nope.json")): "could not read",
            ("query", "noequals"): "usage",
            ("decide", "sub_x", "approve", "r", "--reviewer"): "--reviewer needs a name",
        }
        for args, expect in cases.items():
            proc = run_cli([str(ROOT / "pool.py")] + list(args), self.root)
            self.assertEqual(proc.returncode, 2, args)
            self.assertIn(expect, proc.stderr, args)
            self.assertNotIn("Traceback", proc.stderr, args)

    def test_corrupt_decisions_line_is_skipped(self):
        (self.root / "review").mkdir()
        (self.root / "review" / "decisions.jsonl").write_text("garbage\n[1]\n", encoding="utf-8")
        proc = run_cli([str(ROOT / "pool.py"), "promote"], self.root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)


class BookCheckCliTest(unittest.TestCase):
    def run_main(self, args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = book_main(args)
        return code, json.loads(out.getvalue())

    def test_missing_files_and_bad_revisions_are_reasons(self):
        code, result = self.run_main(["--record", "/nonexistent/record.json"])
        self.assertEqual(code, 1)
        self.assertIn("could not read", result["reasons"][0])
        code, result = self.run_main(["--issue-body", "/nonexistent/body.md"])
        self.assertEqual(code, 1)
        cwd = os.getcwd()
        os.chdir(ROOT)
        try:
            code, result = self.run_main(["--diff", "no-such-revision-xyz", "HEAD"])
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 1)
        self.assertIn("git diff failed", result["reasons"][0])


class Mt5PrivacyTest(unittest.TestCase):
    def test_mt5_server_names_and_broker_keys_are_private(self):
        self.assertIn("account data: broker server name", privacy_reasons("filled on ICMarketsSC-Demo02 at 5100"))
        self.assertIn("account data: broker server name", privacy_reasons("server MetaQuotes-Demo"))
        for key in ("broker", "server", "mt5_server", "trade_server", "metaapi_account_id"):
            self.assertTrue(privacy_reasons({"payload": {key: "x1"}}), key)

    def test_metaapi_style_token_is_blocked(self):
        token = "eyJ" + "a" * 20 + ".eyJ" + "b" * 20 + "." + "c" * 20
        self.assertTrue(pool.secret_hits({"note": token}))

    def test_normal_trade_text_is_not_flagged(self):
        for text in ("E10 long MES on the RTH open", "paper balance 10000", "US500 spread 0.5 at 10:05 ET",
                     "pre-demo hardening", "XAUUSD untested until Load backtests it", "E10-Demo run", "Paper-Trade log"):
            self.assertEqual(privacy_reasons(text), [], text)


class SharingCliTest(unittest.TestCase):
    def test_corrupt_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            path = root / "config" / "user_settings.json"
            for content in (b"\xff\xfe", b"{bad"):
                path.write_bytes(content)
                for cmd in ("status", "on", "confirm"):
                    proc = run_cli([str(ROOT / "tools" / "sharing.py"), "--pool", str(root), cmd], root)
                    self.assertEqual(proc.returncode, 1, (content, cmd, proc.stderr))
                    self.assertNotIn("Traceback", proc.stderr)
                    self.assertIn("sharing stays off", proc.stderr)
                proc = run_cli([str(ROOT / "tools" / "sharing.py"), "--pool", str(root), "off"], root)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["share_data"], False)


if __name__ == "__main__":
    unittest.main()
