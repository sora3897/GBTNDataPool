#!/usr/bin/env python3
"""Shared local data pool for Alex's trading bots. Stdlib only. Append-only JSON Lines.

    from pool import add, query
    add(source_bot="futures_kb", type="backtest", symbol="ES", label="backtest", payload={...})
    query(type="backtest", source_bot="futures_kb")

CLI:  python3 pool.py add '<json>'    |  python3 pool.py query [key=value ...]  |  python3 pool.py count
Set NETWORK_POOL_ROOT to point at a different pool directory (used for tests).
"""
import json, os, re, sys, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(os.environ.get("NETWORK_POOL_ROOT", Path(__file__).resolve().parent))
FOLDERS = {"strategy": "strategies", "backtest": "backtests", "paper_trade": "paper_trades", "market_note": "market_notes"}
SCHEMA = json.loads((Path(__file__).resolve().parent / "schema.json").read_text())

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
def _file(t): return ROOT / FOLDERS[t] / "records.jsonl"

def _iter(folder=None):
    for t, f in FOLDERS.items():
        if folder and folder not in (t, f): continue
        p = ROOT / f / "records.jsonl"
        if p.exists():
            for line in p.read_text().splitlines():
                if line.strip(): yield json.loads(line)

def add(record=None, **fields):
    """Validate, guard, de-dup and append one record. Returns the stored record. Raises ValueError."""
    rec = dict(record or {}); rec.update(fields)
    rec.setdefault("id", uuid.uuid4().hex)
    rec.setdefault("timestamp_et", now_et())
    errs = validate(rec)
    if errs: raise ValueError("schema: " + "; ".join(errs))
    hits = find_secrets(json.dumps(rec["payload"])) + [f"secret-looking key '{k}'" for k in _secret_keys(rec["payload"])] \
        + ["possible seed phrase" for s in _strings(rec["payload"]) if _seed_like(s)]
    if hits: raise ValueError("secret guard: payload rejected (" + ", ".join(sorted(set(hits))) + ")")
    if any(r.get("id") == rec["id"] for r in _iter()): raise ValueError(f"duplicate id: {rec['id']}")
    p = _file(rec["type"]); p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as fh:  # append only, never rewrite
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
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

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("add", "query", "count"): print(__doc__); sys.exit(1)
    try:
        if a[0] == "add": print(json.dumps(add(json.loads(a[1]))))
        elif a[0] == "count": print(json.dumps(counts(), indent=1))
        else:
            kw = dict(x.split("=", 1) for x in a[1:])
            for r in query(**kw): print(json.dumps(r))
    except ValueError as e:
        print(f"REJECTED: {e}", file=sys.stderr); sys.exit(2)
