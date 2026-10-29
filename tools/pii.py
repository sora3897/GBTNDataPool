"""Extra personal-data and secret detectors for free text and record strings.

Stdlib only. Used by tools/book_check.privacy_reasons on issue titles and bodies,
pool records, bug reports, and review reasons. Returns reason names only, never
the matched values. The repo file scan does not use these (docs would trip them).
"""
import base64
import binascii
import re
import unicodedata
from pathlib import Path

# ---- normalizing obfuscated text ------------------------------------------
_INVISIBLE = re.compile("[\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5\u180b-\u180e\u200b-\u200f\u202a-\u202e\u2060-\u206f\u3164\ufe00-\ufe0f\ufeff]")
# Common Cyrillic and Greek letters that look like Latin ones.
_CONFUSABLE = str.maketrans({
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0443": "y", "\u0445": "x",
    "\u0456": "i", "\u0458": "j", "\u0455": "s", "\u0501": "d", "\u04bb": "h", "\u0410": "A", "\u0412": "B",
    "\u0415": "E", "\u041a": "K", "\u041c": "M", "\u041d": "H", "\u041e": "O", "\u0420": "P", "\u0421": "C",
    "\u0422": "T", "\u0425": "X", "\u0406": "I", "\u0408": "J", "\u0405": "S", "\u03bf": "o", "\u03b1": "a",
    "\u03b5": "e", "\u03b9": "i", "\u03ba": "k", "\u03bd": "v", "\u03c1": "p", "\u03c4": "t", "\u03c5": "u",
    "\u0391": "A", "\u0392": "B", "\u0395": "E", "\u0396": "Z", "\u0397": "H", "\u0399": "I", "\u039a": "K",
    "\u039c": "M", "\u039d": "N", "\u039f": "O", "\u03a1": "P", "\u03a4": "T", "\u03a5": "Y", "\u03a7": "X",
})
# Runs of five or more single characters split by one space, dot, dash or underscore ("5 1 2 3 4 5").
_SPACED_RUN = re.compile(r"(?<![\w])\w(?:[ ._-]\w){4,}(?![\w])")
_B64_CANDIDATE = re.compile(r"[A-Za-z0-9+/_-]{16,}={0,2}")


def normalize(text):
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE.sub("", text).translate(_CONFUSABLE)
    return text


def _decoded_base64(text):
    out = []
    for match in _B64_CANDIDATE.finditer(text):
        chunk = match.group(0).rstrip("=")
        if re.fullmatch(r"[0-9a-fA-F]+", chunk):  # hex ids and commit hashes are not base64 secrets
            continue
        for decoder in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                raw = decoder(chunk + "=" * (-len(chunk) % 4))
            except (binascii.Error, ValueError):
                continue
            if len(raw) < 8:
                continue
            try:
                decoded = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            printable = sum(ch.isprintable() or ch in "\n\t" for ch in decoded)
            if printable / len(decoded) >= 0.95 and re.search(r"[A-Za-z]{3}", decoded):
                out.append(decoded)
                break
    return out


def variants(text):
    """The text plus normalized, de-spaced, and base64-decoded forms of it."""
    seen = [text]
    norm = normalize(text)
    collapsed = _SPACED_RUN.sub(lambda m: re.sub(r"[ ._-]", "", m.group(0)), norm)
    dotted = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", re.sub(r"\s*@\s*", "@", norm))
    for item in [norm, collapsed, dotted] + _decoded_base64(norm):
        if item not in seen:
            seen.append(item)
    for item in list(seen[1:]):
        for decoded in _decoded_base64(item):
            if decoded not in seen:
                seen.append(decoded)
    return seen


# ---- detectors ------------------------------------------------------------
_TLD = r"(?:com|net|org|io|me|co|uk|de|fr|es|it|nl|ca|au|us|edu|gov|info|biz|app|dev|xyz|ai|ru|in|br|jp|ch|se)"
_DOT = r"(?:\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*|\s+dot\s+)"
_EMAIL_OBFUSCATED = re.compile(
    r"(?i)(?<![\w.+-])[\w.+-]{2,64}\s*(?:[\[\(\{]\s*at\s*[\]\)\}]\s*[a-z][\w-]*(?:(?:" + _DOT + r"|\.)[a-z][\w-]*)*(?:" + _DOT + r"|\.)" + _TLD
    + r"|\s+at\s+[a-z][\w-]*(?:" + _DOT + r"[a-z][\w-]*)*" + _DOT + _TLD + r")\b"
)
_EMAIL_SPACED = re.compile(r"(?i)(?<![\w.+-])[\w.+-]+\s*@\s*[a-z0-9][\w-]*(?:\s*\.\s*[\w-]+)*\s*\.\s*[a-z]{2,}\b")
_PHONE_UK = re.compile(r"(?<![\d.])0(?:7\d{3}|20|1\d{2,3})[\s-]?\d{3,4}[\s-]?\d{3,4}(?![\d.])")
_PHONE_INTL = re.compile(r"(?<![\w+.])\+\d{1,3}(?:[\s.-]?\(?\d{1,4}\)?){1,5}(?![\w.])")
_PHONE_KEYWORD = re.compile(
    r"(?i)\b(?:phone|tel|telephone|mobile|mob|cell|whatsapp|call(?:\s+me)?|text\s+me|sms|signal)\b(?:\s+(?:number|no\.?|num|is|at|on|me))*"
    r"\s*[:=#]?\s*(\+?\(?\d[\d\s().-]{5,}\d)"
)
_ADDRESS = re.compile(
    r"(?i)\b\d{1,6}\s+(?:[A-Za-z]+\.?\s+){1,3}(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|drive|terrace|"
    r"parkway|pkwy|highway|hwy|crescent|strasse|stra\u00dfe)\b"
)
_ADDRESS_PHRASE = re.compile(
    r"(?i)\b(?:my (?:home |mailing |street |postal )?address(?: is)?|i live at|ship(?:ping)? to|mailing address|home address|"
    r"p\.?\s?o\.?\s+box\s+\d+|apt\.?\s+\d+\w?|apartment\s+\d+\w?)\b"
)
_NOT_NAMES = {
    "Book", "Scan", "Vet", "Size", "Fills", "Risk", "Load", "Server", "Coordinator", "Paper", "Live", "Demo",
    "Long", "Short", "Health", "Pool", "Desk", "The", "This", "That", "Bot", "Check", "Trade", "Test",
}
_NAME_INTRO = re.compile(
    r"(?i:\bi\s+am|\bi'?m|\bthis\s+is|\bregards|\bthanks|\bthank\s+you|\bcheers|\bsincerely|\bsigned|\bname\s*[:=-]|"
    r"\bcontact|\bowner|\bholder|\btrader|\buser)[\s,:-]+([A-Z][a-z]+(?:[-'][A-Z][a-z]+)?)(?:\s+[A-Z]\.)?\s+([A-Z][a-z]+(?:[-'][A-Z][a-z]+)?)\b"
)
_MT_SERVER_ANY = re.compile(
    r"(?i)(?<![\w.-])[a-z][a-z0-9.]{2,40}(?:-[a-z0-9]{1,20}){0,3}-(?:mt[45])?(?:demo|live|real|trial|server|ecn)\d{1,3}\b"
)
_MT_SERVER_CAP = re.compile(
    r"(?<![\w.-])(?!(?:Pre|Post|Non|Anti|Paper)-)[A-Z][A-Za-z]{2,30}[A-Za-z0-9.]{0,30}(?:-[A-Z][A-Za-z0-9]{0,20}){0,3}-(?:MT[45])?(?:Demo|Live|Real|Trial|Server|ECN)\d{0,3}\b"
)
_LOGIN_DIGITS = re.compile(
    r"(?i)\b(?:mt[45]|metatrader|login|account|acct)\b(?:\s+(?:number|no\.?|num|id|is|was|login))*[\s:=#-]{0,3}"
    r"(?!\d{4}-\d{2}-\d{2})\d(?:[\s-]?\d){4,14}\b(?![.:]\d)"
)
_KEY_PROSE = re.compile(
    r"(?i)\b(?:api|access|secret|private|auth|bot|jupiter|helius|hfdata|metaapi|telegram|wallet|rpc|client|my)"
    r"(?:[\s_-]*(?:api|access|secret|private|auth))?[\s_-]*(?:key|token|secret|password)\b(?:\s+(?:is|was|=|:|-|here))*\s*[:=-]?\s*[\"'`]?"
    r"(?=[A-Za-z0-9_\-]{12,})(?=[A-Za-z0-9_\-]*\d)(?=[A-Za-z0-9_\-]*[A-Za-z])[A-Za-z0-9_\-]{12,}"
)
_KEY_ASSIGN = re.compile(
    r"(?i)(?:\b|(?<=_))(?:key|token|secret|pwd|pw|pass|passcode|passphrase|credential|credentials)\s*[\"']?\s*[:=]\s*[\"']?"
    r"(?=[A-Za-z0-9_\-+/.]{12,})(?=[A-Za-z0-9_\-+/.]*\d)(?=[A-Za-z0-9_\-+/.]*[A-Za-z])[A-Za-z0-9_\-+/.]{12,}"
)
_ENV_LINE = re.compile(
    r"(?im)^\s*(?:export\s+|set\s+)?[A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASS|PWD|SEED|MNEMONIC|PRIVATE|CREDENTIALS?|LOGIN)[A-Z0-9_]*"
    r"\s*[:=]\s*[\"']?[^\s\"']{6,}"
)
_ENV_SECRET = re.compile(r"(?i)(?:\b|(?<=_))(?:client[_-]?)?secret\b\s*[\"']?\s*[:=]\s*[\"']?[^\s\"',}]{6,}")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{16,}")
_SOL_KEY = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{80,90}(?![1-9A-HJ-NP-Za-km-z])")
_BYTE_ARRAY = re.compile(r"\[\s*(?:\d{1,3}\s*,\s*){31,}\d{1,3}\s*\]")
_ETH_ADDR = re.compile(r"(?i)\b0x[0-9a-f]{40}\b")
_SOL_ADDR = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])")
_WALLET_CONTEXT = re.compile(
    r"(?i)\b(?:wallet|address|addr|pubkey|public\s+key|owner|signer|payer|deposit|receive|send\s+to|phantom|solflare|my\s+account)\b"
)
_IPV4 = re.compile(r"(?<![\d.])((?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})(?![\d.]|\.\d)")
_IPV6 = re.compile(
    r"(?i)(?<![\w:])(?:(?:[0-9a-f]{1,4}:){7}[0-9a-f]{1,4}|(?:[0-9a-f]{1,4}:){1,6}:(?:[0-9a-f]{1,4}(?::[0-9a-f]{1,4}){0,5})?)(?![\w:])"
)
_GENERIC_USERS = r"(?:runner|user|username|you|your-?name|name|me|box|ubuntu|runneradmin|public|default|shared|all users|<[^>]*>|\$\w+|%\w+%|\{\w+\}|\.\.\.|x+)"
_USER_PATH = re.compile(
    r"(?i)(?:/home/|/users/|\b[a-z]:[\\/]+(?:users|documents and settings)[\\/]+)(?!" + _GENERIC_USERS + r"(?:[\\/\s\"']|$))[^\s/\\:*?\"<>|]+"
)
_GITHUB_PAT = re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}")
_CHAT_ID = re.compile(r"(?i)\b(?:chat|telegram|tg|user|channel)[\s_-]?id\b\W{0,4}(?:is\s+)?-?\d{5,}")
_HANDLE = re.compile(
    r"(?i)\b(?:telegram|tg|discord|twitter|instagram|insta|tiktok|snapchat|snap|signal|whatsapp|reddit|handle|username|"
    r"dm\s+me|message\s+me|find\s+me)\b[^\n@]{0,24}@[A-Za-z0-9_.]{3,}"
)
_CARD = re.compile(r"(?<![\d.-])(?:\d[ -]?){12,18}\d(?![\d.-]|[ -]\d)")
_CARD_GROUPED = re.compile(r"(?<![\d.])\d{4}([ .-])\d{4,6}\1\d{4,5}(?:\1\d{1,4})?(?![\d.])")
_SSN = re.compile(r"(?<![\d-])(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}(?![\d-])")
_SSN_KEYWORD = re.compile(r"(?i)\b(?:ssn|social\s+security(?:\s+(?:number|no\.?))?|sin|tax\s+id|tin|national\s+id|passport(?:\s+(?:number|no\.?))?)\b\W{0,5}[A-Z]?\d(?:[\s-]?\d){6,10}\b")
_URL_SECRET = re.compile(
    r"(?i)[?&#](?:token|access_token|id_token|refresh_token|auth|authorization|api[_-]?key|apikey|key|secret|client_secret|"
    r"password|pwd|pass|sig|signature|x-amz-signature|x-amz-credential|x-amz-security-token|code|session|sessionid|sid|jwt)=[^&\s#\"']{8,}"
)
_URL_USERINFO = re.compile(r"(?i)(?<![\w+.-])[a-z][a-z0-9+.-]{0,15}://[^/\s:@\"']+:[^/\s@\"']+@")


def _bip39():
    path = Path(__file__).with_name("bip39_english.txt")
    try:
        return frozenset(path.read_text(encoding="utf-8").split())
    except OSError:
        return frozenset()


_WORDS = _bip39()


def _seed_run(text):
    run = 0
    for word in re.findall(r"[a-z]+", text.lower()):
        run = run + 1 if word in _WORDS else 0
        if run >= 12:
            return True
    return False


def _luhn(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _card(text):
    for match in list(_CARD.finditer(text)) + list(_CARD_GROUPED.finditer(text)):
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19 and digits[0] in "3456" and _luhn(digits):
            return True
    return False


def _public_ip(text):
    for match in _IPV4.finditer(text):
        parts = [int(p) for p in match.group(1).split(".")]
        if parts[0] in (0, 127) or parts == [255, 255, 255, 255]:
            continue
        if re.search(r"(?i)\b(?:version|ver|v|release|build|python|node)\W{0,3}$", text[max(0, match.start() - 12):match.start()]):
            continue
        return True
    for match in _IPV6.finditer(text):
        value = match.group(0).lower()
        if value in ("::", "::1") or value.count(":") < 2:
            continue
        return True
    return False


def _wallet(text):
    if _ETH_ADDR.search(text):
        return True
    for match in _SOL_ADDR.finditer(text):
        value = match.group(0)
        if not (re.search(r"\d", value) and re.search(r"[a-z]", value) and re.search(r"[A-Z]", value)):
            continue
        before = text[max(0, match.start() - 40):match.start()]
        if _WALLET_CONTEXT.search(before) and not re.search(r"(?i)\b(?:mint|token|pool|pair|program|contract|market)\b[^\n]{0,15}$", before):
            return True
    return False


def _names(text):
    for match in _NAME_INTRO.finditer(text):
        if match.group(1) not in _NOT_NAMES and match.group(2) not in _NOT_NAMES:
            return True
    return False


DETECTORS = (
    ("personal data: email", lambda t: bool(_EMAIL_OBFUSCATED.search(t) or _EMAIL_SPACED.search(t))),
    ("personal data: phone number", lambda t: any(
        len(re.sub(r"\D", "", m.group(1))) >= 9 for m in _PHONE_KEYWORD.finditer(t)) or any(
        len(re.sub(r"\D", "", m.group(0))) >= 9 for m in _PHONE_INTL.finditer(t)) or any(
        len(re.sub(r"\D", "", m.group(0))) in (10, 11) for m in _PHONE_UK.finditer(t))),
    ("personal data: street address", lambda t: bool(_ADDRESS.search(t) or _ADDRESS_PHRASE.search(t))),
    ("personal data: name", _names),
    ("account data: broker server name", lambda t: bool(_MT_SERVER_ANY.search(t) or _MT_SERVER_CAP.search(t))),
    ("account data: account number", lambda t: bool(_LOGIN_DIGITS.search(t))),
    ("secret: api key or token", lambda t: bool(_KEY_PROSE.search(t) or _KEY_ASSIGN.search(t) or _ENV_LINE.search(t)
                                                or _ENV_SECRET.search(t) or _BEARER.search(t) or _GITHUB_PAT.search(t))),
    ("secret: private key or seed phrase", lambda t: bool(_SOL_KEY.search(t) or _BYTE_ARRAY.search(t) or _seed_run(t))),
    ("personal data: wallet address", _wallet),
    ("personal data: IP address", _public_ip),
    ("personal data: file path with a user name", lambda t: bool(_USER_PATH.search(t))),
    ("personal data: chat id or handle", lambda t: bool(_CHAT_ID.search(t) or _HANDLE.search(t))),
    ("personal data: card number", _card),
    ("personal data: government id number", lambda t: bool(_SSN.search(t) or _SSN_KEYWORD.search(t))),
    ("secret: credential in a URL", lambda t: bool(_URL_SECRET.search(t) or _URL_USERINFO.search(t))),
)

_WALLET_KEYS = re.compile(r"(?i)(wallet|owner|signer|payer|pubkey|public_?key|user_?address|from_?address|to_?address|deposit)")
_ID_KEYS = {"chatid", "telegramchatid", "telegramid", "telegramuserid", "userid", "discordid", "ip", "ipaddress",
            "email", "emailaddress", "phone", "phonenumber", "mobile", "streetaddress", "homeaddress", "mailingaddress",
            "ssn", "dob", "dateofbirth", "birthday", "passport", "cardnumber", "creditcard", "iban", "routingnumber",
            "username", "telegramhandle", "telegramusername"}


def key_reasons(obj):
    """Record keys that name personal data, and wallet-like keys that hold an address."""
    reasons = []

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                norm = re.sub(r"[^a-z0-9]", "", str(key).lower())
                if norm in _ID_KEYS and item not in (None, "", [], {}):
                    reasons.append("personal data: " + norm)
                elif _WALLET_KEYS.search(str(key)) and isinstance(item, str) and (
                        _ETH_ADDR.search(item) or _SOL_ADDR.fullmatch(item.strip())):
                    reasons.append("personal data: wallet address")
                walk(item)
        elif isinstance(value, list):
            if len(value) in (32, 64) and all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 255 for x in value):
                reasons.append("secret: private key or seed phrase")
            for item in value:
                walk(item)

    walk(obj)
    return reasons


def text_reasons(texts):
    """Reason names for any detector that fires on any variant of any text."""
    found = []
    for text in texts:
        if not isinstance(text, str) or not text:
            continue
        for variant in variants(text):
            for name, detect in DETECTORS:
                if name not in found and detect(variant):
                    found.append(name)
    return found
