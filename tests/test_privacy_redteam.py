"""Red-team regression tests for the privacy filter.

Every value here is fake and built at runtime, so the repo scan never sees a
literal secret, login number, or personal detail in this file.
"""
import base64
import json
import random
import unittest

import pool
from tools import pii
from tools.book_check import privacy_reasons, validate_record

R = random.Random(8)
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ZW = "\u200b"


def digits(n):
    return "".join(R.choice("123456789") for _ in range(n))


def hexs(n):
    return "".join(R.choice("0123456789abcdef") for _ in range(n))


def b58(n):
    return "".join(R.choice(B58) for _ in range(n))


def alnum(n):
    return "".join(R.choice("abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(n)) + "9z"


AT = "@"
USER, DOMAIN = "jsmith", "example" + ".com"
FIRST, LAST = "Jon" + "athan", "Hart" + "ley"
LOGIN = digits(8)
UUID = "-".join((hexs(8), hexs(4), "4" + hexs(3), "a" + hexs(3), hexs(12)))
FAKE = alnum(22)
JWT = "ey" + "J" + alnum(30) + ".ey" + "J" + alnum(40) + "." + alnum(30)
WORDS = ("zoo wrist yellow wagon velvet umbrella tunnel table switch sugar spice smile "
         "shadow river rocket rabbit puzzle pulse planet pepper orange ocean noble nature").split()


def leaks():
    return {
        "email obfuscated": USER + " [at] example [dot] com",
        "email spaced": USER + " " + AT + " " + DOMAIN,
        "email fullwidth": USER + "\uff20" + DOMAIN,
        "email zero-width": ZW.join(USER + AT + DOMAIN),
        "email homoglyph": (USER + AT + DOMAIN).replace("o", "\u043e"),
        "phone intl": "+44 20 " + digits(4) + " " + digits(4),
        "phone keyword": "my phone is " + digits(10),
        "phone uk mobile": "mob 07" + digits(3) + " " + digits(6),
        "street address": str(R.randint(10, 999)) + " Main Street, Springfield",
        "address phrase": "my address is on file",
        "name intro": "Hi, I'm " + FIRST + " " + LAST + " and the desk froze",
        "name signature": "Regards,\n" + FIRST + " " + LAST,
        "mt5 login spaced": "mt5 login " + " ".join(LOGIN),
        "mt5 login zero-width": "mt5 lo" + ZW + "gin " + LOGIN,
        "mt5 login cyrillic": "mt5 l\u043egin " + LOGIN,
        "login dashed": "mt5 login " + "-".join(LOGIN[i:i + 2] for i in range(0, 8, 2)),
        "server lowercase": "icmarkets" + "sc-demo02",
        "server trial": "Exness" + "-MT5Trial7",
        "server segments": "Pepperstone" + "-Edge-Demo",
        "oanda account": "OANDA account 001-001-" + digits(7) + "-001",
        "api key prose": "my api key is " + FAKE,
        "named key prose": "Here's my HFData key " + FAKE,
        "env secret": "CLIENT" + "_SECRET=" + FAKE,
        "env line": "FOO=bar\nHFDATA" + "_API_KEY=" + FAKE + "\n",
        "bearer lowercase": "authorization: bear" + "er " + FAKE,
        "solana key base58": "key " + b58(88),
        "solana key bytes": "[" + ",".join(str(R.randint(0, 255)) for _ in range(64)) + "]",
        "seed words in prose": "my words are " + " ".join(WORDS),
        "seed numbered": " ".join(f"{i + 1}.{w}" for i, w in enumerate(WORDS[:12])),
        "eth wallet": "polymarket wallet 0x" + hexs(40),
        "sol wallet": "my wallet is " + b58(44),
        "ipv4": "my vps ip " + ".".join(str(R.randint(23, 99)) for _ in range(4)),
        "ipv6": "ip 2a02:" + hexs(4) + ":" + hexs(4) + "::1",
        "home path": "/home/" + USER + "/desk/config.json",
        "windows path": "C:\\Users\\" + FIRST + "\\Documents",
        "github pat": "github" + "_pat_" + alnum(40),
        "telegram bot token with prefix": "bot" + digits(10) + ":A" + "A" + alnum(33),
        "telegram chat id": "telegram chat id " + digits(10),
        "telegram handle": "DM me on Telegram " + AT + USER + "_trades",
        "card": "card " + " ".join(["4111"] + ["1111"] * 3),
        "card dotted": "card " + ".".join(["4111"] + ["1111"] * 3),
        "ssn": "ssn " + str(R.randint(100, 665)) + "-" + str(R.randint(10, 99)) + "-" + digits(4),
        "url token": "https://api.example.net/v1?tok" + "en=" + FAKE,
        "url userinfo": "https://" + USER + ":" + FAKE + AT + "host.example.net/",
        "base64 secret": base64.b64encode(("api" + "_key=" + FAKE).encode()).decode(),
        "base64 email": base64.b64encode((USER + AT + DOMAIN).encode()).decode(),
        "password colon": "pw: " + FAKE,
    }


SAFE = [
    "token BONK up 5% on the open", "BONK mint " + b58(44), "ES 5100.25 long at 10:05 ET", "commit " + hexs(40),
    "record id " + hexs(32), "record id " + UUID, "2026-10-29T10:05:00-04:00", "E10 long MES on the RTH open",
    "pre-demo hardening", "paper balance 10000", "epoch 1730203200000", "/workspace/network_pool/pool.py",
    "The Server bot is idle", "will-the-fed-cut-rates-in-december", "KXFEDDECISION-26DEC-C25 yes at 0.63",
    "token id " + "".join(R.choice("0123456789") for _ in range(77)), "the auth token was rotated", "bearer of good news",
    "Thanks, Book", "call 5100.25 strike", "close long market open order paper price profit", "test suite 105 tests pass",
    "data from New York session", "Best Sharpe Ratio was E10", "mt5 18500.5 fill", "version 10.4.2.1 of the bridge",
    "localhost 127.0.0.1", "the api key is missing", "socials: telegram link present, hard reject", "E21-Live run",
    "You can also write gbtnsupport" + AT + "gmail.com instead of filing this.",
]


class RedTeamTest(unittest.TestCase):
    def test_every_payload_is_blocked_in_text_and_records(self):
        for name, text in leaks().items():
            with self.subTest(name):
                self.assertTrue(privacy_reasons(text), name)
                rec = {"timestamp_et": "2026-10-28T10:05:00-04:00", "source_bot": "scan", "type": "market_note",
                       "symbol": "ES", "label": "paper", "payload": {"legs": [{"comment": text}]}}
                self.assertFalse(validate_record(rec)["ok"], name)
                rec["payload"] = {text: 1}  # a key is checked like a value
                self.assertFalse(validate_record(rec)["ok"], name)

    def test_reasons_never_echo_the_value(self):
        for name, text in leaks().items():
            joined = json.dumps(privacy_reasons(text))
            for part in (FAKE, LOGIN, USER, UUID):
                self.assertNotIn(part, joined, name)

    def test_normal_trading_text_still_passes(self):
        for text in SAFE:
            with self.subTest(text[:30]):
                self.assertEqual(privacy_reasons(text), [], text)

    def test_wallet_keys_and_byte_arrays_in_records(self):
        self.assertTrue(pii.key_reasons({"wallet": b58(44)}))
        self.assertTrue(pii.key_reasons({"owner": "0x" + hexs(40)}))
        self.assertTrue(pii.key_reasons({"k": [R.randint(0, 255) for _ in range(64)]}))
        self.assertTrue(pii.key_reasons({"chat_id": int(digits(9))}))
        self.assertEqual(pii.key_reasons({"mint": b58(44), "pnl": [1.5, -2.0], "socials": {"telegram": "link"}}), [])

    def test_long_hostile_input_stays_fast(self):
        import time
        start = time.time()
        for unit in ("1-", "a.", "A", "a:", "1 . ", "aa-Demo", "a [at] "):
            privacy_reasons((unit * 30000)[:60000])
        self.assertLess(time.time() - start, 10)

    def test_review_reason_is_filtered_too(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("NETWORK_POOL_ROOT")
            os.environ["NETWORK_POOL_ROOT"] = tmp
            try:
                sid = pool.submit({"timestamp_et": "2026-10-28T10:05:00-04:00", "source_bot": "scan", "type": "market_note",
                                   "symbol": "ES", "label": "paper", "payload": {"note": "ok"}})
                with self.assertRaises(ValueError):
                    pool.decide(sid, "reject", "ask " + USER + AT + DOMAIN)
            finally:
                if old is None:
                    os.environ.pop("NETWORK_POOL_ROOT", None)
                else:
                    os.environ["NETWORK_POOL_ROOT"] = old


if __name__ == "__main__":
    unittest.main()
