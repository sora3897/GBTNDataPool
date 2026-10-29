#!/usr/bin/env python3
"""Book's checklist as code, for the automatic public filter.

Stdlib only. Exit 0 when the record or diff passes, 1 when it fails,
2 when a pull request touches anything other than */records.jsonl.

A passing record may carry payload["needs-book-review"] when profit
factor is over 5 or the variant count is over 50. Those still pass.
"""
import json
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

NY = ZoneInfo("America/New_York")
MAX_RECORD_BYTES = pool.MAX_RECORD_BYTES
ET_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?-0[45]:00$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$")
RECORDS_PATH = re.compile(r"^[^/]+/records\.jsonl$")
LABELS = ("backtest", "paper", "live-observation")
OOS_KEYS = ("out_of_sample", "oos", "full_OOS")
VARIANT_KEYS = ("variant_count", "variants_tried", "n_variants", "n_candidates")
PNL_KEYS = ("pnl", "total_pnl", "net_pnl")
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s.-])?(?:\(\d{3}\)[\s.-]?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?!\w)"
)
CLOCK_SKEW = timedelta(seconds=120)
CODE_OK = 0
CODE_FAIL = 1
CODE_MAINTAINER = 2


def extract_json(text):
    """Pull the first JSON object out of an issue form body."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("no JSON record found")
    errors = []
    for block in re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, re.I):
        try:
            value = json.loads(block.strip())
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
            continue
        if isinstance(value, dict):
            return value
    idx = text.find("{")
    if idx >= 0:
        try:
            value, _ = json.JSONDecoder().raw_decode(text[idx:])
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
        else:
            if isinstance(value, dict):
                return value
    raise ValueError(errors[0] if errors else "no JSON record found")


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _whole(value):
    number = _num(value)
    if number is None or number < 0 or not number.is_integer():
        return None
    return int(number)


def _line(record):
    return json.dumps(record, sort_keys=True) + "\n"


def _schema_reasons(rec):
    reasons = []
    for err in pool.validate(rec):
        if err.startswith("missing field: source_bot") or err.startswith("source_bot:"):
            continue
        if err.startswith("missing field: label") or err.startswith("label:"):
            continue
        if err.startswith("missing field: timestamp_et") or err.startswith("timestamp_et:"):
            continue
        reasons.append("schema: " + err)
    return reasons


def _timestamp_reasons(value):
    if not isinstance(value, str) or not ET_TS.fullmatch(value):
        return ["timestamp_et must be an ISO-8601 time with a US Eastern offset (-04:00 or -05:00)"]
    dt = datetime.fromisoformat(value)
    local = dt.astimezone(NY)
    if dt.utcoffset() != local.utcoffset():
        return ["timestamp_et offset does not match US Eastern for that moment"]
    if local > datetime.now(NY) + CLOCK_SKEW:
        return ["timestamp_et is in the future"]
    return []


def _trade_pnl(trade):
    if isinstance(trade, bool):
        raise TypeError
    if isinstance(trade, (int, float)):
        return float(trade)
    if isinstance(trade, dict):
        for key in ("pnl", "p_l", "profit", "net", "net_usd"):
            number = _num(trade.get(key)) if key in trade else None
            if number is not None:
                return number
    raise TypeError


def _numeric_reasons(payload):
    reasons = []
    borderline = False
    for key in ("pf", "profit_factor"):
        if key not in payload:
            continue
        number = _num(payload[key])
        if number is None or number < 0:
            reasons.append("profit factor must be >= 0")
        elif number > 5:
            borderline = True
    for key in ("drawdown", "max_drawdown"):
        if key not in payload:
            continue
        number = _num(payload[key])
        if number is None or number < 0 or number > 100:
            reasons.append("drawdown must be between 0 and 100")
    if "win_rate" in payload:
        number = _num(payload["win_rate"])
        if number is None or number < 0 or number > 1:
            reasons.append("win rate must be between 0 and 1")
    if "trades" in payload and not isinstance(payload["trades"], (int, float)):
        trades = payload["trades"]
        if not isinstance(trades, list):
            reasons.append("P&L is not consistent with trades")
        else:
            try:
                total = sum(_trade_pnl(trade) for trade in trades)
            except TypeError:
                reasons.append("P&L is not consistent with trades")
            else:
                stated = next((_num(payload[key]) for key in PNL_KEYS if key in payload), None)
                if stated is None or abs(stated - total) > 0.01:
                    reasons.append("P&L is not consistent with trades")
                elif all(key in payload for key in ("start_bank", "end_bank")):
                    start, end = _num(payload["start_bank"]), _num(payload["end_bank"])
                    if start is None or end is None or abs(start + stated - end) > 0.01:
                        reasons.append("P&L is not consistent with trades")
    elif "trades" in payload and isinstance(payload["trades"], bool):
        reasons.append("P&L is not consistent with trades")
    return reasons, borderline


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_dicts(item)


def _variant_count_in(obj):
    if not isinstance(obj, dict):
        return None
    for key in VARIANT_KEYS:
        if key not in obj:
            continue
        if key != "variant_count" and isinstance(obj[key], list):
            return len(obj[key])
        return _whole(obj[key])
    return None


def _variant_count(payload):
    found = [count for obj in _walk_dicts(payload) if (count := _variant_count_in(obj)) is not None]
    return max(found) if found else None


def _has_oos(payload):
    for obj in _walk_dicts(payload):
        if any(key in obj and obj[key] not in (None, "") for key in OOS_KEYS):
            return True
    return False


def _backtest_reasons(rec):
    if rec.get("type") != "backtest" and rec.get("label") != "backtest":
        return [], False
    payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
    reasons = []
    if not _has_oos(payload):
        reasons.append("backtest requires out-of-sample results")
    count = _variant_count(payload)
    if count is None:
        reasons.append("backtest requires a variant count")
    return reasons, bool(count is not None and count > 50)


SUPPORT_EMAIL = "gbtnsupport@gmail.com"
BUG_FIELDS = (
    "symptom", "component", "platform", "health_check_code", "root_cause",
    "fix_steps", "status", "fixed_in", "supersedes",
)
BUG_STATUSES = ("open", "fixed", "workaround")
_PERSON_KEYS = {
    "fullname", "firstname", "lastname", "realname", "givenname", "surname",
    "accountholder", "accountname", "customername", "clientname", "legalname",
    "personname", "tradername", "ownername",
}
_ACCOUNT_NUMBER_KEYS = {
    "accountnumber", "accountno", "acctnumber", "acctno", "loginnumber",
    "accountlogin", "login",
}
_BALANCE_KEYS = {
    "balance", "equity", "accountbalance", "accountequity", "acctbalance",
    "cashbalance", "accountvalue", "netliquidation", "netliq", "nlv",
    "buyingpower", "marginbalance", "availablebalance", "settledcash",
    "currentbalance",
}
_BROKER_ID_KEYS = {
    "brokeraccountid", "brokeraccount", "accountid", "ibaccount",
    "mt4account", "mt5account", "brokerid", "clearingaccount",
    "brokeraccountnumber", "broker", "brokername", "servername", "brokerserver",
    "tradeserver", "mt4server", "mt5server", "metaapiaccountid",
}
_NAME_VALUE = re.compile(r"^[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){1,2}$")
_NAME_PHRASE = re.compile(
    r"(?i)\b(my name is|full name|real name|account holder|account name|legal name|client name|customer name)\b"
)
_ACCOUNT_NUM_PHRASE = re.compile(
    r"(?i)\b(?:account|acct|login)\s*(?:number|no\.?|num|#)\s*[:=#]?\s*[A-Za-z0-9][A-Za-z0-9-]{4,}"
)
_BALANCE_PHRASE = re.compile(
    r"(?i)\b(?:account\s+(?:balance|equity|value)|net liquidation|buying power|margin balance)\b"
)
_BROKER_ID_PHRASE = re.compile(
    r"(?i)\b(?:broker\s+account(?:\s+id)?|account\s+id|ib\s+account)\s*[:=#]?\s*[A-Za-z0-9][A-Za-z0-9-]{3,}"
)
_IB_ID = re.compile(r"\bDU\d{6,8}\b|\bU\d{7,8}\b")
# A MetaAPI account id (a UUID) written next to "metaapi" or "account" (also "accountId", "metaapi_account").
_METAAPI_ID = re.compile(r"(?i)\b(?:metaapi|account)[a-z_]*\b[^\n]{0,24}?\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
# MT4/MT5 trade server names name the broker, for example "BrokerName-Demo" or "Broker-Live3".
_MT_SERVER = re.compile(r"(?<![\w.-])[A-Z][A-Za-z]{2,30}[A-Za-z0-9.]{0,30}-(?:Demo|Live|Real)\d{0,3}\b")
# Free text only (issue bodies, logs): account or login numbers, balances, and passwords written in prose.
_PROSE_ACCOUNT = re.compile(
    r"(?i)\b(?:account|acct|login)(?:\s+(?:number|no\.?|num|id))?\s*(?:is|was|:|=|#)?\s*\d{5,12}\b"
)
_PROSE_BALANCE = re.compile(
    r"(?i)(?<!paper\s)(?<!cash\s)(?<!sim\s)\bbalance\b\s*(?:is|was|of|at|:|=)?\s*(?:[$\u20ac\u00a3]|usd\s*)?\s*\d[\d,]{2,}(?:\.\d+)?"
)
_PROSE_PASSWORD = re.compile(r"(?i)\bpass(?:word|wd)\b\s+(?:is\s+|was\s+)?[^\s,.;]{6,}")


def _norm_key(key):
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _dedupe(reasons):
    found = []
    for reason in reasons:
        if reason not in found:
            found.append(reason)
    return found


def _key_privacy_reasons(value):
    reasons = []

    def walk(obj):
        if isinstance(obj, dict):
            for key, item in obj.items():
                norm = _norm_key(key)
                if norm in _PERSON_KEYS and isinstance(item, str) and item.strip():
                    reasons.append("personal data: name")
                elif norm == "name" and isinstance(item, str) and _NAME_VALUE.match(item.strip()):
                    reasons.append("personal data: name")
                elif norm in _ACCOUNT_NUMBER_KEYS and item not in (None, ""):
                    reasons.append("account data: account number")
                elif norm in _BALANCE_KEYS and item not in (None, ""):
                    reasons.append("account data: balance or equity")
                elif norm in _BROKER_ID_KEYS and item not in (None, ""):
                    reasons.append("account data: broker account id")
                walk(item)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(value)
    return reasons


def _all_keys(obj):
    if isinstance(obj, dict):
        return [str(k) for k in obj] + [k for v in obj.values() for k in _all_keys(v)]
    if isinstance(obj, list):
        return [k for v in obj for k in _all_keys(v)]
    return []


def privacy_reasons(obj):
    """Reasons for secrets, account data, or personal data. Never includes the values.

    Every check runs on the raw text and on normalized forms of it (Unicode
    look-alikes and zero-width characters removed, spaced-out characters joined,
    base64 decoded), on each string value and each key of a record.
    """
    from tools import pii
    if isinstance(obj, str):
        hits = pool.secret_hits({"log": obj})
        text = obj
        key_reasons = []
        prose = [obj]
    else:
        hits = pool.secret_hits(obj)
        text = json.dumps(obj)
        key_reasons = _key_privacy_reasons(obj) + pii.key_reasons(obj)
        prose = pool._strings(obj) + _all_keys(obj)
    texts = [text] + prose
    forms = [v.replace(SUPPORT_EMAIL, "") for t in texts if isinstance(t, str) for v in pii.variants(t)]
    prose_forms = [v.replace(SUPPORT_EMAIL, "") for t in prose if isinstance(t, str) for v in pii.variants(t)]
    hits = sorted(set(hits) | {name for v in forms[1:] for name in pool.find_secrets(v)}
                  | {"possible seed phrase" for v in prose_forms if pool._seed_like(v)})
    reasons = []
    if hits:
        reasons.append("secret or personal data: " + ", ".join(hits))
    reasons.extend(key_reasons)
    hit = lambda rx: any(rx.search(v) for v in forms)
    if hit(EMAIL_RE):
        reasons.append("personal data: email")
    if hit(PHONE_RE):
        reasons.append("personal data: phone number")
    if hit(_NAME_PHRASE):
        reasons.append("personal data: name")
    if hit(_ACCOUNT_NUM_PHRASE):
        reasons.append("account data: account number")
    if hit(_BALANCE_PHRASE):
        reasons.append("account data: balance or equity")
    if hit(_BROKER_ID_PHRASE) or hit(_IB_ID) or hit(_METAAPI_ID):
        reasons.append("account data: broker account id")
    if hit(_MT_SERVER):
        reasons.append("account data: broker server name")
    # Prose checks run on free text and on every string value inside a record
    # (a bug report's root_cause or a note is free text too).
    if any(_PROSE_ACCOUNT.search(s) for s in prose_forms):
        reasons.append("account data: account number")
    if any(_PROSE_BALANCE.search(s) for s in prose_forms):
        reasons.append("account data: balance or equity")
    if any(_PROSE_PASSWORD.search(s) for s in prose_forms):
        reasons.append("secret or personal data: password")
    reasons.extend(pii.text_reasons([t.replace(SUPPORT_EMAIL, "") for t in prose if isinstance(t, str)]))
    return _dedupe(reasons)


def _bug_reasons(rec):
    if rec.get("type") != "bug_report":
        return []
    payload = rec.get("payload")
    if not isinstance(payload, dict):
        return ["bug report payload is required"]
    reasons = []
    for key in BUG_FIELDS:
        if key not in payload:
            reasons.append(f"bug report missing {key}")
    status = payload.get("status")
    if "status" in payload and status not in BUG_STATUSES:
        reasons.append("bug report status must be open, fixed, or workaround")
    if status == "fixed" and not str(payload.get("fixed_in") or "").strip():
        reasons.append("bug report fixed_in is required when status is fixed")
    steps = payload.get("fix_steps")
    if "fix_steps" in payload and not isinstance(steps, (str, list)):
        reasons.append("bug report fix_steps must be text or a list")
    elif isinstance(steps, list) and any(not isinstance(step, str) for step in steps):
        reasons.append("bug report fix_steps must be text or a list")
    for key in ("symptom", "component", "platform", "health_check_code", "root_cause", "fixed_in", "supersedes"):
        if key in payload and payload[key] is not None and not isinstance(payload[key], str):
            reasons.append(f"bug report {key} must be text")
    if isinstance(payload.get("symptom"), str) and not payload["symptom"].strip():
        reasons.append("bug report symptom is required")
    if isinstance(payload.get("component"), str) and not payload["component"].strip():
        reasons.append("bug report component is required")
    if isinstance(payload.get("health_check_code"), str) and not payload["health_check_code"].strip():
        reasons.append("bug report health_check_code is required")
    return reasons


def _pii_reasons(rec):
    return privacy_reasons(rec)


def _remember(text, found):
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            found[pool.content_hash(rec)] = str(rec.get("id") or "")
    return found


def _load_hashes(pool_root, skip_paths=()):
    found = {}
    root = Path(pool_root)
    skipped = set(skip_paths)
    for folder in pool.FOLDERS.values():
        rel = f"{folder}/records.jsonl"
        if rel in skipped:
            continue
        path = root / rel
        if path.exists():
            _remember(path.read_text(encoding="utf-8"), found)
    return found


def validate_record(record, pool_root=None, hashes=None):
    """Validate one pool record. Returns ok, reasons, id, record, needs_book_review."""
    if not isinstance(record, dict):
        return {"ok": False, "code": CODE_FAIL, "reasons": ["record must be a JSON object"],
                "id": None, "record": None, "needs_book_review": False}
    rec = json.loads(json.dumps(record))
    if not isinstance(rec.get("id"), str) or not rec["id"].strip():
        rec["id"] = "r" + pool.content_hash(rec)[:16]
    reasons = []
    if not ID_RE.fullmatch(rec["id"]):
        reasons.append("schema: id: invalid")
    if not isinstance(rec.get("source_bot"), str) or not rec["source_bot"].strip():
        reasons.append("source_bot is required")
    if rec.get("label") not in LABELS:
        reasons.append("label must be backtest, paper, or live-observation")
    reasons.extend(_timestamp_reasons(rec.get("timestamp_et")))
    reasons.extend(_schema_reasons(rec))
    borderline = False
    payload = rec.get("payload")
    if isinstance(payload, dict):
        numeric, flag = _numeric_reasons(payload)
        reasons.extend(numeric)
        borderline = borderline or flag
        extra, flag = _backtest_reasons(rec)
        reasons.extend(extra)
        borderline = borderline or flag
        reasons.extend(_bug_reasons(rec))
        count = _variant_count(payload)
        if count is not None and count > 50:
            borderline = True
    reasons.extend(_pii_reasons(rec))
    if isinstance(payload, dict) and (borderline or payload.get("needs-book-review") is True):
        payload["needs-book-review"] = True
        borderline = True
    if len(_line(rec).encode("utf-8")) > MAX_RECORD_BYTES:
        reasons.append("record exceeds 50 KB")
    if not reasons and pool_root is not None:
        corpus = hashes if hashes is not None else _load_hashes(pool_root)
        digest = pool.content_hash(rec)
        prior = corpus.get(digest)
        if prior:
            reasons.append(f"duplicate of {prior}")
        else:
            corpus[digest] = rec["id"]
    # Drop duplicate schema complaints that repeat a dedicated reason.
    deduped = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    ok = not deduped
    return {
        "ok": ok,
        "code": CODE_OK if ok else CODE_FAIL,
        "reasons": deduped,
        "id": rec.get("id"),
        "record": rec if ok else None,
        "needs_book_review": bool(ok and borderline),
    }


def _records_from_append(old, new):
    if new == old:
        return None, "no records appended"
    if not old:
        suffix = new
    elif new.startswith(old):
        if old and not old.endswith("\n"):
            return None, "diff is not append-only"
        suffix = new[len(old):]
    elif old and not old.endswith("\n") and new.startswith(old + "\n"):
        suffix = new[len(old) + 1:]
    else:
        return None, "diff is not append-only"
    records = []
    for line in suffix.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            return None, "appended line is not JSON"
        if not isinstance(value, dict):
            return None, "appended line is not a JSON object"
        records.append(value)
    if not records:
        return None, "no records appended"
    return records, None


def _join(old, records):
    base = old
    if base and not base.endswith("\n"):
        base += "\n"
    return base + "".join(_line(rec) for rec in records)


def review_changes(changes, pool_root):
    """changes is a list of (path, old_text, new_text) for files that differ."""
    other = [path for path, _old, _new in changes if not RECORDS_PATH.fullmatch(path)]
    if other:
        return {
            "ok": False,
            "code": CODE_MAINTAINER,
            "reasons": ["PR touches files other than */records.jsonl and needs the maintainer"],
            "ids": [],
            "records": [],
            "files": [],
            "needs_book_review": False,
        }
    changed = [path for path, _old, _new in changes]
    hashes = _load_hashes(pool_root, skip_paths=changed)
    for path, old, _new in changes:
        if RECORDS_PATH.fullmatch(path):
            _remember(old, hashes)
    reasons = []
    records = []
    files = []
    ids = []
    borderline = False
    for path, old, new in changes:
        added, problem = _records_from_append(old, new)
        if problem:
            reasons.append(f"{path}: {problem}")
            continue
        accepted = []
        failed = False
        for rec in added:
            result = validate_record(rec, pool_root, hashes)
            if not result["ok"]:
                failed = True
                ident = result.get("id") or "?"
                reasons.extend(f"{ident}: {reason}" for reason in result["reasons"])
                continue
            accepted.append(result["record"])
            ids.append(result["id"])
            records.append(result["record"])
            borderline = borderline or result["needs_book_review"]
        if not failed and any(left != right for left, right in zip(added, accepted)):
            files.append({"path": path, "text": _join(old, accepted)})
    ok = not reasons
    return {
        "ok": ok,
        "code": CODE_OK if ok else CODE_FAIL,
        "reasons": reasons,
        "ids": ids if ok else [],
        "records": records if ok else [],
        "files": files if ok else [],
        "needs_book_review": bool(ok and borderline),
    }


def _git_text(rev, path):
    proc = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        check=False, capture_output=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.decode("utf-8")


def review_git_diff(base, head, pool_root):
    proc = subprocess.run(
        ["git", "diff", "--name-status", base, head],
        check=True, capture_output=True, text=True,
    )
    changes = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status, path = parts[0], parts[-1]
        if status.startswith("D"):
            old = _git_text(base, path)
            changes.append((path, old, ""))
            continue
        if status.startswith("R") or status.startswith("C"):
            # A rename is not an append to one records file.
            changes.append((path, "renamed", _git_text(head, path) + "\nnot-prefix"))
            continue
        old = _git_text(base, path) if not status.startswith("A") else ""
        new = _git_text(head, path)
        if old != new:
            changes.append((path, old, new))
    if not changes:
        return {
            "ok": False, "code": CODE_FAIL, "reasons": ["no records appended"],
            "ids": [], "records": [], "files": [], "needs_book_review": False,
        }
    return review_changes(changes, pool_root)


def main(argv):
    import argparse
    parser = argparse.ArgumentParser(description="Run Book's checklist")
    parser.add_argument("--record", help="Path to one JSON record")
    parser.add_argument("--issue-body", help="Path to an issue body")
    parser.add_argument("--diff", nargs=2, metavar=("BASE", "HEAD"), help="Git revisions to compare")
    parser.add_argument("--pool", default=".", help="Pool root used for the duplicate check")
    parser.add_argument("--json-out", help="Also write the result JSON to this path")
    args = parser.parse_args(argv)
    pool_root = Path(args.pool)
    try:
        if args.record:
            result = validate_record(json.loads(Path(args.record).read_text(encoding="utf-8")), pool_root)
        elif args.issue_body:
            result = validate_record(extract_json(Path(args.issue_body).read_text(encoding="utf-8")), pool_root)
        elif args.diff:
            result = review_git_diff(args.diff[0], args.diff[1], pool_root)
        else:
            parser.error("pass --record, --issue-body, or --diff")
            return CODE_FAIL
    except ValueError as exc:
        result = {"ok": False, "code": CODE_FAIL, "reasons": [str(exc)], "id": None,
                  "record": None, "needs_book_review": False}
    except OSError as exc:
        result = {"ok": False, "code": CODE_FAIL, "reasons": ["could not read the input file (" + (exc.strerror or "error") + ")"],
                  "id": None, "record": None, "needs_book_review": False}
    except subprocess.CalledProcessError:
        result = {"ok": False, "code": CODE_FAIL, "reasons": ["git diff failed; check the two revisions"],
                  "id": None, "record": None, "needs_book_review": False}
    text = json.dumps(result)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    return int(result["code"])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
