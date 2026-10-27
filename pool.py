#!/usr/bin/env python3
"""Shared local data pool for Alex's trading bots. Stdlib only. Append-only JSON Lines.

    from pool import add, query
    add(source_bot="futures_kb", type="backtest", symbol="ES", label="backtest", payload={...})
    query(type="backtest", source_bot="futures_kb")

CLI:  python3 pool.py add '<json>'    |  python3 pool.py query [key=value ...]  |  python3 pool.py count
      python3 pool.py append <record.json>                     -> records.jsonl (automatic filter only)
Approval queue (see CONTRIBUTING.md):
      python3 pool.py submit '<json>'                          -> pending/<submission_id>.json
      python3 pool.py intake                                   -> validate pending/, failures -> pending/rejected/
      python3 pool.py decide <submission_id> approve|reject '<reason>' [--reviewer Book]
      python3 pool.py promote                                  -> Book-approved -> records.jsonl via add()
Set NETWORK_POOL_ROOT to point at a different pool directory (used for tests).
"""
import hashlib, json, os, re, sys, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

FOLDERS = {"strategy": "strategies", "backtest": "backtests", "paper_trade": "paper_trades", "market_note": "market_notes"}
SCHEMA = json.loads((Path(__file__).resolve().parent / "schema.json").read_text())
MAX_RECORD_BYTES = 50 * 1024

def _bind_paths():
    """Resolve pool paths on each call so NETWORK_POOL_ROOT works for tests."""
    global ROOT, PENDING, REJECTED, ARCHIVE_OK, ARCHIVE_NO, DECISIONS
    ROOT = Path(os.environ.get("NETWORK_POOL_ROOT", Path(__file__).resolve().parent))
    PENDING = ROOT / "pending"
    REJECTED = PENDING / "rejected"
    ARCHIVE_OK = PENDING / "archive" / "approved"
    ARCHIVE_NO = PENDING / "archive" / "rejected"
    DECISIONS = ROOT / "review" / "decisions.jsonl"

_bind_paths()

def now_et():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds")
    except Exception:  # fallback: US DST rule (2nd Sun Mar 2:00 -> 1st Sun Nov 2:00)
        u = datetime.now(timezone.utc); y = u.year
        mar = datetime(y, 3, 8, 7, tzinfo=timezone.utc); mar += timedelta(days=(6 - mar.weekday()) % 7)
        nov = datetime(y, 11, 1, 6, tzinfo=timezone.utc); nov += timedelta(days=(6 - nov.weekday()) % 7)
        off = -4 if mar <= u < nov else -5
        return u.astimezone(timezone(timedelta(hours=off))).isoformat(timespec="seconds")

# ---- secret guard -------------------------------------------------------
SECRET_PATTERNS = [
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "PEM private key"),
    (r"\b0x[0-9a-fA-F]{64}\b", "hex private key (64 hex)"),
    (r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])", "raw 64-hex key"),
    (r"\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b", "WIF private key"),
    (r"\b(sk|pk|rk)[-_](live|test|proj|ant)?[-_]?[A-Za-z0-9]{16,}", "API secret key"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key"),
    (r"\bgh[pousr]_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"\bxox[abpr]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"\bAIza[0-9A-Za-z_-]{35}\b", "Google API key"),
    (r"(?i)\b(api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|private[_-]?key|password|passwd)\b\s*[\"']?\s*[:=]\s*[\"']?[^\s\"',}]{6,}", "credential assignment"),
    (r"(?i)\bmt5\b[^\n]{0,40}?\b\d{5,12}\b", "MT5 login number"),
    (r"(?i)\b(mt5[_ -]?)?(login|account)[_ -]?(id|number|no)?\b\s*[\"']?\s*[:=#]\s*[\"']?\d{5,12}\b", "broker login number"),
    (r"(?i)\b(seed[_ -]?phrase|mnemonic|recovery[_ -]?phrase)\b", "seed phrase keyword"),
]
SECRET_KEYS = re.compile(r"(?i)(private_?key|secret|api_?key|password|mnemonic|seed_?phrase|mt5_?login|wallet_?key)")

def find_secrets(text):
    return [name for pat, name in SECRET_PATTERNS if re.search(pat, text)]

def _strings(obj):
    if isinstance(obj, dict): return [s for v in obj.values() for s in _strings(v)]
    if isinstance(obj, list): return [s for v in obj for s in _strings(v)]
    return [obj] if isinstance(obj, str) else []

def _seed_like(s):  # a value that is exactly 12/15/18/21/24 bare lowercase words
    w = s.strip().split()
    return len(w) in (12, 15, 18, 21, 24) and all(re.fullmatch(r"[a-z]{3,8}", x) for x in w)

def _secret_keys(obj):
    if isinstance(obj, dict):
        return [k for k in obj if SECRET_KEYS.search(str(k))] + [x for v in obj.values() for x in _secret_keys(v)]
    if isinstance(obj, list):
        return [x for v in obj for x in _secret_keys(v)]
    return []

def secret_hits(obj):
    """Names of secret patterns found anywhere in obj (never the matched values)."""
    return sorted(set(find_secrets(json.dumps(obj)) + [f"secret-looking key '{k}'" for k in _secret_keys(obj)]
                      + ["possible seed phrase" for s in _strings(obj) if _seed_like(s)]))

# ---- validation (minimal JSON Schema subset for schema.json) -------------
_T = {"string": str, "object": dict, "array": list, "number": (int, float), "integer": int, "boolean": bool}

def validate(rec):
    errs = []
    if not isinstance(rec, dict): return ["record must be an object"]
    for k in SCHEMA["required"]:
        if k not in rec: errs.append(f"missing field: {k}")
    if not SCHEMA.get("additionalProperties", True):
        errs += [f"unknown field: {k}" for k in rec if k not in SCHEMA["properties"]]
    for k, spec in SCHEMA["properties"].items():
        if k not in rec: continue
        v = rec[k]
        if not isinstance(v, _T[spec["type"]]): errs.append(f"{k}: expected {spec['type']}"); continue
        if "enum" in spec and v not in spec["enum"]: errs.append(f"{k}: must be one of {spec['enum']}")
        if "minLength" in spec and len(v) < spec["minLength"]: errs.append(f"{k}: too short")
        if "pattern" in spec and not re.search(spec["pattern"], v): errs.append(f"{k}: does not match {spec['pattern']}")
    return errs

# ---- storage --------------------------------------------------------------
def content_hash(record):
    """Hash record content. id, timestamp, and the review flag do not count."""
    body = {k: v for k, v in record.items() if k not in ("id", "timestamp_et")}
    payload = body.get("payload")
    if isinstance(payload, dict) and "needs-book-review" in payload:
        payload = {k: v for k, v in payload.items() if k != "needs-book-review"}
        body["payload"] = payload
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _file(t):
    _bind_paths()
    return ROOT / FOLDERS[t] / "records.jsonl"

def _iter(folder=None):
    _bind_paths()
    for t, f in FOLDERS.items():
        if folder and folder not in (t, f): continue
        p = ROOT / f / "records.jsonl"
        if p.exists():
            for line in p.read_text().splitlines():
                if line.strip(): yield json.loads(line)

def add(record=None, **fields):
    """Validate, guard, de-dup and append one record. Returns the stored record. Raises ValueError."""
    _bind_paths()
    rec = dict(record or {}); rec.update(fields)
    rec.setdefault("id", uuid.uuid4().hex)
    rec.setdefault("timestamp_et", now_et())
    errs = validate(rec)
    if errs: raise ValueError("schema: " + "; ".join(errs))
    hits = secret_hits(rec["payload"])
    if hits: raise ValueError("secret guard: payload rejected (" + ", ".join(hits) + ")")
    if any(r.get("id") == rec["id"] for r in _iter()): raise ValueError(f"duplicate id: {rec['id']}")
    p = _file(rec["type"]); p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as fh:  # append only, never rewrite
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec

def append_checked(record):
    """Append one record the automatic filter already accepted.

    Idempotent when the same id is already stored with the same content.
    Refuses a second id with the same content, a reused id with different
    content, schema failures, secrets, and records over 50 KB.
    """
    _bind_paths()
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    rec = dict(record)
    errs = validate(rec)
    if errs:
        raise ValueError("schema: " + "; ".join(errs))
    hits = secret_hits(rec)
    if hits:
        raise ValueError("secret guard: record rejected (" + ", ".join(hits) + ")")
    line = json.dumps(rec, sort_keys=True) + "\n"
    if len(line.encode("utf-8")) > MAX_RECORD_BYTES:
        raise ValueError("record exceeds 50 KB")
    digest = content_hash(rec)
    for existing in _iter():
        if existing.get("id") == rec.get("id"):
            if content_hash(existing) == digest:
                return existing
            raise ValueError(f"duplicate id: {rec['id']}")
        if content_hash(existing) == digest:
            raise ValueError(f"duplicate of {existing.get('id')}")
    path = _file(rec["type"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:  # append only, never rewrite
        fh.write(line)
    return rec

def query(folder=None, **filters):
    """Exact-match filters on top-level fields; payload__key=value matches payload keys. folder='backtests' etc."""
    out = []
    for r in _iter(folder):
        ok = True
        for k, v in filters.items():
            got = r.get("payload", {}).get(k[9:]) if k.startswith("payload__") else r.get(k)
            if str(got) != str(v): ok = False; break
        if ok: out.append(r)
    return out

def counts():
    return {f: len(query(folder=f)) for f in FOLDERS.values()}

# ---- approval queue: submit -> intake -> decide -> promote ----------------
AUTHORIZED_REVIEWER = "Book"
VERDICTS = ("approve", "reject")
SID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
PENDING = ROOT / "pending"
REJECTED = PENDING / "rejected"
ARCHIVE_OK = PENDING / "archive" / "approved"
ARCHIVE_NO = PENDING / "archive" / "rejected"
DECISIONS = ROOT / "review" / "decisions.jsonl"

def _write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp"); tmp.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n"); os.replace(tmp, path)

def _reject(path, sid, reason, keep_file=True):
    """Move a pending file to pending/rejected/ with a <sid>.reason.json sidecar. keep_file=False (secret hit)
    deletes the submission instead, so only the reason (never the offending content) is stored."""
    _bind_paths()
    REJECTED.mkdir(parents=True, exist_ok=True)
    _write_json(REJECTED / f"{sid}.reason.json", {"submission_id": sid, "reason": reason, "rejected_at_et": now_et()})
    if keep_file: os.replace(path, REJECTED / path.name)
    else: path.unlink()
    return reason

def submit(record=None, **fields):
    """Queue one record for review. Secrets are refused before anything is written. Returns the submission_id."""
    _bind_paths()
    rec = dict(record or {}); rec.update(fields)
    hits = secret_hits(rec)
    if hits: raise ValueError("secret guard: submission refused, nothing written (" + ", ".join(hits) + ")")
    rec.setdefault("id", uuid.uuid4().hex)  # fixed now so promote can never double-append
    rec.setdefault("timestamp_et", now_et())
    sid = "sub_" + re.sub(r"\D", "", rec["timestamp_et"][:19]) + "_" + uuid.uuid4().hex[:8]
    _write_json(PENDING / f"{sid}.json", {"submission_id": sid, "submitted_at_et": now_et(), "status": "submitted", "record": rec})
    return sid

def _pending_files():
    _bind_paths()
    return sorted(p for p in PENDING.glob("*.json") if p.is_file()) if PENDING.exists() else []

def intake():
    """Validate every unvalidated pending/*.json with schema + secret guard. Returns {sid: 'valid' | reason}."""
    _bind_paths()
    out = {}
    for p in _pending_files():
        sid = p.stem if SID_RE.match(p.stem) else "bad_" + uuid.uuid4().hex[:8]
        raw = p.read_text(errors="replace")
        if find_secrets(raw): out[sid] = _reject(p, sid, "secret guard: " + ", ".join(find_secrets(raw)), keep_file=False); continue
        try: sub = json.loads(raw)
        except ValueError: out[sid] = _reject(p, sid, "invalid JSON"); continue
        if not isinstance(sub, dict) or not isinstance(sub.get("record"), dict):
            out[sid] = _reject(p, sid, "submission must be an object with a 'record' object"); continue
        if sub.get("status") == "valid": continue
        hits = secret_hits(sub)
        if hits: out[sid] = _reject(p, sid, "secret guard: " + ", ".join(hits), keep_file=False); continue
        if sub.get("submission_id") != sid: out[sid] = _reject(p, sid, "submission_id does not match file name"); continue
        errs = validate(sub["record"])
        if errs: out[sid] = _reject(p, sid, "schema: " + "; ".join(errs)); continue
        if any(r.get("id") == sub["record"]["id"] for r in _iter()): out[sid] = _reject(p, sid, f"duplicate id: {sub['record']['id']}"); continue
        sub.update(status="valid", validated_at_et=now_et()); _write_json(p, sub); out[sid] = "valid"
    return out

def decide(submission_id, verdict, reason, reviewer=AUTHORIZED_REVIEWER):
    """Append one decision line to review/decisions.jsonl (append only)."""
    _bind_paths()
    if verdict not in VERDICTS: raise ValueError(f"verdict must be one of {VERDICTS}")
    if not SID_RE.match(str(submission_id)) or not (PENDING / f"{submission_id}.json").is_file():
        raise ValueError(f"no such pending submission: {submission_id}")
    if not str(reason).strip(): raise ValueError("reason is required")
    if find_secrets(str(reason)): raise ValueError("secret guard: reason rejected")
    line = {"submission_id": submission_id, "verdict": verdict, "reason": str(reason), "reviewer": str(reviewer), "timestamp_et": now_et()}
    DECISIONS.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISIONS, "a") as fh: fh.write(json.dumps(line, sort_keys=True) + "\n")
    return line

def _latest_decisions():
    """Latest decision per submission from the authorized reviewer only; other reviewers' lines are ignored."""
    _bind_paths()
    latest = {}
    if DECISIONS.exists():
        for line in DECISIONS.read_text().splitlines():
            if not line.strip(): continue
            d = json.loads(line)
            if d.get("reviewer") == AUTHORIZED_REVIEWER and d.get("verdict") in VERDICTS: latest[d.get("submission_id")] = d
    return latest

def promote():
    """Book-approved valid submissions -> add() -> archive/approved; Book-rejected -> archive/rejected; else untouched.
    Idempotent: a record id already in the pool is never appended again."""
    _bind_paths()
    dec, out = _latest_decisions(), {}
    for p in _pending_files():
        try: sub = json.loads(p.read_text())
        except ValueError: continue
        sid = sub.get("submission_id")
        if sub.get("status") != "valid" or sid != p.stem or sid not in dec: continue  # run intake / await decision
        if dec[sid]["verdict"] == "reject":
            ARCHIVE_NO.mkdir(parents=True, exist_ok=True); os.replace(p, ARCHIVE_NO / p.name); out[sid] = "archived-rejected"; continue
        rec = sub["record"]
        if any(r.get("id") == rec.get("id") for r in _iter()): out[sid] = "already-in-pool"
        else:
            try: add(rec); out[sid] = "promoted"
            except ValueError as e: out[sid] = _reject(p, sid, f"promote failed: {e}"); continue
        ARCHIVE_OK.mkdir(parents=True, exist_ok=True); os.replace(p, ARCHIVE_OK / p.name)
    return out

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("add", "query", "count", "submit", "intake", "decide", "promote", "append"): print(__doc__); sys.exit(1)
    _bind_paths()
    try:
        if a[0] == "add": print(json.dumps(add(json.loads(a[1]))))
        elif a[0] == "append":
            if len(a) != 2: raise ValueError("usage: append <record.json>")
            print(json.dumps(append_checked(json.loads(Path(a[1]).read_text()))))
        elif a[0] == "count": print(json.dumps(counts(), indent=1))
        elif a[0] == "submit": print(submit(json.loads(a[1])))
        elif a[0] == "intake": print(json.dumps(intake(), indent=1))
        elif a[0] == "promote": print(json.dumps(promote(), indent=1))
        elif a[0] == "decide":
            rest = a[1:]; reviewer = AUTHORIZED_REVIEWER
            if "--reviewer" in rest:
                i = rest.index("--reviewer"); reviewer = rest[i + 1]; del rest[i:i + 2]
            if len(rest) != 3: raise ValueError("usage: decide <submission_id> approve|reject '<reason>' [--reviewer Book]")
            print(json.dumps(decide(rest[0], rest[1], rest[2], reviewer)))
        else:
            kw = dict(x.split("=", 1) for x in a[1:])
            for r in query(**kw): print(json.dumps(r))
    except (ValueError, IndexError) as e:
        print(f"REJECTED: {e}", file=sys.stderr); sys.exit(2)
