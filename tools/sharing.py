#!/usr/bin/env python3
"""User-side on/off switch for upstream sharing.

Local pool writes are never blocked here. Upstream means a public issue,
a records pull request, or any other post that leaves the machine.
share_bugs follows share_data unless the file sets it on its own.
"""
import json
import sys
from pathlib import Path

SETTINGS = "config/user_settings.json"
DEFAULT = {"share_data": False, "share_bugs": False, "upstream_confirmed": False}


def settings_path(root):
    return Path(root) / SETTINGS


def load_settings(root):
    """Return share_data, share_bugs, and upstream_confirmed. Missing file means off."""
    path = settings_path(root)
    if not path.is_file():
        return dict(DEFAULT)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("user settings must be a JSON object")
    if "share_data" not in raw:
        share = False
    else:
        share = raw["share_data"]
    if not isinstance(share, bool):
        raise ValueError("share_data must be true or false")
    bugs = raw["share_bugs"] if "share_bugs" in raw else share
    if not isinstance(bugs, bool):
        raise ValueError("share_bugs must be true or false")
    confirmed = raw.get("upstream_confirmed", False)
    if not isinstance(confirmed, bool):
        raise ValueError("upstream_confirmed must be true or false")
    return {"share_data": share, "share_bugs": bugs, "upstream_confirmed": confirmed}


def save_settings(root, data):
    path = settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    stored = {
        "share_data": bool(data["share_data"]),
        "share_bugs": bool(data["share_bugs"]),
        "upstream_confirmed": bool(data["upstream_confirmed"]),
    }
    path.write_text(json.dumps(stored, indent=2) + "\n", encoding="utf-8")
    return stored


def set_sharing(root, enabled):
    """Turn both switches on or off together. Off clears the upstream confirmation."""
    data = load_settings(root)
    data["share_data"] = bool(enabled)
    data["share_bugs"] = bool(enabled)
    if not enabled:
        data["upstream_confirmed"] = False
    return save_settings(root, data)


def confirm_upstream(root):
    """Record the user's OK for the first upstream submission. Sharing must already be on."""
    data = load_settings(root)
    if not data["share_data"] and not data["share_bugs"]:
        raise ValueError("turn sharing on before confirming an upstream submission")
    data["upstream_confirmed"] = True
    return save_settings(root, data)


def upstream_decision(root, kind):
    """kind is 'data' or 'bugs'.

    allowed is true only when that switch is on and the user has already
    confirmed the first upstream submission.
    """
    if kind not in ("data", "bugs"):
        raise ValueError("kind must be data or bugs")
    data = load_settings(root)
    flag = data["share_data"] if kind == "data" else data["share_bugs"]
    if not flag:
        return {"allowed": False, "reason": "off", "settings": data}
    if not data["upstream_confirmed"]:
        return {"allowed": False, "reason": "needs_confirmation", "settings": data}
    return {"allowed": True, "reason": "allowed", "settings": data}


def main(argv):
    import argparse
    parser = argparse.ArgumentParser(description="Read or change the upstream sharing switch")
    parser.add_argument("--pool", default=".", help="Pool root")
    parser.add_argument("command", choices=("status", "on", "off", "confirm"))
    args = parser.parse_args(argv)
    root = Path(args.pool)
    if args.command == "status":
        data = load_settings(root)
    elif args.command == "on":
        data = set_sharing(root, True)
    elif args.command == "off":
        data = set_sharing(root, False)
    else:
        data = confirm_upstream(root)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
