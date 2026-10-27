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
VARIANT_KEYS = ("variant_count", "variants_tried", "n_variants")
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


def _variant_count(payload):
    for key in VARIANT_KEYS:
        if key not in payload:
            continue
        if key != "variant_count" and isinstance(payload[key], list):
            return len(payload[key])
        return _whole(payload[key])
    return None


def _has_oos(payload):
    return any(key in payload and payload[key] not in (None, "") for key in OOS_KEYS)


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


def _pii_reasons(rec):
    text = json.dumps(rec)
    reasons = []
    hits = pool.secret_hits(rec)
    if hits:
        reasons.append("secret or personal data: " + ", ".join(hits))
    if EMAIL_RE.search(text):
        reasons.append("personal data: email")
    if PHONE_RE.search(text):
        reasons.append("personal data: phone number")
    return reasons


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
    if old and new.startswith(old):
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
    text = json.dumps(result)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    return int(result["code"])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
