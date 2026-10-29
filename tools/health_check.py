#!/usr/bin/env python3
"""Shared health check for the user's desk and the public repo.

Paper and demo only. Output names problems and fixes. It never prints a
login, password, account number, balance, or other account value.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pool
from tools.book_check import SUPPORT_EMAIL, extract_json, privacy_reasons, validate_record
from tools.sharing import load_settings

NY = ZoneInfo("America/New_York")
STUCK_AFTER = timedelta(hours=48)
EXPECTED_BOTS = (
    "coordinator", "scan", "vet", "size", "fills", "risk", "book", "load", "server",
)
PLATFORMS = {
    "mt5", "mt4", "tradingview", "ninjatrader", "tradovate",
    "interactive_brokers", "solana_jupiter", "polymarket_kalshi", "undecided",
}
NEEDS_LOGIN = {"mt5", "mt4", "tradingview", "ninjatrader", "tradovate", "interactive_brokers"}
PLATFORM_KEYS = {"platform", "mode", "chosen_at"}
DEMO_KEYS = {"connected", "checked_at"}
TELEGRAM_KEYS = {"connected", "test_ok", "checked_at"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
JSON_SUFFIXES = {".json", ".jsonl"}
FULL_PRIVACY_PARTS = {"records.jsonl", "pending", "config", "logs"}


def _check(code, name, status, detail, fix="", safe_fix=None):
    item = {"code": code, "name": name, "status": status, "detail": detail, "fix": fix}
    if safe_fix:
        item["safe_fix"] = safe_fix
    return item


def _overall(checks):
    if any(item["status"] == "fail" for item in checks):
        return "fail"
    if any(item["status"] == "warn" for item in checks):
        return "warn"
    return "pass"


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _use_root(root):
    old = os.environ.get("NETWORK_POOL_ROOT")
    os.environ["NETWORK_POOL_ROOT"] = str(root)
    pool._bind_paths()
    return old


def _restore_root(old):
    if old is None:
        os.environ.pop("NETWORK_POOL_ROOT", None)
    else:
        os.environ["NETWORK_POOL_ROOT"] = old
    pool._bind_paths()


def _iter_records(root):
    root = Path(root)
    for folder in pool.FOLDERS.values():
        path = root / folder / "records.jsonl"
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                yield folder, path, lineno, line


def check_record_lines(root):
    """Schema and Book's checklist for every stored record. Skips the self-duplicate hash."""
    problems = []
    superseded = set()
    for _folder, _path, _lineno, line in _iter_records(root):
        try:
            sup = (json.loads(line).get("payload") or {}).get("supersedes")
        except (json.JSONDecodeError, AttributeError):
            continue
        if isinstance(sup, str) and sup:
            superseded.add(sup)
    for folder, _path, lineno, line in _iter_records(root):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            problems.append(f"{folder}/records.jsonl:{lineno}: line is not JSON")
            continue
        if isinstance(rec, dict) and rec.get("id") in superseded:
            continue  # corrected by a later record (append-only fix path)
        result = validate_record(rec, pool_root=None)
        if not result["ok"]:
            ident = result.get("id") or str(lineno)
            problems.extend(f"{ident}: {reason}" for reason in result["reasons"])
    return problems


def duplicate_ids(root):
    seen = {}
    problems = []
    for _folder, path, lineno, line in _iter_records(root):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ident = rec.get("id")
        if not isinstance(ident, str) or not ident:
            problems.append(f"{path.name}:{lineno}: missing id")
            continue
        prior = seen.get(ident)
        if prior:
            problems.append(f"duplicate id {ident}")
        else:
            seen[ident] = f"{path.parent.name}:{lineno}"
    return problems


def content_duplicates(root):
    seen = {}
    problems = []
    for _folder, _path, _lineno, line in _iter_records(root):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        digest = pool.content_hash(rec)
        prior = seen.get(digest)
        ident = str(rec.get("id") or "")
        if prior and prior != ident:
            problems.append(f"duplicate of {prior}")
        elif not prior:
            seen[digest] = ident
    return problems


def _iter_files(root):
    root = Path(root)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.stat().st_size > 5_000_000:
            continue
        yield path


def _full_privacy_target(path, root):
    rel = path.relative_to(root)
    if path.name == "records.jsonl":
        return True
    if rel.parts and rel.parts[0] in {"config", "logs", "pending"}:
        return True
    return False


# Keyword patterns describe the policy and match the detector source itself.
# Token patterns still run on every file. Real assignments are checked separately.
_SOURCE_SKIP = {"credential assignment", "seed phrase keyword", "MT5 login number", "broker login number"}
_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|private[_-]?key|password|passwd)\b"
    r"\s*[\"']?\s*[:=]\s*[\"']?([^\s\"',}]{6,})"
)


def _text_privacy(text):
    """Secrets, emails, and phone numbers in prose. The public support address is allowed."""
    reasons = []
    names = []
    for pattern, name in pool.SECRET_PATTERNS:
        if name in _SOURCE_SKIP:
            continue
        if re.search(pattern, text):
            names.append(name)
    for match in _ASSIGNMENT.finditer(text):
        value = match.group(1)
        if value.startswith(("$", "{", "(", "[")) or "GITHUB" in value.upper():
            continue
        names.append("credential assignment")
        break
    if names:
        reasons.append("secret or personal data: " + ", ".join(sorted(set(names))))
    from tools.book_check import EMAIL_RE, PHONE_RE, SUPPORT_EMAIL
    cleaned = text.replace(SUPPORT_EMAIL, "")
    if EMAIL_RE.search(cleaned):
        reasons.append("personal data: email")
    if PHONE_RE.search(text):
        reasons.append("personal data: phone number")
    return reasons


def _split_record_problems(problems):
    """A stored backtest that only lacks a variant count is a warning, not a hard failure."""
    soft_marker = "backtest requires a variant count"
    soft, hard = [], []
    for problem in problems:
        if problem.endswith(soft_marker):
            soft.append(problem)
        else:
            hard.append(problem)
    return hard, soft


def scan_repo(root):
    """Secret and personal-data scan. Reasons never include the matched values."""
    root = Path(root)
    problems = []
    for path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(root).as_posix()
        reasons = []
        if path.suffix.lower() in JSON_SUFFIXES and _full_privacy_target(path, root):
            parsed = []
            if path.suffix.lower() == ".jsonl":
                for lineno, line in enumerate(text.splitlines(), 1):
                    if not line.strip():
                        continue
                    try:
                        parsed.append(json.loads(line))
                    except json.JSONDecodeError:
                        reasons.append(f"line {lineno} is not JSON")
            else:
                try:
                    parsed.append(json.loads(text))
                except json.JSONDecodeError:
                    reasons.append("invalid JSON")
            for obj in parsed:
                reasons.extend(privacy_reasons(obj))
        else:
            reasons.extend(_text_privacy(text))
        for reason in reasons:
            problems.append(f"{rel}: {reason}")
    return problems


def lint_workflows(root):
    problems = []
    directory = Path(root) / ".github" / "workflows"
    if not directory.is_dir():
        return ["workflows: .github/workflows is missing"]
    files = sorted(list(directory.glob("*.yml")) + list(directory.glob("*.yaml")))
    if not files:
        return ["workflows: no workflow files"]
    for path in files:
        text = path.read_text(encoding="utf-8")
        if "\t" in text:
            problems.append(f"{path.name}: uses tabs")
        for key in ("name:", "on:", "jobs:"):
            if not re.search(rf"(?m)^{re.escape(key)}", text):
                problems.append(f"{path.name}: missing {key[:-1]}")
        if "runs-on:" not in text:
            problems.append(f"{path.name}: missing runs-on")
    health = directory / "health.yml"
    if not health.is_file():
        problems.append("health.yml: missing")
    else:
        text = health.read_text(encoding="utf-8")
        for token in ("push", "pull_request", "workflow_dispatch", "schedule", "cron:"):
            if token not in text:
                problems.append(f"health.yml: missing {token}")
    return problems


def _load_desk_state(root, override):
    if override is not None:
        return override
    path = Path(root) / "config" / "desk_state.json"
    if not path.is_file():
        return {"desk": "stopped", "bots": {}}
    data = _read_json(path)
    if not isinstance(data, dict):
        return {"desk": "stopped", "bots": {}}
    data.setdefault("desk", "stopped")
    data.setdefault("bots", {})
    return data


def _platform_data(root):
    path = Path(root) / "config" / "platform.json"
    if not path.is_file():
        return None, "missing"
    try:
        data = _read_json(path)
    except json.JSONDecodeError:
        return None, "invalid"
    if not isinstance(data, dict):
        return None, "invalid"
    return data, None


def _status_dirty(path, allowed):
    if not path.is_file():
        return False, None
    try:
        data = _read_json(path)
    except json.JSONDecodeError:
        return True, None
    if not isinstance(data, dict):
        return True, None
    if set(data) - allowed:
        return True, data
    return False, data


def _check_bots(root, state):
    missing = [name for name in EXPECTED_BOTS if not (Path(root) / "bots" / f"{name}.md").is_file()]
    if missing:
        return _check(
            "bots", "Bots", "fail",
            "Missing bot roles: " + ", ".join(missing) + ".",
            "Restore the missing role file from the repo, then run this check again. The new bot stays idle.",
        )
    desk = state.get("desk") or "stopped"
    bots = state.get("bots") or {}
    unexpected = []
    for name in EXPECTED_BOTS:
        actual = bots.get(name, "idle")
        if desk == "stopped" and actual not in ("idle", "stopped"):
            unexpected.append(name)
        elif desk == "running" and actual not in ("idle", "running"):
            unexpected.append(name)
        elif desk not in ("stopped", "running"):
            unexpected.append(name)
    if unexpected:
        return _check(
            "bots", "Bots", "fail",
            "These bots are not idle or running as expected: " + ", ".join(unexpected) + ".",
            "Say stop if the desk should be quiet, or start if you meant to run it. Then run the health check again.",
        )
    return _check("bots", "Bots", "pass", "Every bot is on disk and idle or running as expected.")


def _check_platform(root):
    data, problem = _platform_data(root)
    if problem == "missing":
        return _check(
            "platform", "Platform", "fail",
            "config/platform.json is missing.",
            "Choose a platform from the menu, or I'll decide later. Mode stays paper.",
            safe_fix="write-platform-default",
        )
    if problem == "invalid":
        return _check(
            "platform", "Platform", "fail",
            "config/platform.json is not valid JSON.",
            "I can restore a paper, undecided platform file if you say yes.",
            safe_fix="write-platform-default",
        )
    if set(data) != PLATFORM_KEYS:
        return _check(
            "platform", "Platform", "fail",
            "config/platform.json should only contain platform, mode, and chosen_at.",
            "Remove any extra fields. Do not put a login, account number, or balance in that file.",
        )
    if data.get("platform") not in PLATFORMS:
        return _check(
            "platform", "Platform", "fail",
            "The platform value is not one this desk knows.",
            "Pick the platform again from the menu. I'll decide later is fine.",
        )
    if data.get("mode") != "paper":
        return _check(
            "platform", "Platform", "fail",
            "Mode is not paper. This desk never runs real money.",
            "I can set mode back to paper if you say yes. Nothing else in the file changes.",
            safe_fix="force-paper-mode",
        )
    chosen = data.get("chosen_at")
    if chosen is not None and not isinstance(chosen, str):
        return _check(
            "platform", "Platform", "fail",
            "chosen_at must be empty or a time string.",
            "Set chosen_at to the time you picked the platform, in your local time, or leave it empty.",
        )
    return _check("platform", "Platform", "pass", "config/platform.json is valid and paper-only.")


def _check_login(root):
    data, problem = _platform_data(root)
    path = Path(root) / "config" / "demo_connection.json"
    dirty, status = _status_dirty(path, DEMO_KEYS)
    if dirty:
        return _check(
            "demo-login", "Demo login", "fail",
            "The demo connection file has something other than a connected flag.",
            "I can rewrite it to a connected true or false flag if you say yes. The login itself is never stored there.",
            safe_fix="strip-demo-connection",
        )
    platform = data.get("platform") if isinstance(data, dict) else None
    if problem or platform not in NEEDS_LOGIN:
        if status and status.get("connected") is True:
            return _check(
                "demo-login", "Demo login", "pass",
                "Demo login test call succeeded. No account data is shown.",
            )
        return _check(
            "demo-login", "Demo login", "pass",
            "No demo login is needed for this platform.",
        )
    if not path.is_file() or not status or status.get("connected") is not True:
        return _check(
            "demo-login", "Demo login", "fail",
            "The demo login is not connected.",
            "Connect your own demo or paper account from the menu. Use the platform's official login or API. "
            "Credentials stay in secure storage, never in chat, the repo, the pool, or a file. "
            "Ask for step-by-step instructions if you would rather do it yourself.",
        )
    return _check(
        "demo-login", "Demo login", "pass",
        "Demo login test call succeeded. No account data is shown.",
    )


def _check_pool(root):
    old = _use_root(root)
    try:
        problems = check_record_lines(root) + duplicate_ids(root) + content_duplicates(root)
        counts = pool.counts()
    finally:
        _restore_root(old)
    hard, soft = _split_record_problems(problems)
    rendered = ", ".join(f"{name} {count}" for name, count in sorted(counts.items()))
    if hard:
        return _check(
            "pool", "Local pool", "fail",
            "The local pool did not validate. " + " ".join(hard[:8]),
            "Fix the record named in the detail, or ask Book to reject it. Do not put account data in the pool.",
        )
    if soft:
        item = _check(
            "pool", "Local pool", "warn",
            "The local pool counts check out (" + rendered + "), but a stored backtest has no variant count.",
            "Add a new record that includes the variant count and points at the old id with payload.supersedes. Do not edit the old line.",
        )
        item["items"] = soft[:20]
        return item
    return _check("pool", "Local pool", "pass", f"The local pool validates ({rendered}).")


def _parse_et(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _check_pending(root, now):
    pending = Path(root) / "pending"
    files = sorted(path for path in pending.glob("*.json") if path.is_file()) if pending.is_dir() else []
    if not files:
        return _check("pending-queue", "Pending queue", "pass", "The pending queue is empty.")
    stuck = []
    fresh = 0
    for path in files:
        try:
            data = _read_json(path)
        except json.JSONDecodeError:
            stuck.append(path.name)
            continue
        stamp = _parse_et(data.get("submitted_at_et")) if isinstance(data, dict) else None
        if stamp is None and isinstance(data, dict):
            record = data.get("record") if isinstance(data.get("record"), dict) else {}
            stamp = _parse_et(record.get("timestamp_et"))
        if stamp is None or now - stamp > STUCK_AFTER:
            stuck.append(path.name)
        else:
            fresh += 1
    if stuck:
        return _check(
            "pending-queue", "Pending queue", "fail",
            f"{len(stuck)} submission(s) look stuck.",
            "Run pool.py intake, then ask Book to approve or reject each one. "
            "Server can promote the approved rows locally. Nothing goes upstream unless data sharing is on and you have said yes.",
        )
    return _check(
        "pending-queue", "Pending queue", "pass",
        f"The pending queue has {fresh} recent submission(s).",
    )


def _check_telegram(root):
    path = Path(root) / "config" / "telegram_status.json"
    dirty, status = _status_dirty(path, TELEGRAM_KEYS)
    if dirty:
        return _check(
            "telegram", "Telegram", "fail",
            "The Telegram status file has something other than connected and test_ok.",
            "I can rewrite it to those flags if you say yes. The bot token and chat id never go in that file.",
            safe_fix="strip-telegram-status",
        )
    if not path.is_file() or not status or status.get("connected") is not True:
        return _check(
            "telegram", "Telegram", "pass",
            "Telegram is not connected, so the alert test was skipped.",
        )
    if status.get("test_ok") is True:
        return _check(
            "telegram", "Telegram", "pass",
            "Telegram alert test succeeded. Alerts are trade activity only.",
        )
    return _check(
        "telegram", "Telegram", "fail",
        "Telegram is connected, but the alert test has not succeeded.",
        "Send one test alert from secure storage, then mark test_ok. The message should be trade activity only, never account details.",
    )


def _check_logs(root, logs):
    texts = list(logs or [])
    log_dir = Path(root) / "logs"
    if log_dir.is_dir():
        for path in sorted(log_dir.rglob("*")):
            if path.is_file():
                try:
                    texts.append(path.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
    if not texts:
        return _check("secrets-in-logs", "Local logs", "pass", "There are no local logs to scan.")
    for text in texts:
        if privacy_reasons(text):
            return _check(
                "secrets-in-logs", "Local logs", "fail",
                "Local logs contain secrets or account data.",
                "Delete or redact the log, then run the health check again. Do not paste the log into chat.",
            )
    return _check("secrets-in-logs", "Local logs", "pass", "Local logs are clear of secrets and account data.")


def _check_stopped(state):
    desk = state.get("desk") or "stopped"
    if desk != "stopped":
        return _check(
            "stopped-desk", "Stopped desk", "pass",
            "The desk is marked running, so this idle check does not apply.",
        )
    bots = state.get("bots") or {}
    running = [name for name, actual in bots.items() if actual not in ("idle", "stopped", None)]
    routines = state.get("routines") or []
    if running or routines:
        return _check(
            "stopped-desk", "Stopped desk", "fail",
            "Something is still running while the desk is supposed to be stopped.",
            "Say stop, pause, or halt. That stops every bot and every routine immediately.",
        )
    return _check("stopped-desk", "Stopped desk", "pass", "Nothing is running.")


def find_known_fixes(root, code=None, symptom=None):
    """Bug records whose health-check code or symptom matches. Fixed rows come first."""
    path = Path(root) / "bugs" / "records.jsonl"
    if not path.is_file():
        return []
    matches = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        code_ok = code and str(payload.get("health_check_code") or "").lower() == str(code).lower()
        text = str(payload.get("symptom") or "")
        symptom_ok = symptom and symptom.lower() in text.lower()
        if not code_ok and not symptom_ok:
            continue
        steps = payload.get("fix_steps") or []
        if isinstance(steps, str):
            steps = [steps]
        matches.append({
            "id": rec.get("id"),
            "status": payload.get("status"),
            "symptom": payload.get("symptom") or "",
            "fix_steps": [step for step in steps if isinstance(step, str)],
            "root_cause": payload.get("root_cause") or "",
            "fixed_in": payload.get("fixed_in") or "",
            "health_check_code": payload.get("health_check_code") or "",
        })
    matches.reverse()
    rank = {"fixed": 0, "workaround": 1, "open": 2}
    matches.sort(key=lambda item: rank.get(item["status"], 9))
    return matches


def _attach_known_fixes(root, checks):
    for item in checks:
        if item["status"] == "pass":
            continue
        found = find_known_fixes(root, code=item["code"])
        if found:
            item["known_fix"] = found[0]
    return checks


def _finish(checks, root, sharing=None):
    checks = _attach_known_fixes(root, checks)
    status = _overall(checks)
    result = {
        "ok": status != "fail",
        "status": status,
        "checks": checks,
        "summary": "",
        "sharing": sharing,
    }
    result["summary"] = plain_summary(result)
    return result


def plain_summary(result):
    lines = [f"Health check: {result['status']}."]
    for item in result.get("checks") or []:
        line = f"{item['name']}: {item['status']}. {item['detail']}"
        if item["status"] != "pass" and item.get("fix"):
            line += " Suggested fix: " + item["fix"]
        known = item.get("known_fix")
        if known and known.get("fix_steps"):
            line += " Known fix (" + str(known.get("status") or "recorded") + "): " + "; ".join(known["fix_steps"])
        lines.append(line)
    lines.append("Say the word if you want me to apply a safe fix, or to send a report to the dev through the pool.")
    return "\n".join(lines)


def run_desk_health(root, desk_state=None, logs=None, now=None):
    root = Path(root)
    now = now or datetime.now(NY)
    state = _load_desk_state(root, desk_state)
    checks = [
        _check_bots(root, state),
        _check_platform(root),
        _check_login(root),
        _check_pool(root),
        _check_pending(root, now),
        _check_telegram(root),
        _check_logs(root, logs),
        _check_stopped(state),
    ]
    sharing = None
    try:
        sharing = load_settings(root)
    except (ValueError, json.JSONDecodeError):
        checks.append(_check(
            "settings", "Data sharing", "fail",
            "Data sharing settings could not be read, so nothing will be sent upstream.",
            "I can reset both switches to off if you say yes. You can turn them on again from the menu.",
            safe_fix="reset-sharing-off",
        ))
    return _finish(checks, root, sharing)


def run_repo_health(root):
    root = Path(root)
    old = _use_root(root)
    try:
        record_problems = check_record_lines(root) + content_duplicates(root)
        record_hard, record_soft = _split_record_problems(record_problems)
        id_problems = duplicate_ids(root)
        secret_problems = scan_repo(root)
        lint_problems = lint_workflows(root)
    finally:
        _restore_root(old)
    checks = []
    if record_hard:
        checks.append(_check(
            "records", "Pool records", "fail",
            "A pool record failed the schema or Book's checklist.",
            "Read the record id in the log, fix that record in a new append-only line, and remove any account data.",
        ))
        checks[-1]["items"] = record_hard[:20]
    elif record_soft:
        checks.append(_check(
            "records", "Pool records", "warn",
            "A stored backtest has out-of-sample results but no variant count.",
            "Add a new record that includes the variant count and payload.supersedes the old id. Do not edit the old line.",
        ))
        checks[-1]["items"] = record_soft[:20]
    else:
        checks.append(_check("records", "Pool records", "pass", "Every records.jsonl line passes the schema and Book's checklist."))
    if id_problems:
        checks.append(_check(
            "duplicate-ids", "Duplicate ids", "fail",
            "The pool has a repeated record id.",
            "Add a correction record with a new id and payload.supersedes set to the old id. Do not edit the old line.",
        ))
        checks[-1]["items"] = id_problems[:20]
    else:
        checks.append(_check("duplicate-ids", "Duplicate ids", "pass", "Record ids are unique."))
    if secret_problems:
        checks.append(_check(
            "secret-scan", "Secret and personal-data scan", "fail",
            "The secret and personal-data scan found a problem. The value is not shown.",
            "Remove the secret or account data from the named file and run the scan again. Do not paste it into chat or an issue.",
        ))
        checks[-1]["items"] = secret_problems[:20]
    else:
        checks.append(_check(
            "secret-scan", "Secret and personal-data scan", "pass",
            "The secret and personal-data scan is clear.",
        ))
    if lint_problems:
        checks.append(_check(
            "workflows", "Workflow lint", "fail",
            "A workflow file is missing a required piece.",
            "Give every workflow a name, an on block, jobs, and runs-on. health.yml needs push, pull request, workflow dispatch, and a daily schedule.",
        ))
        checks[-1]["items"] = lint_problems[:20]
    else:
        checks.append(_check("workflows", "Workflow lint", "pass", "Workflow files have the pieces this desk expects."))
    try:
        sharing = load_settings(root)
    except (ValueError, json.JSONDecodeError):
        sharing = None
        checks.append(_check(
            "settings", "Data sharing", "fail",
            "config/user_settings.json is not valid.",
            "Reset share_data and share_bugs to false until a person chooses.",
            safe_fix="reset-sharing-off",
        ))
    return _finish(checks, root, sharing)


def _offered_fixes(result):
    return {item["safe_fix"] for item in result.get("checks") or [] if item.get("safe_fix")}


def _connected_flag(path):
    if not path.is_file():
        return False
    try:
        data = _read_json(path)
    except json.JSONDecodeError:
        return False
    return bool(isinstance(data, dict) and data.get("connected") is True)


def apply_safe_fixes(root, ids, desk_state=None, logs=None, now=None):
    """Apply only fixes the current health check offered. Never prints secret values."""
    root = Path(root)
    current = run_desk_health(root, desk_state=desk_state, logs=logs, now=now)
    offered = _offered_fixes(current)
    applied = []
    refused = []
    for ident in ids:
        if ident not in offered:
            refused.append(ident)
            continue
        if ident == "force-paper-mode":
            path = root / "config" / "platform.json"
            data = _read_json(path)
            data["mode"] = "paper"
            _write_json(path, {key: data.get(key) for key in ("platform", "mode", "chosen_at")})
        elif ident == "write-platform-default":
            _write_json(root / "config" / "platform.json", {
                "platform": "undecided", "mode": "paper", "chosen_at": None,
            })
        elif ident == "strip-demo-connection":
            path = root / "config" / "demo_connection.json"
            _write_json(path, {"connected": _connected_flag(path)})
        elif ident == "strip-telegram-status":
            path = root / "config" / "telegram_status.json"
            connected = _connected_flag(path)
            test_ok = False
            if path.is_file():
                try:
                    data = _read_json(path)
                    test_ok = bool(isinstance(data, dict) and data.get("test_ok") is True and connected)
                except json.JSONDecodeError:
                    test_ok = False
            _write_json(path, {"connected": connected, "test_ok": test_ok})
        elif ident == "reset-sharing-off":
            _write_json(root / "config" / "user_settings.json", {
                "share_data": False, "share_bugs": False, "upstream_confirmed": False,
            })
        else:
            refused.append(ident)
            continue
        applied.append(ident)
    follow = run_desk_health(root, desk_state=desk_state, logs=logs, now=now)
    return {"applied": applied, "refused": refused, "health": follow}


def mark_demo_connected(root, connected):
    """Store only whether the demo test call worked. No credential arguments exist."""
    _write_json(Path(root) / "config" / "demo_connection.json", {"connected": bool(connected)})


def mark_telegram(root, connected, test_ok):
    """Store only Telegram flags. The token and chat id stay in secure storage."""
    connected = bool(connected)
    _write_json(Path(root) / "config" / "telegram_status.json", {
        "connected": connected,
        "test_ok": bool(test_ok) and connected,
    })


def draft_bug_issue(result):
    """A bug-report draft the user reviews before it is filed. No account values."""
    failed = [item for item in result.get("checks") or [] if item["status"] == "fail"]
    happened = " ".join(item["detail"] for item in failed) or "The health check reported a problem."
    expected = "The health check should pass, with every bot idle or running as expected and no account data stored."
    steps = "Run python3 tools/health_check.py --mode desk"
    output = result.get("summary") or happened
    platform = "undecided"
    return "\n".join([
        "Draft bug report. Please review it before anything is filed.",
        "Do not add credentials or account data.",
        "You can also write gbtnsupport@gmail.com instead of filing this.",
        "",
        "What happened: " + happened,
        "Expected: " + expected,
        "Steps: " + steps,
        "Platform: " + platform,
        "Health-check output:",
        output,
    ])


def _bug_id(record):
    body = {key: value for key, value in record.items() if key != "id"}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    return "bug" + digest[:20]


def _parse_fix_block(block):
    fields = {}
    steps = []
    in_steps = False
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("fix_steps:"):
            in_steps = True
            rest = stripped.split(":", 1)[1].strip()
            if rest:
                steps.append(rest)
            continue
        if in_steps and stripped.startswith("- "):
            steps.append(stripped[2:].strip())
            continue
        in_steps = False
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            fields[key.strip().lower().replace(" ", "_").replace("-", "_")] = value.strip()
    return fields, steps


def bug_record_from_text(text, timestamp_et):
    """Build a bug_report record from a fenced JSON object or a ## Fix section."""
    if not text or not str(text).strip():
        return None
    candidate = None
    try:
        found = extract_json(text)
    except ValueError:
        found = None
    if isinstance(found, dict) and found.get("type") == "bug_report":
        candidate = json.loads(json.dumps(found))
        candidate.setdefault("timestamp_et", timestamp_et)
        candidate.setdefault("label", "paper")
        candidate.setdefault("source_bot", "health-check")
        candidate.setdefault("symbol", "DESK")
        if not candidate.get("id"):
            candidate["id"] = _bug_id(candidate)
        return candidate
    match = re.search(r"(?ms)^## Fix\s*\n(.*?)(?=^## |\Z)", text)
    if not match:
        return None
    fields, steps = _parse_fix_block(match.group(1))
    if not fields.get("symptom") or not fields.get("health_check_code"):
        return None
    payload = {
        "symptom": fields.get("symptom", ""),
        "component": fields.get("component") or "pipeline",
        "platform": fields.get("platform") or "undecided",
        "health_check_code": fields.get("health_check_code", ""),
        "root_cause": fields.get("root_cause", ""),
        "fix_steps": steps or ([fields["fix_steps"]] if fields.get("fix_steps") else []),
        "status": fields.get("status") or "fixed",
        "fixed_in": fields.get("fixed_in", ""),
        "supersedes": fields.get("supersedes", ""),
    }
    if payload["status"] not in ("open", "fixed", "workaround"):
        payload["status"] = "fixed"
    record = {
        "timestamp_et": timestamp_et,
        "source_bot": "health-check",
        "type": "bug_report",
        "symbol": (payload["component"] or "DESK")[:32] or "DESK",
        "label": "paper",
        "payload": payload,
    }
    record["id"] = _bug_id(record)
    return record


def prepare_upstream(root, kind, record=None):
    """Gate a public submission on the sharing switch and the user's first OK."""
    from tools.sharing import upstream_decision
    decision = upstream_decision(root, kind)
    checked = record
    if record is not None:
        result = validate_record(record, pool_root=None)
        if not result["ok"]:
            return {
                "allowed": False,
                "reason": "rejected",
                "reasons": result["reasons"],
                "record": None,
                "settings": decision.get("settings"),
            }
        checked = result["record"]
    if decision["reason"] == "needs_confirmation":
        decision["ask"] = "Share this with the network pool? It goes through the automatic filter."
    decision["record"] = checked if decision["allowed"] else None
    return decision


def accept_bug_record(root, record):
    """Validate and append one bug record. Refuses account data and other checklist failures."""
    root = Path(root)
    old = _use_root(root)
    try:
        result = validate_record(record, root)
        if not result["ok"]:
            return {"ok": False, "reasons": result["reasons"], "id": None}
        try:
            stored = pool.append_checked(result["record"])
        except ValueError as exc:
            return {"ok": False, "reasons": [str(exc)], "id": None}
        return {"ok": True, "reasons": [], "id": stored["id"]}
    finally:
        _restore_root(old)


BUG_COMPONENTS = {
    "bots": "coordinator",
    "platform": "platform",
    "demo-login": "login",
    "pool": "server",
    "pending-queue": "server",
    "telegram": "telegram",
    "secrets-in-logs": "logs",
    "stopped-desk": "coordinator",
    "settings": "sharing",
}


def bug_record_from_health(root, result, timestamp_et=None):
    """Turn the first failing (or warning) check into a bug_report record for the pool.

    The record carries symptom, cause, fix steps, and status only. No logs,
    no account values, and no email address of the user.
    """
    checks = result.get("checks") or []
    bad = [item for item in checks if item.get("status") == "fail"]
    bad = bad or [item for item in checks if item.get("status") == "warn"]
    if not bad:
        return None
    item = bad[0]
    known = item.get("known_fix") or {}
    steps = list(known.get("fix_steps") or [])
    if not steps and item.get("fix"):
        steps = [item["fix"]]
    if not steps:
        steps = ["Run python3 tools/health_check.py --mode desk and follow the suggested fix"]
    platform_data, _ = _platform_data(root)
    platform = (platform_data or {}).get("platform") or "undecided"
    if not isinstance(platform, str):
        platform = "undecided"
    timestamp_et = timestamp_et or datetime.now(NY).isoformat(timespec="seconds")
    record = {
        "timestamp_et": timestamp_et,
        "source_bot": "health-check",
        "type": "bug_report",
        "symbol": "DESK",
        "label": "paper",
        "payload": {
            "symptom": f"{item.get('name') or item.get('code')}: {item.get('detail') or 'health check failed'}",
            "component": BUG_COMPONENTS.get(item.get("code"), "pipeline"),
            "platform": platform,
            "health_check_code": str(item.get("code") or "unknown"),
            "root_cause": str(known.get("root_cause") or "Not known yet. Reported from the desk health check."),
            "fix_steps": [str(step) for step in steps],
            "status": "open",
            "fixed_in": "",
            "supersedes": "",
        },
    }
    record["id"] = _bug_id(record)
    return record


def send_report_to_dev(root, result, timestamp_et=None):
    """Plan the health check's 'send report to dev' step.

    Never sends or drafts an email, and never uses the user's email account.
    Sharing on: the report becomes a bug_report record that goes through the
    pool's Submit bug fix issue or a records-only pull request, so the
    automatic trading-data-only filter applies. Sharing off: it stays local.
    """
    root = Path(root)
    contact = "You can also write to " + SUPPORT_EMAIL + " yourself if you like."
    base = {"email_sent": False, "uses_user_email": False, "support_contact": SUPPORT_EMAIL}
    record = bug_record_from_health(root, result, timestamp_et)
    if record is None:
        return dict(base, route="none", record=None, allowed=False,
                    message="The health check passed, so there is nothing to report.",
                    options=["Back to main menu"])
    try:
        settings = load_settings(root)
    except (ValueError, json.JSONDecodeError):
        settings = {"share_data": False, "share_bugs": False, "upstream_confirmed": False}
    if not settings.get("share_bugs"):
        return dict(
            base, route="local", record=record, allowed=False, settings=settings,
            message=(
                "Data sharing is off, so this report stays on your machine and nothing is sent. "
                "I can turn sharing on so it goes to the pool through the automatic filter, "
                "or show you the dev's contact."
            ),
            options=["Turn data sharing on", "Show the dev's contact", "Back to main menu"],
        )
    plan = prepare_upstream(root, "bugs", record)
    plan.update(base)
    plan["route"] = "pool"
    plan["submit_via"] = "Submit bug fix issue (.github/ISSUE_TEMPLATE/bug-fix.yml) or a pull request that only appends to bugs/records.jsonl"
    if plan.get("reason") == "rejected":
        plan["message"] = "The automatic filter would reject this report, so nothing was sent. It stays local."
        plan["options"] = ["Show the dev's contact", "Back to main menu"]
    elif plan.get("reason") == "needs_confirmation":
        plan["record"] = record
        plan["message"] = (
            "This report goes to the pool as a bug record through the automatic filter (trading data only). "
            "Share it? " + contact
        )
        plan["options"] = ["Yes, share it", "No, keep it local", "Back to main menu"]
    else:
        plan["message"] = "Filing this as a bug record in the pool. The automatic filter accepts or rejects it. " + contact
        plan["options"] = ["Back to main menu"]
    return plan


def render_health_issue(result):
    lines = [
        "The repo health check failed. This note has no credentials and no account data.",
        "",
        result.get("summary") or "Health check failed.",
        "",
        "If you fix it, add a ## Fix section (symptom, component, platform, health_check_code, root_cause, fixed_in, and fix_steps) or a fenced bug_report JSON object. The next green run records that fix in bugs/records.jsonl.",
    ]
    for item in result.get("checks") or []:
        for extra in item.get("items") or []:
            lines.append("- " + extra)
    return "\n".join(lines) + "\n"


def plan_health_issue(result, issue, timestamp_et):
    """Decide whether to open, update, or close the single health issue."""
    failed = result.get("status") == "fail"
    body = render_health_issue(result)
    if failed and not issue:
        return {"action": "open", "title": "Health check failed", "body": body, "comment": None, "bug": None}
    if failed and issue:
        return {"action": "comment", "title": None, "body": None, "comment": body, "bug": None}
    if not failed and issue:
        text = (issue.get("body") or "") + "\n" + "\n".join(issue.get("comments") or [])
        bug = bug_record_from_text(text, timestamp_et)
        return {
            "action": "close",
            "title": None,
            "body": None,
            "comment": "Health check is green again.",
            "bug": bug,
        }
    return {"action": "none", "title": None, "body": None, "comment": None, "bug": None}


def _gh(args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True)


def _open_health_issue():
    listed = _gh(["issue", "list", "--label", "health", "--state", "open", "--json", "number,title,body", "--limit", "20"])
    issues = json.loads(listed.stdout or "[]")
    if not issues:
        return None
    issues.sort(key=lambda item: item["number"])
    primary = issues[0]
    viewed = _gh(["issue", "view", str(primary["number"]), "--json", "comments"])
    payload = json.loads(viewed.stdout or "{}")
    primary["comments"] = [item.get("body") or "" for item in payload.get("comments") or []]
    primary["extras"] = [item["number"] for item in issues[1:]]
    return primary


def _ensure_health_label():
    listed = _gh(["label", "list", "--limit", "200", "--json", "name"])
    names = {item.get("name") for item in json.loads(listed.stdout or "[]")}
    if "health" not in names:
        _gh(["label", "create", "health", "--description", "Repo health check", "--color", "B60205"])


def _commit_bug_append(root, ident):
    subprocess.run(["git", "add", "--", "bugs/records.jsonl"], cwd=root, check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root)
    if diff.returncode == 0:
        return
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", f"Record health fix {ident}"], cwd=root, check=True)
    subprocess.run(["git", "push", "origin", "HEAD"], cwd=root, check=True)


def sync_health_issue(root, result):
    """Open, update, or close the single health issue. Append a bug record when a fix is present."""
    root = Path(root)
    issue = _open_health_issue()
    plan = plan_health_issue(result, issue, pool.now_et())
    _ensure_health_label()
    if plan["action"] == "open":
        _gh(["issue", "create", "--label", "health", "--title", plan["title"], "--body", plan["body"]])
    elif plan["action"] == "comment":
        _gh(["issue", "comment", str(issue["number"]), "--body", plan["comment"]])
    elif plan["action"] == "close":
        note = plan["comment"]
        bug = plan.get("bug")
        if bug:
            accepted = accept_bug_record(root, bug)
            if accepted["ok"]:
                _commit_bug_append(root, accepted["id"])
                note += " Recorded bug " + accepted["id"] + "."
            else:
                note += " Bug record was not added: " + "; ".join(accepted["reasons"])
        _gh(["issue", "close", str(issue["number"]), "--reason", "completed", "--comment", note])
        for extra in issue.get("extras") or []:
            _gh(["issue", "close", str(extra), "--reason", "completed", "--comment", "Closed in favor of the single health issue."])
    plan["synced"] = True
    return plan


def _emit(result, json_out):
    text = json.dumps(result, indent=2)
    print(text)
    if json_out:
        Path(json_out).write_text(text + "\n", encoding="utf-8")


def main(argv):
    parser = argparse.ArgumentParser(description="Run the desk or repo health check")
    parser.add_argument("--mode", choices=("desk", "repo"), default="desk")
    parser.add_argument("--pool", default=".")
    parser.add_argument("--json-out")
    parser.add_argument("--desk-state", help="JSON file with desk and bot states")
    parser.add_argument("--apply-safe-fixes", nargs="+", default=None)
    parser.add_argument("--sync-health-issue", metavar="HEALTH_JSON",
                        help="CI only (.github/workflows/health.yml). Uses gh and git push; refuses to run outside GitHub Actions.")
    parser.add_argument("--mark-demo-connected", choices=("true", "false"))
    parser.add_argument("--mark-telegram", nargs=2, metavar=("CONNECTED", "TEST_OK"))
    parser.add_argument("--report-to-dev", metavar="HEALTH_JSON",
                        help="Plan 'send report to dev' from a saved desk health result. Never emails.")
    args = parser.parse_args(argv)
    root = Path(args.pool)
    if args.mark_demo_connected is not None:
        mark_demo_connected(root, args.mark_demo_connected == "true")
    if args.mark_telegram is not None:
        mark_telegram(root, args.mark_telegram[0] == "true", args.mark_telegram[1] == "true")
    if args.sync_health_issue:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            print("--sync-health-issue only runs inside GitHub Actions. Nothing was posted.", file=sys.stderr)
            return 2
        result = json.loads(Path(args.sync_health_issue).read_text(encoding="utf-8"))
        plan = sync_health_issue(root, result)
        _emit({key: value for key, value in plan.items() if key != "bug"}, args.json_out)
        return 0
    if args.report_to_dev:
        result = json.loads(Path(args.report_to_dev).read_text(encoding="utf-8"))
        _emit(send_report_to_dev(root, result), args.json_out)
        return 0
    desk_state = _read_json(args.desk_state) if args.desk_state else None
    if args.apply_safe_fixes is not None:
        outcome = apply_safe_fixes(root, args.apply_safe_fixes, desk_state=desk_state)
        _emit(outcome, args.json_out)
        return 0 if outcome["health"]["status"] != "fail" else 1
    result = run_repo_health(root) if args.mode == "repo" else run_desk_health(root, desk_state=desk_state)
    _emit(result, args.json_out)
    return 0 if result["status"] != "fail" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
