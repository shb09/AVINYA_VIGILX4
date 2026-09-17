from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models.state import DataClass


@dataclass
class RawHit:
    raw: str
    data_class: DataClass
    hint: str
    start: int = 0
    end: int = 0


@dataclass
class InstructionHit:
    text: str
    kind: str
    reason: str
    trusted: bool = False
    span: tuple[int, int] = (0, 0)


_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_TOKEN_RE = re.compile(
    r"\b(?:sk|pk|ghp|gho|ghu|tok|xox[a-z]?|api|key|sec|acct)[_-][A-Za-z0-9_\-]{12,}\b"
    r"|\bsk-[A-Za-z0-9]{12,}\b",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{16,}\b", re.IGNORECASE)
_HEX_RE = re.compile(r"\b[0-9a-fA-F]{32,64}\b")
_B64_RE = re.compile(r"\b[A-Za-z0-9+/]{44,}={0,2}\b")
_CODE_RE = re.compile(r"\b[A-Z0-9]{3,8}-[A-Z0-9]{3,8}\b")
_API_URL_KEY_RE = re.compile(r"(?:[?&](?:key|token|secret|api_key|access_token)=)[^\s&\"']+")
_PHONE_RE = re.compile(r"(?:^|\s)\+[0-9][0-9\s.\-()]{6,18}[0-9]\b")

_INSTRUCTION_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "OVERRIDE",
        "tells the agent to override or disregard its original task",
        re.compile(
            r"ignore (your|the|the user'?s|my|all|previous|earlier)([^.!?]{0,40}?)(instructions|task|prompt|orders?|goals?|checks?|request)"
            r"|disregard (your|the|the user'?s|previous|earlier)(\s+feature)?\s*(instructions|task|prompt|orders?|goals?|checks?|request)"
            r"|forget (your|the|previous|earlier).{0,20}(task|instructions|orders)"
            r"|instead of (the )?(original|user'?s|user|requested) (task|instructions|request|prompt)"
            r"|do not (follow|complete|obey) (the )?(user|original|requested).{0,20}(task|instruction|request)"
            r"|do not (inform|tell) the (user|human)",
            re.IGNORECASE,
        ),
    ),
    (
        "EXFILTRATION",
        "asks the agent to send, submit, or exfiltrate data",
        re.compile(
            r"send (your|the|user'?s|victim'?s|my).{0,40}(token|key|password|secret|data|details|information|cookie|session|code|credentials)"
            r"|submit (your|the|user'?s|my).{0,30}(token|key|password|secret|data|code|credentials)"
            r"|(exfiltrate|transfer|upload|export|post|forward) (your|the|user'?s|my).{0,30}(token|key|secret|data|information)"
            r"|copy (your|the|user'?s|my).{0,30}(token|key|password|secret|code) to"
            r"|enter (your|the|user'?s|my).{0,30}(token|password|secret|code) into",
            re.IGNORECASE,
        ),
    ),
    (
        "PRESSURE",
        "applies artificial pressure to coerce the agent into acting",
        re.compile(
            r"(to|if|in order to) (continue|proceed|keep|unlock|access|finish|verify|confirm)( reading| using| access)?"
            r"|you (must|need|have) to (send|submit|enter|provide|verify|confirm|paste)"
            r"|will (lock|ban|remove|delete|penalize|charge|terminate) (your|the) (account|access)"
            r"|before you can (continue|proceed|access|read)",
            re.IGNORECASE,
        ),
    ),
    (
        "SECRET_HARVEST",
        "asks the agent to reveal confidential values",
        re.compile(
            r"what (is|was) (your|the|my) (password|token|secret|pin|code|key|card)"
            r"|reveal (your|the|my) (password|token|secret|pin|code|key)"
            r"|confirm (your|my|the) (password|token|pin|secret|code|identity)",
            re.IGNORECASE,
        ),
    ),
    (
        "ROLE_EXPLOIT",
        "attempts to redefine the agent's authority or scope",
        re.compile(
            r"from now on (you|your|behave|act|treat)"
            r"|you are now (an?|the).{0,25}agent(?![a-zA-Z])"
            r"|(act|behave) as if you are (a )?(human|admin|user|owner)"
            r"|you have (no|full|complete) (restrictions|permissions|limits|authority)",
            re.IGNORECASE,
        ),
    ),
]


def _luhn_valid(digits: str) -> bool:
    total = 0
    reverse = digits[::-1]
    for i, ch in enumerate(reverse):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _longest_first(hits: list[RawHit]) -> list[RawHit]:
    seen: set[str] = set()
    out: list[RawHit] = []
    for h in sorted(hits, key=lambda h: (len(h.raw), -h.start), reverse=True):
        if h.raw in seen:
            continue
        overlap = any(h.start < o.end and o.start < h.end for o in out)
        if overlap:
            continue
        seen.add(h.raw)
        out.append(h)
    return list(sorted(out, key=lambda h: h.start))


def detect_raw(text: str, canary: str | None = None) -> list[RawHit]:
    if not text:
        return []
    hits: list[RawHit] = []

    if canary and canary in text:
        i = text.find(canary)
        hits.append(RawHit(canary, DataClass.CANARY, "seeded canary", i, i + len(canary)))

    for m in _EMAIL_RE.finditer(text):
        hits.append(RawHit(m.group(0), DataClass.EMAIL, "email address", m.start(), m.end()))

    for m in _SSN_RE.finditer(text):
        hits.append(RawHit(m.group(0), DataClass.PII, "social security number", m.start(), m.end()))

    for m in _CARD_RE.finditer(text):
        digits = re.sub(r"[^0-9]", "", m.group(0))
        if len(digits) in {13, 15, 16, 17, 18, 19} and _luhn_valid(digits):
            hits.append(RawHit(m.group(0), DataClass.CARD, "card number", m.start(), m.end()))

    for m in _TOKEN_RE.finditer(text):
        hits.append(RawHit(m.group(0), DataClass.SECRET, "API-style token", m.start(), m.end()))

    for m in _BEARER_RE.finditer(text):
        hits.append(RawHit(m.group(0), DataClass.SECRET, "bearer token", m.start(), m.end()))

    for m in _API_URL_KEY_RE.finditer(text):
        hits.append(RawHit(m.group(0).split("=", 1)[1], DataClass.SECRET, "secret in URL parameter", m.start(), m.end()))

    for m in _HEX_RE.finditer(text):
        hits.append(RawHit(m.group(0), DataClass.SECRET, "high-entropy hex value", m.start(), m.end()))

    for m in _B64_RE.finditer(text):
        hits.append(RawHit(m.group(0), DataClass.SECRET, "high-entropy base64 value", m.start(), m.end()))

    for m in _CODE_RE.finditer(text):
        token = m.group(0)
        if any(k in token for k in ("TOKEN", "KEY", "CODE", "SECRET", "PIN", "PASS")) or re.search(r"\d", token):
            hits.append(RawHit(token, DataClass.SECRET, "one-time code / passcode", m.start(), m.end()))

    for m in _PHONE_RE.finditer(text):
        hits.append(RawHit(m.group(0), DataClass.PII, "phone number", m.start(), m.end()))

    return _longest_first(hits)


def detect_instructions(text: str) -> list[InstructionHit]:
    if not text:
        return []
    found: list[InstructionHit] = []
    for kind, reason, pattern in _INSTRUCTION_PATTERNS:
        for m in pattern.finditer(text):
            found.append(
                InstructionHit(
                    text=m.group(0),
                    kind=kind,
                    reason=reason,
                    trusted=False,
                    span=(m.start(), m.end()),
                )
            )
    return found


_FIELD_NAME_CLASS: list[tuple[str, DataClass]] = [
    ("card", DataClass.CARD),
    ("cvv", DataClass.CARD),
    ("cc-number", DataClass.CARD),
    ("password", DataClass.CREDENTIAL),
    ("passwd", DataClass.CREDENTIAL),
    ("pin", DataClass.CREDENTIAL),
    ("token", DataClass.SECRET),
    ("apikey", DataClass.SECRET),
    ("api_key", DataClass.SECRET),
    ("secret", DataClass.SECRET),
    ("access-code", DataClass.SECRET),
    ("email", DataClass.EMAIL),
    ("mail", DataClass.EMAIL),
    ("phone", DataClass.PII),
    ("ssn", DataClass.PII),
    ("address", DataClass.LOCATION),
    ("location", DataClass.LOCATION),
    ("zip", DataClass.LOCATION),
]


def classify_field(name: str, type_: str | None, value: str | None) -> DataClass:
    if type_ in {"password", "secret", "token"}:
        return DataClass.CREDENTIAL if type_ == "password" else DataClass.SECRET
    needle = name.lower() if name else ""
    for key, cls in _FIELD_NAME_CLASS:
        if key in needle:
            return cls
    if value and "@" in value and "." in value:
        return DataClass.EMAIL
    if value and len(value) >= 3 and _CODE_RE.search(value):
        return DataClass.SECRET
    return DataClass.PUBLIC