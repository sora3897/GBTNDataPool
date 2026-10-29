"""Desk health, repo health, known fixes, and the health-issue plan."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.health_check import (
    EXPECTED_BOTS,
    accept_bug_record,
    apply_safe_fixes,
    bug_record_from_text,
    find_known_fixes,
    plan_health_issue,
    prepare_upstream,
    run_desk_health,
    run_repo_health,
    scan_repo,
    send_report_to_dev,
)
from tools.sharing import confirm_upstream, set_sharing

NY = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=NY)


def bug(**overrides):
    payload = {
        "symptom": "pending queue sat for two days",
        "component": "server",
        "platform": "undecided",
        "health_check_code": "pending-queue",
        "root_cause": "intake was not run",
        "fix_steps": ["Run intake"],
        "status": "fixed",
        "fixed_in": "abc1234",
        "supersedes": "",
    }
    payload.update(overrides.pop("payload", {}))
    base = {
        "id": "bugrecord0101",
        "timestamp_et": "2024-01-15T15:00:00-05:00",
        "source_bot": "health-check",
        "type": "bug_report",
        "symbol": "DESK",
        "label": "paper",
        "payload": payload,
    }
    base.update(overrides)
    return base


class DeskFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        bots = self.root / "bots"
        bots.mkdir()
        for name in EXPECTED_BOTS:
            (bots / f"{name}.md").write_text("# " + name + "\nStay idle until start.\n", encoding="utf-8")
        config = self.root / "config"
        config.mkdir()
        (config / "platform.json").write_text(json.dumps({
            "platform": "undecided", "mode": "paper", "chosen_at": None,
        }), encoding="utf-8")
        (config / "user_settings.json").write_text(json.dumps({
            "share_data": False, "share_bugs": False, "upstream_confirmed": False,
        }), encoding="utf-8")
        self._old = os.environ.get("NETWORK_POOL_ROOT")
        os.environ["NETWORK_POOL_ROOT"] = str(self.root)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("NETWORK_POOL_ROOT", None)
        else:
            os.environ["NETWORK_POOL_ROOT"] = self._old
        self.tmp.cleanup()

    def test_idle_desk_passes(self):
        result = run_desk_health(self.root, now=NOW)
        self.assertEqual(result["status"], "pass", result["summary"])
        self.assertIn("Health check: pass.", result["summary"])

    def test_running_while_stopped_fails_with_a_fix(self):
        result = run_desk_health(self.root, desk_state={
            "desk": "stopped",
            "bots": {"scan": "running"},
            "routines": ["morning-scan"],
        }, now=NOW)
        stopped = next(item for item in result["checks"] if item["code"] == "stopped-desk")
        self.assertEqual(stopped["status"], "fail")
        self.assertIn("stop", stopped["fix"].lower())
        self.assertNotIn("password", result["summary"].lower())

    def test_demo_login_failure_hides_account_data(self):
        (self.root / "config" / "platform.json").write_text(json.dumps({
            "platform": "mt5", "mode": "paper", "chosen_at": "2026-10-27T09:00:00",
        }), encoding="utf-8")
        number = "100" + "200302"
        (self.root / "config" / "demo_connection.json").write_text(json.dumps({
            "connected": True, "account_number": number,
        }), encoding="utf-8")
        result = run_desk_health(self.root, now=NOW)
        login = next(item for item in result["checks"] if item["code"] == "demo-login")
        self.assertEqual(login["status"], "fail")
        self.assertEqual(login["safe_fix"], "strip-demo-connection")
        self.assertNotIn(number, result["summary"])
        applied = apply_safe_fixes(self.root, ["strip-demo-connection"], now=NOW)
        self.assertIn("strip-demo-connection", applied["applied"])
        stored = json.loads((self.root / "config" / "demo_connection.json").read_text(encoding="utf-8"))
        self.assertEqual(set(stored), {"connected"})
        self.assertNotIn("account_number", stored)

    def test_paper_mode_is_a_safe_fix(self):
        (self.root / "config" / "platform.json").write_text(json.dumps({
            "platform": "mt5", "mode": "live", "chosen_at": None,
        }), encoding="utf-8")
        before = run_desk_health(self.root, now=NOW)
        platform = next(item for item in before["checks"] if item["code"] == "platform")
        self.assertEqual(platform["safe_fix"], "force-paper-mode")
        refused = apply_safe_fixes(self.root, ["not-a-real-fix"], now=NOW)
        self.assertEqual(refused["applied"], [])
        self.assertEqual(json.loads((self.root / "config" / "platform.json").read_text())["mode"], "live")
        apply_safe_fixes(self.root, ["force-paper-mode"], now=NOW)
        self.assertEqual(json.loads((self.root / "config" / "platform.json").read_text())["mode"], "paper")

    def test_log_scan_does_not_echo_secrets(self):
        secret = "account number " + ("100" + "200303")
        result = run_desk_health(self.root, logs=[secret], now=NOW)
        logs = next(item for item in result["checks"] if item["code"] == "secrets-in-logs")
        self.assertEqual(logs["status"], "fail")
        self.assertNotIn("200303", result["summary"])

    def test_known_fix_is_offered(self):
        folder = self.root / "bugs"
        folder.mkdir()
        (folder / "records.jsonl").write_text(json.dumps(bug(
            payload={
                "symptom": "a bot role file was missing",
                "health_check_code": "bots",
                "fix_steps": ["Restore the role file"],
                "status": "fixed",
            },
        )) + "\n", encoding="utf-8")
        found = find_known_fixes(self.root, code="bots")
        self.assertEqual(found[0]["fix_steps"], ["Restore the role file"])
        (self.root / "bots" / "scan.md").unlink()
        result = run_desk_health(self.root, now=NOW)
        bots = next(item for item in result["checks"] if item["code"] == "bots")
        self.assertEqual(bots["known_fix"]["status"], "fixed")
        self.assertIn("Restore the role file", result["summary"])

    def test_stuck_queue_fails(self):
        pending = self.root / "pending"
        pending.mkdir()
        (pending / "sub_old.json").write_text(json.dumps({
            "submission_id": "sub_old",
            "submitted_at_et": "2024-01-15T15:00:00-05:00",
            "status": "submitted",
            "record": {"id": "pendingrecord1"},
        }), encoding="utf-8")
        result = run_desk_health(self.root, now=NOW)
        queue = next(item for item in result["checks"] if item["code"] == "pending-queue")
        self.assertEqual(queue["status"], "fail")

    def test_upstream_bug_respects_the_switch(self):
        record = bug()
        blocked = prepare_upstream(self.root, "bugs", record)
        self.assertEqual(blocked["reason"], "off")
        self.assertIsNone(blocked["record"])
        set_sharing(self.root, True)
        asking = prepare_upstream(self.root, "bugs", record)
        self.assertEqual(asking["reason"], "needs_confirmation")
        self.assertIn("Share this", asking["ask"])
        confirm_upstream(self.root)
        allowed = prepare_upstream(self.root, "bugs", record)
        self.assertTrue(allowed["allowed"])
        self.assertEqual(allowed["record"]["type"], "bug_report")

    def _failing_result(self):
        state = {"desk": "stopped", "bots": {name: "running" for name in EXPECTED_BOTS}}
        result = run_desk_health(self.root, desk_state=state, now=NOW)
        self.assertEqual(result["status"], "fail")
        return result

    def test_report_to_dev_stays_local_when_sharing_is_off(self):
        plan = send_report_to_dev(self.root, self._failing_result(), "2026-10-27T12:00:00-04:00")
        self.assertEqual(plan["route"], "local")
        self.assertFalse(plan["allowed"])
        self.assertFalse(plan["email_sent"])
        self.assertFalse(plan["uses_user_email"])
        self.assertIn("stays on your machine", plan["message"])
        self.assertIn("Turn data sharing on", plan["options"])
        self.assertIn("Show the dev's contact", plan["options"])
        self.assertIn("Back to main menu", plan["options"])
        self.assertEqual(plan["support_contact"], "gbtnsupport@gmail.com")

    def test_report_to_dev_goes_through_the_pool_when_sharing_is_on(self):
        set_sharing(self.root, True)
        result = self._failing_result()
        asking = send_report_to_dev(self.root, result, "2026-10-27T12:00:00-04:00")
        self.assertEqual(asking["route"], "pool")
        self.assertEqual(asking["reason"], "needs_confirmation")
        self.assertFalse(asking["email_sent"])
        self.assertIn("Back to main menu", asking["options"])
        confirm_upstream(self.root)
        plan = send_report_to_dev(self.root, result, "2026-10-27T12:00:00-04:00")
        self.assertTrue(plan["allowed"])
        self.assertFalse(plan["email_sent"])
        self.assertIn("bug-fix.yml", plan["submit_via"])
        record = plan["record"]
        self.assertEqual(record["type"], "bug_report")
        for key in ("symptom", "root_cause", "fix_steps", "status"):
            self.assertTrue(record["payload"][key], key)
        self.assertEqual(record["payload"]["status"], "open")
        accepted = accept_bug_record(self.root, record)
        self.assertTrue(accepted["ok"], accepted["reasons"])

    def test_report_to_dev_with_nothing_to_report(self):
        result = run_desk_health(self.root, now=NOW)
        plan = send_report_to_dev(self.root, result)
        self.assertEqual(plan["route"], "none")
        self.assertFalse(plan["email_sent"])

    def test_accept_bug_record_and_reject_account_data(self):
        accepted = accept_bug_record(self.root, bug())
        self.assertTrue(accepted["ok"], accepted["reasons"])
        self.assertTrue((self.root / "bugs" / "records.jsonl").is_file())
        dirty = bug(id="bugrecord0102", payload={"account_balance": 10})
        refused = accept_bug_record(self.root, dirty)
        self.assertFalse(refused["ok"])
        self.assertNotIn("10", " ".join(refused["reasons"]))
        text = (self.root / "bugs" / "records.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("account_balance", text)


class RepoHealthTest(unittest.TestCase):
    def test_this_repo_is_not_a_hard_failure(self):
        result = run_repo_health(ROOT)
        self.assertNotEqual(result["status"], "fail", result["summary"])
        by_code = {item["code"]: item for item in result["checks"]}
        self.assertEqual(by_code["secret-scan"]["status"], "pass")
        self.assertEqual(by_code["duplicate-ids"]["status"], "pass")
        self.assertEqual(by_code["workflows"]["status"], "pass")
        self.assertIn(by_code["records"]["status"], ("pass", "warn"))
        self.assertEqual(scan_repo(ROOT), [])

    def test_duplicate_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "market_notes"
            folder.mkdir()
            line = json.dumps({
                "id": "duperecord01",
                "timestamp_et": "2024-01-15T15:00:00-05:00",
                "source_bot": "unit-test",
                "type": "market_note",
                "symbol": "ES",
                "label": "paper",
                "payload": {"note": "one"},
            })
            other = json.dumps({
                "id": "duperecord01",
                "timestamp_et": "2024-02-15T15:00:00-05:00",
                "source_bot": "unit-test",
                "type": "market_note",
                "symbol": "ES",
                "label": "paper",
                "payload": {"note": "two"},
            })
            (folder / "records.jsonl").write_text(line + "\n" + other + "\n", encoding="utf-8")
            for name in ("strategies", "backtests", "paper_trades", "bugs"):
                (root / name).mkdir()
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            shutil.copy(ROOT / ".github" / "workflows" / "health.yml", workflows / "health.yml")
            (root / "config").mkdir()
            shutil.copy(ROOT / "config" / "user_settings.json", root / "config" / "user_settings.json")
            result = run_repo_health(root)
            duplicate = next(item for item in result["checks"] if item["code"] == "duplicate-ids")
            self.assertEqual(duplicate["status"], "fail")


class SupersededRecordTest(unittest.TestCase):
    def test_superseded_backtest_no_longer_warns(self):
        from tools.health_check import check_record_lines
        old = {
            "id": "oldbacktest01",
            "timestamp_et": "2024-02-15T15:00:00-05:00",
            "source_bot": "unit-test",
            "type": "backtest",
            "symbol": "ES",
            "label": "backtest",
            "payload": {"oos": {"pf": 1.1}},
        }
        new = dict(old, id="newbacktest01",
                   payload={"oos": {"pf": 1.1}, "variant_count": 3, "supersedes": "oldbacktest01"})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "backtests").mkdir()
            path = root / "backtests" / "records.jsonl"
            path.write_text(json.dumps(old) + "\n", encoding="utf-8")
            self.assertTrue(any("variant count" in p for p in check_record_lines(root)))
            path.write_text(json.dumps(old) + "\n" + json.dumps(new) + "\n", encoding="utf-8")
            self.assertEqual(check_record_lines(root), [])


class IssuePlanTest(unittest.TestCase):
    def test_open_comment_and_close_with_fix(self):
        failed = {"status": "fail", "summary": "Health check: fail.", "checks": []}
        opened = plan_health_issue(failed, None, "2024-01-15T15:00:00-05:00")
        self.assertEqual(opened["action"], "open")
        self.assertIn("health", opened["title"].lower())
        commented = plan_health_issue(failed, {"number": 4, "body": "old", "comments": []}, "2024-01-15T15:00:00-05:00")
        self.assertEqual(commented["action"], "comment")
        self.assertIsNone(commented["bug"])
        body = """## Fix
symptom: the health workflow did not lint
component: pipeline
platform: undecided
health_check_code: workflows
root_cause: health.yml was missing
fixed_in: abc1234
fix_steps:
- Add the workflow
- Run it again
"""
        closed = plan_health_issue(
            {"status": "pass", "summary": "Health check: pass.", "checks": []},
            {"number": 4, "body": body, "comments": []},
            "2024-01-15T15:00:00-05:00",
        )
        self.assertEqual(closed["action"], "close")
        self.assertEqual(closed["bug"]["type"], "bug_report")
        self.assertEqual(closed["bug"]["payload"]["status"], "fixed")
        self.assertEqual(closed["bug"]["payload"]["fix_steps"], ["Add the workflow", "Run it again"])
        fenced = "```json\n" + json.dumps(bug()) + "\n```\n"
        parsed = bug_record_from_text(fenced, "2024-01-15T15:00:00-05:00")
        self.assertEqual(parsed["id"], "bugrecord0101")

    def test_docs_cover_the_onboarding_contract(self):
        setup = (ROOT / "SETUP.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        coordinator = (ROOT / "bots" / "coordinator.md").read_text(encoding="utf-8")
        privacy = (
            "We only collect trading data (instrument, side, size, entry and exit prices and times, "
            "P&L, strategy label). We never collect account data: no login, password, account number, "
            "balance, personal info, or broker identity. Trading data shared to the public pool is "
            "anonymized, checked by the automatic filter, and labeled paper."
        )
        self.assertIn(privacy, setup)
        self.assertIn(privacy, readme)
        self.assertIn("Want a different name? Just tell me.", setup)
        self.assertIn("Want a different name? Just tell me.", coordinator)
        self.assertIn("Desk is running. Just say stop and we'll stop.", setup)
        self.assertIn("Desk is running. Just say stop and we'll stop.", coordinator)
        self.assertIn("Share anonymized trading data and bug fixes with the network pool?", setup)
        self.assertIn("We're still in beta, so every shared trade and fix helps every desk get better faster.", setup)
        self.assertIn("Health & bug fixes", readme)
        self.assertIn("## Health and bug fixes", setup)
        self.assertIn("gbtnsupport@gmail.com", setup)
        welcome = (
            "A message from the dev: Hello, and thank you for your interest in the Grok Bot Trading Network. "
            "This network is still in early stages of development and my goal is to be able to one day have a "
            "steady blueprint that people can consistently build to benefit them. It is recommended you start "
            "this on paper trade, as the data your desk gathers will benefit every single instance run by you "
            "and everyone who takes part in testing. Just say 'build this' and the desk will walk you through the set up"
        )
        self.assertIn(welcome, setup)
        self.assertIn(welcome, coordinator)
        self.assertIn("include Back to main menu as one of the options", setup)
        self.assertIn("include Back to main menu as one of the options", coordinator)
        self.assertIn("never emails anyone and never uses the user's email account", setup)
        self.assertIn("never emails anyone and never uses the user's email account", coordinator)
        self.assertNotIn("Say one short paragraph: this is a paper-trading desk.", setup)
        blob = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(part in {".git", "__pycache__"} for part in path.parts):
                continue
            if path.suffix.lower() not in {".md", ".py", ".yml", ".yaml", ".json"}:
                continue
            blob.append(path.read_text(encoding="utf-8", errors="replace"))
        text = "\n".join(blob)
        retired = ("Li" + "la", "server" + "bot", "li" + "la.md")
        for word in retired:
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
