import base64
import hashlib
import json
import os
import re
import time
import uuid
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any, Deque, Dict, List, Optional, Tuple

from cachetools import TTLCache
from fastapi import FastAPI, Header, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pydantic import BaseModel, Field

from models import AuthRequest, AuthResponse, ChatRequest, ChatResponse, FeedbackRequest

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def getenv_str(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return default if v is None else str(v)


def getenv_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or str(v).strip() == "":
        return default
    try:
        return int(str(v).strip())
    except Exception:
        return default


def getenv_float(key: str, default: float) -> float:
    v = os.getenv(key)
    if v is None or str(v).strip() == "":
        return default
    try:
        return float(str(v).strip())
    except Exception:
        return default


def parse_bool(x: Any, default: bool = False) -> bool:
    if x is None:
        return default
    s = str(x).strip().lower()
    if s == "":
        return default
    return s in ("true", "1", "yes", "y", "on")


ENV = getenv_str("ENV", "dev").strip().lower()

CORS_ORIGINS_ENV = [s.strip() for s in getenv_str("CORS_ORIGINS", "").split(",") if s.strip()]
CORS_ORIGIN_REGEX_ENV = getenv_str("CORS_ORIGIN_REGEX", "").strip()
CORS_ALLOW_CREDENTIALS = parse_bool(getenv_str("CORS_ALLOW_CREDENTIALS", ""), default=False)

AUTH_MODE = getenv_str("AUTH_MODE", "auto").strip().lower()
GOOGLE_OAUTH_CLIENT_ID = getenv_str("GOOGLE_OAUTH_CLIENT_ID", "").strip()
GOOGLE_ALLOWED_DOMAINS = [s.strip().lower() for s in getenv_str("GOOGLE_ALLOWED_DOMAINS", "").split(",") if s.strip()]

JWT_ISSUER = getenv_str("JWT_ISSUER", "corpbot")
JWT_AUDIENCE = getenv_str("JWT_AUDIENCE", "corpbot-users")
JWT_TTL_SECONDS = getenv_int("JWT_TTL_SECONDS", 12 * 60 * 60)
JWT_TTL_SECONDS = max(12 * 60 * 60, min(JWT_TTL_SECONDS, 24 * 60 * 60))
JWT_SIGNING_KEY_BASE64 = getenv_str("JWT_SIGNING_KEY_BASE64", "")
USER_HASH_SALT = getenv_str("USER_HASH_SALT", "")

ADMIN_TOKEN = getenv_str("ADMIN_TOKEN", "").strip()
CACHE_TTL_SECONDS = getenv_int("CACHE_TTL_SECONDS", 86400)
CACHE_TTL_SECONDS = max(60, min(CACHE_TTL_SECONDS, 7 * 24 * 60 * 60))

VERSION_CELL_A1 = getenv_str("VERSION_CELL_A1", "E1")
DATA_RANGE_A1 = getenv_str("DATA_RANGE_A1", "A:F")

GOOGLE_APPLICATION_CREDENTIALS = getenv_str("GOOGLE_APPLICATION_CREDENTIALS", "")

UNRESOLVED_SHEET_ID = getenv_str("UNRESOLVED_SHEET_ID", "")
UNRESOLVED_SHEET_TAB = getenv_str("UNRESOLVED_SHEET_TAB", "Unresolved")
UNRESOLVED_APPEND_RANGE = getenv_str("UNRESOLVED_APPEND_RANGE", "A:M")

UNRESOLVED_DEFAULT_DEPT = getenv_str("UNRESOLVED_DEFAULT_DEPT", "general_affairs").strip() or "general_affairs"

EVENTS_SHEET_ID = getenv_str("EVENTS_SHEET_ID", "").strip()
EVENTS_SHEET_TAB = getenv_str("EVENTS_SHEET_TAB", "Events").strip() or "Events"
EVENTS_APPEND_RANGE = getenv_str("EVENTS_APPEND_RANGE", "A:V").strip() or "A:V"
EVENTS_STORE_QUERY_RAW = parse_bool(getenv_str("EVENTS_STORE_QUERY_RAW", ""), default=True)

EVENTS_SPLIT_TABS = parse_bool(getenv_str("EVENTS_SPLIT_TABS", ""), default=False)

EVENTS_TAB_APP = getenv_str("EVENTS_TAB_APP", "AppEvents").strip() or "AppEvents"
EVENTS_TAB_API = getenv_str("EVENTS_TAB_API", "ApiEvents").strip() or "ApiEvents"
EVENTS_TAB_AUTH = getenv_str("EVENTS_TAB_AUTH", "AuthEvents").strip() or "AuthEvents"

SYS_SHEET_ID = getenv_str("SYS_SHEET_ID", "")
GA_SHEET_ID = getenv_str("GA_SHEET_ID", "")
LABOR_SHEET_ID = getenv_str("LABOR_SHEET_ID", "")
LEGAL_SHEET_ID = getenv_str("LEGAL_SHEET_ID", "")
HR_SHEET_ID = getenv_str("HR_SHEET_ID", "")

DEPT_SHEET_IDS: Dict[str, str] = {
    "system": SYS_SHEET_ID,
    "general_affairs": GA_SHEET_ID,
    "labor": LABOR_SHEET_ID,
    "legal": LEGAL_SHEET_ID,
    "hr": HR_SHEET_ID,
}

DEPT_DISPLAY: Dict[str, Dict[str, str]] = {
    "system": {"name": "システム課", "ext": "1001"},
    "general_affairs": {"name": "総務", "ext": "1002"},
    "labor": {"name": "労務", "ext": "1003"},
    "legal": {"name": "法務", "ext": "1004"},
    "hr": {"name": "人事", "ext": "1005"},
}

SYNONYMS_JSON = getenv_str("SYNONYMS_JSON", "").strip()
SYNONYMS_MAX_EXPANSIONS = max(1, min(getenv_int("SYNONYMS_MAX_EXPANSIONS", 6), 20))
SYNONYMS_MAX_APPLIED = max(1, min(getenv_int("SYNONYMS_MAX_APPLIED", 6), 30))
FUZZY_THRESHOLD = max(0.0, min(getenv_float("FUZZY_THRESHOLD", 0.80), 1.0))
FUZZY_TOP_K = max(1, min(getenv_int("FUZZY_TOP_K", 10), 50))

FALLBACK_DEPT_KEY = UNRESOLVED_DEFAULT_DEPT

ROUTING_DOMINANCE_MIN_COUNT = max(1, getenv_int("ROUTING_DOMINANCE_MIN_COUNT", 2))
ROUTING_DOMINANCE_MIN_DIFF = max(0, getenv_int("ROUTING_DOMINANCE_MIN_DIFF", 1))
ROUTING_DOMINANCE_MIN_RATIO = max(0.0, min(getenv_float("ROUTING_DOMINANCE_MIN_RATIO", 0.60), 1.0))

KW_KEYWORD_MIN_SCORE = max(0.0, min(getenv_float("KW_KEYWORD_MIN_SCORE", 0.65), 1.0))
KW_KEYWORD_MIN_DIFF = max(0, min(getenv_float("KW_KEYWORD_MIN_DIFF", 0.15), 1.0))
KW_KEYWORD_MIN_STRONG_HITS = max(1, min(getenv_int("KW_KEYWORD_MIN_STRONG_HITS", 2), 10))

SESSION_VERSION_TTL_SECONDS = getenv_int("SESSION_VERSION_TTL_SECONDS", 30 * 24 * 60 * 60)
SESSION_VERSION_TTL_SECONDS = max(3600, min(SESSION_VERSION_TTL_SECONDS, 120 * 24 * 60 * 60))


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise HTTPException(status_code=500, detail=msg)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_jst() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))


def now_utc_iso() -> str:
    return now_utc().replace(microsecond=0).isoformat()


def now_jst_iso() -> str:
    return now_jst().replace(microsecond=0).isoformat()


_re_space = re.compile(r"\s+")
_re_punct = re.compile(
    r"[、,。．\.・/／\(\)\[\]\{\}<>＜＞「」『』【】“”\"'`~!！\?？:：;；\|｜\\]+"
)
_re_tail = re.compile(
    r"(です|ます|でした|でしょう|下さい|ください|お願い|お願いします|教えて|教えてください|できますか|出来ますか|可能ですか|可能でしょうか)\s*$"
)
_re_kw_split = re.compile(r"[,\u3001，､\n\r\t]+")
_re_particle = re.compile(r"(が|を|に|で|と|は|の|も|へ|や)")
_re_alphanum = re.compile(r"([a-z0-9]+)")


def normalize_q(s: str) -> str:
    t = unicodedata.normalize("NFKC", (s or "")).strip().lower()
    if not t:
        return ""
    t = _re_alphanum.sub(r" \1 ", t)
    t = _re_punct.sub(" ", t)
    # t = _re_particle.sub(" ", t)
    t = _re_space.sub(" ", t).strip()
    for _ in range(3):
        nt = _re_tail.sub("", t).strip()
        if nt == t:
            break
        t = nt
    t = _re_space.sub(" ", t).strip()
    return t


def tokenize_for_keyword(s: str) -> List[str]:
    qn = normalize_q(s)
    if not qn:
        return []
    parts = [p.strip() for p in qn.split(" ") if p.strip()]
    out: List[str] = []
    for p in parts:
        for x in re.split(r"[\s/]+", p):
            x = x.strip()
            if x:
                out.append(x)
    return out


def split_keywords(raw: Any) -> List[str]:
    s = str(raw or "")
    if not s.strip():
        return []
    parts = [p.strip() for p in _re_kw_split.split(s) if p and p.strip()]
    out: List[str] = []
    for p in parts:
        nk = normalize_q(p)
        if nk:
            out.append(nk)
    out = list(dict.fromkeys(out))
    return out


def token_signature(tokens: List[str]) -> str:
    ts = [str(t).strip() for t in (tokens or []) if str(t).strip()]
    if not ts:
        return ""
    uniq = sorted(list(dict.fromkeys(ts)))
    payload = json.dumps(uniq, ensure_ascii=False, separators=(",", ":"))
    base = payload + "|" + (USER_HASH_SALT or "")
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def hash_subject(subject: str) -> str:
    require(USER_HASH_SALT.strip() != "", "USER_HASH_SALT is required")
    s = (subject or "").strip() + "|" + USER_HASH_SALT
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(s: str) -> bytes:
    pad = "=" * ((4 - (len(s) % 4)) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))


def jwt_signing_key() -> bytes:
    require(JWT_SIGNING_KEY_BASE64.strip() != "", "JWT_SIGNING_KEY_BASE64 is required")
    return base64.b64decode(JWT_SIGNING_KEY_BASE64)


def jwt_encode(payload: Dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = b64url_encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    payload_b64 = b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    msg = f"{header_b64}.{payload_b64}".encode("ascii")
    import hmac

    sig = hmac.new(jwt_signing_key(), msg, hashlib.sha256).digest()
    sig_b64 = b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def jwt_decode(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="invalid token")
    header_b64, payload_b64, sig_b64 = parts
    msg = f"{header_b64}.{payload_b64}".encode("ascii")
    import hmac

    expected = hmac.new(jwt_signing_key(), msg, hashlib.sha256).digest()
    got = b64url_decode(sig_b64)
    if not hmac.compare_digest(expected, got):
        raise HTTPException(status_code=401, detail="invalid token")
    payload = json.loads(b64url_decode(payload_b64).decode("utf-8"))
    return payload


_session_versions = TTLCache(maxsize=200000, ttl=SESSION_VERSION_TTL_SECONDS)


def get_session_version(user_hash: str) -> int:
    if not user_hash:
        return 0
    v = _session_versions.get(user_hash)
    try:
        return int(v) if v is not None else 0
    except Exception:
        return 0


def bump_session_version(user_hash: str) -> int:
    if not user_hash:
        return 0
    cur = get_session_version(user_hash)
    nxt = cur + 1
    _session_versions[user_hash] = nxt
    return nxt


def issue_jwt_for_user_hash(user_hash: str) -> str:
    now_ts = int(time.time())
    sv = get_session_version(user_hash)
    payload = {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": user_hash,
        "sv": int(sv),
        "iat": now_ts,
        "exp": now_ts + int(JWT_TTL_SECONDS),
    }
    return jwt_encode(payload)


def verify_bearer(authorization: str) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer")
    token = authorization.split(" ", 1)[1].strip()
    payload = jwt_decode(token)
    if payload.get("iss") != JWT_ISSUER or payload.get("aud") != JWT_AUDIENCE:
        raise HTTPException(status_code=401, detail="invalid token claims")
    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise HTTPException(status_code=401, detail="invalid token exp")
    if int(time.time()) >= exp:
        raise HTTPException(status_code=401, detail="token expired")
    sub = str(payload.get("sub") or "").strip()
    if not sub:
        raise HTTPException(status_code=401, detail="invalid token sub")
    sv = payload.get("sv")
    try:
        sv_i = int(sv)
    except Exception:
        sv_i = 0
    cur_sv = get_session_version(sub)
    if sv_i != int(cur_sv):
        raise HTTPException(status_code=401, detail="token revoked")
    return payload


RATE_LIMIT_PER_MIN = getenv_int("RATE_LIMIT_PER_MIN", 30)
_rate: Dict[str, Deque[float]] = defaultdict(deque)


def check_rate_limit(user_hash: str, limit_per_minute: int) -> str:
    now = time.time()
    q = _rate[user_hash]
    while q and (now - q[0]) > 60.0:
        q.popleft()
    if len(q) >= limit_per_minute:
        raise HTTPException(status_code=429, detail="rate limit")
    q.append(now)
    return f"ok({len(q)}/{limit_per_minute})"


_svc_cache: Dict[str, Any] = {}


def sheets_service():
    if "svc" in _svc_cache:
        return _svc_cache["svc"]
    require(GOOGLE_APPLICATION_CREDENTIALS.strip() != "", "GOOGLE_APPLICATION_CREDENTIALS is required")
    require(os.path.exists(GOOGLE_APPLICATION_CREDENTIALS), f"credentials not found: {GOOGLE_APPLICATION_CREDENTIALS}")
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_APPLICATION_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
    _svc_cache["svc"] = svc
    return svc


def read_values(sheet_id: str, rng: str) -> List[List[Any]]:
    svc = sheets_service()
    resp = svc.spreadsheets().values().get(spreadsheetId=sheet_id, range=rng).execute()
    return resp.get("values", []) or []


def append_values(sheet_id: str, rng: str, values: List[List[Any]]) -> None:
    svc = sheets_service()
    body = {"values": values}
    svc.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=rng,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()


def parse_rows(values: List[List[Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    # 最初の行がヘッダーらしいか判定するフラグ
    skip_first = False
    if len(values) > 0 and isinstance(values[0], list) and len(values[0]) > 0:
        first_cell = str(values[0][0] or "").strip().lower()
        if "keyword" in first_cell or "キーワード" in first_cell:
            skip_first = True

    for idx, row in enumerate(values, start=1):
        if skip_first and idx == 1:
            continue

        a = row[0] if len(row) > 0 else ""
        b = row[1] if len(row) > 1 else ""
        c = row[2] if len(row) > 2 else ""
        d = row[3] if len(row) > 3 else ""
        f = row[5] if len(row) > 5 else ""
        public = parse_bool(f, default=True)

        q = str(b)
        q_norm = normalize_q(q)

        keywords = split_keywords(a)
        if q_norm:
            keywords = list(dict.fromkeys(keywords + [q_norm]))
        keywords_set = set(keywords)

        rows.append(
            {
                "row_id": idx,
                "id": "",
                "keywords": keywords,
                "keywords_set": keywords_set,
                "q": q,
                "q_norm": q_norm,
                "a": str(c),
                "owner": str(d),
                "public": public,
            }
        )
    return [r for r in rows if r["public"]]


dept_cache = TTLCache(maxsize=50, ttl=CACHE_TTL_SECONDS)
_dept_version_cache = TTLCache(maxsize=200, ttl=CACHE_TTL_SECONDS)


def load_dept(dept_key: str) -> Tuple[str, List[Dict[str, Any]]]:
    sheet_id = DEPT_SHEET_IDS.get(dept_key, "")
    if not sheet_id:
        return ("", [])
    version_vals = read_values(sheet_id, VERSION_CELL_A1)
    version = version_vals[0][0] if version_vals and version_vals[0] else ""
    data_vals = read_values(sheet_id, DATA_RANGE_A1)
    rows = parse_rows(data_vals)
    for r in rows:
        r["id"] = f"{dept_key}:{r['row_id']}"
    return (str(version), rows)


def get_dept_rows_with_auto_refresh(dept_key: str) -> List[Dict[str, Any]]:
    sheet_id = DEPT_SHEET_IDS.get(dept_key, "")
    if not sheet_id:
        return []
    cached = dept_cache.get(dept_key)
    if not cached:
        version, rows = load_dept(dept_key)
        dept_cache[dept_key] = {"version": version, "rows": rows}
        _dept_version_cache[dept_key] = version
        return rows

    rows = cached.get("rows", [])
    cached_version = str(cached.get("version") or "")

    vchk = _dept_version_cache.get(dept_key)
    if vchk is not None and str(vchk) == cached_version:
        return rows

    version_vals = read_values(sheet_id, VERSION_CELL_A1)
    current_version = str(version_vals[0][0] if version_vals and version_vals[0] else "")

    if cached_version == current_version:
        _dept_version_cache[dept_key] = current_version
        return rows

    version, new_rows = load_dept(dept_key)
    dept_cache[dept_key] = {"version": version, "rows": new_rows}
    _dept_version_cache[dept_key] = version
    return new_rows


def admin_refresh_cache(dept_key: Optional[str] = None) -> Dict[str, Any]:
    refreshed: List[str] = []
    skipped: List[str] = []
    targets = [dept_key] if dept_key else list(DEPT_SHEET_IDS.keys())
    for dk in targets:
        if not DEPT_SHEET_IDS.get(dk, ""):
            skipped.append(dk)
            continue
        version, rows = load_dept(dk)
        dept_cache[dk] = {"version": version, "rows": rows}
        _dept_version_cache[dk] = version
        refreshed.append(dk)
    return {"refreshed": refreshed, "skipped": skipped}


def _is_short_ascii_token(s: str) -> bool:
    x = (s or "").strip().lower()
    if not x:
        return True
    if not re.fullmatch(r"[a-z0-9]+", x):
        return False
    return len(x) <= 2


def keyword_score_tokens(tokens: List[str], row_keywords_set: set) -> float:
    if not tokens or not row_keywords_set:
        return 0.0
    hit = sum(1 for t in tokens if t in row_keywords_set)
    denom = max(len(set(tokens)), 1)
    return hit / denom


def keyword_score_loose(query_norm: str, tokens: List[str], row_keywords_set: set) -> float:
    if not row_keywords_set:
        return 0.0
    base = keyword_score_tokens(tokens, row_keywords_set)
    qn = normalize_q(query_norm)
    if not qn:
        return base
    qflat = qn.replace(" ", "")
    if not qflat:
        return base

    kw_hits = 0
    denom = 0
    for kw in row_keywords_set:
        k = str(kw or "").strip().lower()
        if not k:
            continue
        if len(k) < 2:
            continue
        if _is_short_ascii_token(k):
            continue
        denom += 1
        if k.replace(" ", "") in qflat:
            kw_hits += 1
    if denom <= 0:
        return base
    sub = kw_hits / max(min(denom, 3), 1)
    return max(base, sub)


def keyword_loose_strong_hits(query_norm: str, row_keywords_set: set) -> int:
    if not row_keywords_set:
        return 0
    qn = normalize_q(query_norm)
    qflat = qn.replace(" ", "")
    if not qflat:
        return 0
    hits = 0
    for kw in row_keywords_set:
        k = str(kw or "").strip().lower()
        if not k:
            continue
        if len(k) < 2:
            continue
        if _is_short_ascii_token(k):
            continue
        if k.replace(" ", "") in qflat:
            hits += 1
    return hits


def _exclude_set(exclude_ids: Optional[List[str]]) -> set:
    if not exclude_ids:
        return set()
    return set(str(x) for x in exclude_ids if str(x).strip() != "")


_syn_cache: Dict[str, Any] = {}


def _load_synonyms_mapping() -> Dict[str, List[str]]:
    if "syn" in _syn_cache:
        return _syn_cache["syn"]
    if not SYNONYMS_JSON:
        _syn_cache["syn"] = {}
        return {}
    try:
        data = json.loads(SYNONYMS_JSON)
        out: Dict[str, List[str]] = {}
        if isinstance(data, dict):
            for k, v in data.items():
                ck = normalize_q(str(k))
                if not ck:
                    continue
                arr: List[str] = []
                if isinstance(v, list):
                    arr = [normalize_q(str(x)) for x in v if normalize_q(str(x))]
                elif isinstance(v, str):
                    arr = [normalize_q(x) for x in re.split(r"[,\u3001]+", v) if normalize_q(x)]
                arr = [x for x in arr if x and x != ck]
                if arr:
                    out[ck] = sorted(list(dict.fromkeys(arr)))
        _syn_cache["syn"] = out
        return out
    except Exception:
        _syn_cache["syn"] = {}
        return {}


def _build_alias_index(syn: Dict[str, List[str]]) -> Dict[str, List[str]]:
    idx: Dict[str, List[str]] = defaultdict(list)
    for canon, vars_ in syn.items():
        allv = [canon] + list(vars_ or [])
        allv = [normalize_q(x) for x in allv if normalize_q(x)]
        allv = sorted(list(dict.fromkeys(allv)))
        for a in allv:
            repl = [x for x in allv if x != a]
            if repl:
                idx[a] = repl
    return dict(idx)


def _syn_alias_index() -> Dict[str, List[str]]:
    if "alias" in _syn_cache:
        return _syn_cache["alias"]
    syn = _load_synonyms_mapping()
    alias = _build_alias_index(syn)
    _syn_cache["alias"] = alias
    _syn_cache["aliases_sorted"] = sorted(alias.keys(), key=lambda x: (-len(x), x))
    return alias


def _syn_aliases_sorted() -> List[str]:
    _syn_alias_index()
    return _syn_cache.get("aliases_sorted", []) or []


def expand_queries(query_norm: str) -> Tuple[List[str], List[str]]:
    qn = normalize_q(query_norm)
    if not qn:
        return ([], [])
    alias_index = _syn_alias_index()
    aliases_sorted = _syn_aliases_sorted()
    base = qn
    expansions: List[str] = [base]
    applied: List[str] = []
    if not alias_index or not aliases_sorted:
        return (expansions, applied)
    candidates: List[Tuple[str, str]] = []
    for a in aliases_sorted:
        if not a:
            continue
        if a in base:
            repls = alias_index.get(a, [])
            for r in repls[:3]:
                if not r or r == a:
                    continue
                candidates.append((a, r))
    for a, r in candidates[:SYNONYMS_MAX_APPLIED]:
        new_list: List[str] = []
        for q in expansions:
            if len(expansions) + len(new_list) >= SYNONYMS_MAX_EXPANSIONS:
                break
            if a in q:
                nq = normalize_q(q.replace(a, r))
                if nq and nq not in expansions and nq not in new_list:
                    new_list.append(nq)
                    applied.append(f"{a}->{r}")
        expansions.extend(new_list)
        if len(expansions) >= SYNONYMS_MAX_EXPANSIONS:
            break
    expansions = [x for x in expansions if x]
    expansions = list(dict.fromkeys(expansions))
    applied = list(dict.fromkeys(applied))
    return (expansions, applied)


def fuzzy_candidates(
    q_norm: str,
    rows_by_dept: List[Tuple[str, Dict[str, Any]]],
    threshold: float,
    top_k: int,
) -> List[Tuple[float, str, Dict[str, Any]]]:
    qn = normalize_q(q_norm)
    if not qn:
        return []
    scored: List[Tuple[float, str, Dict[str, Any]]] = []
    for dk, r in rows_by_dept:
        rn = str(r.get("q_norm") or "")
        if not rn:
            continue
        ratio = SequenceMatcher(None, qn, rn).ratio()
        if ratio >= threshold:
            scored.append((ratio, dk, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def unresolved_guidance_text(dept_name: str = "総務") -> str:
    return f"この内容に一致する案内が見つかりませんでした。まずは{dept_name}へお問い合わせください。\nこの内容は今後の改善に活用します。"

DEPT_KEYWORDS = {
    "system": [
        "pc", "パソコン", "電源", "起動", "立ち上が", "ログイン",
        "アカウント", "パスワード", "wifi", "wi-fi", "無線", "ネット",
        "インターネット", "vpn", "メール", "gmail", "outlook",
        "teams", "chrome", "edge", "ブラウザ", "拡張", "extension",
        "windows", "mac", "macbook", "iphone", "ipad", "android",
        "intune", "entra", "azure", "m365", "office", "onedrive",
        "sharepoint", "プリンタ", "印刷", "スキャナ", "scanner",
        "lan", "社内wifi",
        "ビデオ", "会議", "web会議", "カメラ", "マイク", "zoom", "meet", "google meet"
    ],
    "legal": [
        "契約", "捺印", "印鑑", "リーガル", "反社", "秘密保持", "nda", "登記"
    ],
    "labor": [
        "勤怠", "有給", "休暇", "残業", "保険", "健康診断", "36協定", "産休", "育休"
    ],
    "hr": [
        "採用", "異動", "評価", "目標", "面談", "人事", "入社", "退職", "給与"
    ],
    "general_affairs": [
        "備品", "郵便", "名刺", "入館証", "代表電話", "慶弔", "電球", "掃除"
    ]
}

def guess_department_by_keyword(query_norm: str) -> str:
    qn = normalize_q(query_norm)
    if not qn:
        return ""
    qflat = qn.replace(" ", "")

    for dept_key, keywords in DEPT_KEYWORDS.items():
        for k in keywords:
            kw = normalize_q(k).replace(" ", "")
            if kw and kw in qflat:
                return dept_key

    return ""


def choose_candidate_routing(depts: List[str], query_norm: str = "") -> str:
    ds = [str(d or "").strip() for d in (depts or []) if str(d or "").strip()]
    if not ds:
        guessed = guess_department_by_keyword(query_norm)
        return guessed if guessed else FALLBACK_DEPT_KEY

    uniq = sorted(list(dict.fromkeys(ds)))
    if len(uniq) == 1:
        return uniq[0]

    cnt = Counter(ds)
    most = cnt.most_common()
    top_dept, top_count = most[0][0], int(most[0][1]) if most else ("", 0)

    if top_dept and top_count >= 3:
        return top_dept

    guessed = guess_department_by_keyword(query_norm)
    if guessed:
        return guessed

    return FALLBACK_DEPT_KEY


def choose_routing_department(
    source: str,
    hit_department: str,
    candidates: List[Dict[str, Any]],
    searched_departments: List[str],
    query_norm: str = "",
) -> str:
    if source in ("exact", "keyword") and hit_department:
        return hit_department

    if source == "candidate":
        depts = [
            str(c.get("department") or "").strip()
            for c in (candidates or [])
            if str(c.get("department") or "").strip()
        ]
        return choose_candidate_routing(depts, query_norm=query_norm)

    if source == "none":
        guessed = guess_department_by_keyword(query_norm)
        return guessed if guessed else FALLBACK_DEPT_KEY

    if searched_departments:
        return searched_departments[0]

    guessed = guess_department_by_keyword(query_norm)
    return guessed if guessed else FALLBACK_DEPT_KEY


def _ensure_row_id(dept_key: str, r: Dict[str, Any]) -> str:
    rid = str(r.get("id") or "").strip()
    if rid:
        return rid
    try:
        row_id = int(r.get("row_id") or 0)
    except Exception:
        row_id = 0
    if row_id <= 0:
        row_id = 0
    rid = f"{dept_key}:{row_id}"
    r["id"] = rid
    return rid


def search_all_departments(query: str, exclude_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    searched_order: List[str] = []
    exact_hit: Optional[Tuple[str, Dict[str, Any]]] = None
    ex = _exclude_set(exclude_ids)

    qn = normalize_q(query)
    expansions, applied = expand_queries(qn)
    q_tokens_orig = tokenize_for_keyword(qn)
    q_tokens_exp: List[List[str]] = []
    for x in expansions[1:]:
        q_tokens_exp.append(tokenize_for_keyword(x))

    scored_orig: List[Tuple[float, str, Dict[str, Any]]] = []
    scored_all: Dict[str, Tuple[float, bool, str, Dict[str, Any]]] = {}
    all_rows_flat: List[Tuple[str, Dict[str, Any]]] = []

    for dept_key in DEPT_SHEET_IDS.keys():
        if not DEPT_SHEET_IDS.get(dept_key, ""):
            continue
        searched_order.append(dept_key)
        rows = get_dept_rows_with_auto_refresh(dept_key)

        for r in rows:
            rid = _ensure_row_id(dept_key, r)
            if rid and rid in ex:
                continue
            all_rows_flat.append((dept_key, r))
            if qn and str(r.get("q_norm") or "") == qn:
                exact_hit = (dept_key, r)
                break
        if exact_hit:
            break

        for r in rows:
            rid = _ensure_row_id(dept_key, r)
            if rid and rid in ex:
                continue
            kws = r.get("keywords_set") or set(r.get("keywords") or [])

            sc0_exact = keyword_score_tokens(q_tokens_orig, kws)
            if sc0_exact > 0:
                scored_orig.append((sc0_exact, dept_key, r))

            best_sc = keyword_score_loose(qn, q_tokens_orig, kws)
            best_is_orig = sc0_exact > 0

            if q_tokens_exp:
                for tks in q_tokens_exp:
                    scx = keyword_score_loose(qn, tks, kws)
                    if scx > best_sc:
                        best_sc = scx
                        best_is_orig = False

            if best_sc > 0:
                prev = scored_all.get(rid)
                if prev is None or best_sc > prev[0] or (best_sc == prev[0] and best_is_orig and not prev[1]):
                    scored_all[rid] = (best_sc, best_is_orig, dept_key, r)

    if exact_hit:
        dk, r = exact_hit
        routing = choose_routing_department("exact", dk, [], searched_order, query_norm=qn)
        return {
            "source": "exact",
            "answer": r["a"],
            "hit_department": dk,
            "hit_row_id": str(r["row_id"]),
            "candidates": [],
            "searched_departments": searched_order,
            "query_norm": qn,
            "expanded_used": expansions[:],
            "syn_applied": applied[:],
            "match_detail": "exact",
            "routing_department": routing,
        }

    scored_orig.sort(key=lambda x: x[0], reverse=True)
    if scored_orig:
        best_score = scored_orig[0][0]
        tie_eps = 0.01
        near_best = [x for x in scored_orig[:10] if x[0] >= best_score - tie_eps]
        if best_score >= 0.8 and len(near_best) == 1:
            dk, r = scored_orig[0][1], scored_orig[0][2]
            routing = choose_routing_department("keyword", dk, [], searched_order, query_norm=qn)
            return {
                "source": "keyword",
                "answer": r["a"],
                "hit_department": dk,
                "hit_row_id": str(r["row_id"]),
                "candidates": [],
                "searched_departments": searched_order,
                "query_norm": qn,
                "expanded_used": expansions[:],
                "syn_applied": applied[:],
                "match_detail": "keyword",
                "routing_department": routing,
            }

    all_list: List[Tuple[float, bool, str, Dict[str, Any]]] = list(scored_all.values())
    all_list.sort(key=lambda x: (x[0], 1 if x[1] else 0), reverse=True)
    top = all_list[:10]

    if not top:
        fz = fuzzy_candidates(qn, all_rows_flat, threshold=FUZZY_THRESHOLD, top_k=FUZZY_TOP_K)
        candidates: List[Dict[str, str]] = []
        for sc, dk, r in fz:
            rid = _ensure_row_id(dk, r)
            if rid and rid in ex:
                continue
            candidates.append(
                {
                    "id": rid,
                    "department": dk,
                    "question": r["q"],
                    "owner": r["owner"],
                }
            )
            if len(candidates) >= 5:
                break
        if candidates:
            routing = choose_routing_department("candidate", "", candidates, searched_order, query_norm=qn)
            return {
                "source": "candidate",
                "answer": "",
                "hit_department": "",
                "hit_row_id": "",
                "candidates": candidates,
                "searched_departments": searched_order,
                "query_norm": qn,
                "expanded_used": expansions[:],
                "syn_applied": applied[:],
                "match_detail": "fuzzy_candidate",
                "routing_department": routing,
            }
        routing = choose_routing_department("none", "", [], searched_order, query_norm=qn)
        return {
            "source": "none",
            "answer": "",
            "hit_department": "",
            "hit_row_id": "",
            "candidates": [],
            "searched_departments": searched_order,
            "query_norm": qn,
            "expanded_used": expansions[:],
            "syn_applied": applied[:],
            "match_detail": "none",
            "routing_department": routing,
        }

    best_score_all = top[0][0]
    best_is_orig, best_dk, best_r = top[0][1], top[0][2], top[0][3]
    second_score_all = top[1][0] if len(top) >= 2 else 0.0
    strong_hits = keyword_loose_strong_hits(qn, best_r.get("keywords_set") or set(best_r.get("keywords") or []))

    if (
        best_score_all >= KW_KEYWORD_MIN_SCORE
        and (len(top) == 1 or (best_score_all - second_score_all) >= KW_KEYWORD_MIN_DIFF)
        and strong_hits >= KW_KEYWORD_MIN_STRONG_HITS
    ):
        routing = choose_routing_department("keyword", best_dk, [], searched_order, query_norm=qn)
        return {
            "source": "keyword",
            "answer": best_r["a"],
            "hit_department": best_dk,
            "hit_row_id": str(best_r["row_id"]),
            "candidates": [],
            "searched_departments": searched_order,
            "query_norm": qn,
            "expanded_used": expansions[:],
            "syn_applied": applied[:],
            "match_detail": "keyword_loose" if not best_is_orig else "keyword",
            "routing_department": routing,
        }

    candidates = []
    any_syn_only = False
    for sc, is_orig, dk, r in top:
        if sc < max(best_score_all - 0.15, 0.35):
            continue
        rid = _ensure_row_id(dk, r)
        if rid and rid in ex:
            continue
        if not is_orig:
            any_syn_only = True
        candidates.append(
            {
                "id": rid,
                "department": dk,
                "question": r["q"],
                "owner": r["owner"],
            }
        )
        if len(candidates) >= 5:
            break

    if candidates:
        md = "synonym_candidate" if any_syn_only and not scored_orig else "candidate"
        routing = choose_routing_department("candidate", "", candidates, searched_order, query_norm=qn)
        return {
            "source": "candidate",
            "answer": "",
            "hit_department": "",
            "hit_row_id": "",
            "candidates": candidates,
            "searched_departments": searched_order,
            "query_norm": qn,
            "expanded_used": expansions[:],
            "syn_applied": applied[:],
            "match_detail": md,
            "routing_department": routing,
        }

    routing = choose_routing_department("none", "", [], searched_order, query_norm=qn)
    return {
        "source": "none",
        "answer": "",
        "hit_department": "",
        "hit_row_id": "",
        "candidates": [],
        "searched_departments": searched_order,
        "query_norm": qn,
        "expanded_used": expansions[:],
        "syn_applied": applied[:],
        "match_detail": "none",
        "routing_department": routing,
    }


def resolve_candidate(selection_id: str) -> Dict[str, Any]:
    if ":" not in selection_id:
        raise HTTPException(status_code=400, detail="invalid selection_id")
    dept_key, row_id_s = selection_id.split(":", 1)
    try:
        row_id = int(row_id_s)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid selection_id")
    rows = get_dept_rows_with_auto_refresh(dept_key)
    for r in rows:
        if int(r["row_id"]) == row_id:
            return {
                "answer": r["a"],
                "hit_department": dept_key,
                "hit_row_id": str(r["row_id"]),
            }
    raise HTTPException(status_code=404, detail="not found")


def audit_log(obj: Dict[str, Any]) -> None:
    s = json.dumps(obj, ensure_ascii=False)
    print(s, flush=True)

    try:
        if isinstance(obj, dict) and obj.get("log_type") == "events_error":
            code = str(obj.get("error_code") or "")
            phase = str(obj.get("phase") or "")
            src = str(obj.get("source") or "")
            tab = str(obj.get("tab") or "")
            reason = str(obj.get("reason") or "")
            print(
                f"EVENTS_ERROR code={code} phase={phase} source={src} tab={tab} reason={reason}",
                flush=True,
            )
    except Exception:
        pass


_unresolved_recent = TTLCache(maxsize=2000, ttl=600)


def normalize_append_range(tab: str, rng_env: str, default_range: str) -> str:
    s = (rng_env or "").strip()
    if not s:
        s = default_range
    if "!" in s:
        return s
    return f"{tab}!{s}"


def unresolved_already_logged(ticket_id: str) -> bool:
    if not ticket_id:
        return False
    if ticket_id in _unresolved_recent:
        return True
    if UNRESOLVED_SHEET_ID.strip() == "":
        return False
    try:
        vals = read_values(UNRESOLVED_SHEET_ID, f"{UNRESOLVED_SHEET_TAB}!A:A")
        col = [str(r[0]).strip() for r in vals if r]
        exists = ticket_id in (col[1:] if len(col) >= 2 else col)
        if exists:
            _unresolved_recent[ticket_id] = True
        return exists
    except Exception:
        return False


_email_re = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_tel_re = re.compile(r"\b(?:0\d{1,4}[- ]?\d{1,4}[- ]?\d{3,4}|0\d{9,10})\b")


def mask_and_summarize_query(query: str, max_len: int = 120) -> str:
    s = (query or "").strip()
    if not s:
        return ""
    s = _email_re.sub("[email]", s)
    s = _tel_re.sub("[tel]", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        return s[:max_len] + "…"
    return s


def append_unresolved_row(values: List[Any]) -> None:
    require(UNRESOLVED_SHEET_ID.strip() != "", "UNRESOLVED_SHEET_ID is required")
    if len(values) != 13:
        raise ValueError(f"unresolved row must have 13 cols, got {len(values)}")
    rng = normalize_append_range(UNRESOLVED_SHEET_TAB, UNRESOLVED_APPEND_RANGE, "A:M")
    append_values(UNRESOLVED_SHEET_ID, rng, [values])


def append_event_row(values: List[Any], tab: str) -> None:
    if not EVENTS_SHEET_ID:
        return
    if len(values) != 22:
        raise ValueError(f"events row must have 22 cols, got {len(values)}")
    rng = normalize_append_range(tab, EVENTS_APPEND_RANGE, "A:V")
    append_values(EVENTS_SHEET_ID, rng, [values])


def build_event_row(
    *,
    tsu: str,
    tsj: str,
    request_id: str,
    user_hash: str,
    query_raw: str,
    query_norm: str,
    expanded_used: List[str],
    syn_applied: List[str],
    match_detail: str,
    routing_department: str,
    source: str,
    searched_departments: List[str],
    hit_department: str,
    hit_row_id: str,
    candidates: List[str],
    selection_id: str,
    solved: str,
    client_version: str,
    rate_limit_status: str,
    error_code: str,
    meta: Dict[str, Any],
) -> List[Any]:
    return [
        uuid.uuid4().hex,
        tsu,
        tsj,
        request_id,
        user_hash,
        query_raw,
        query_norm,
        json.dumps(expanded_used or [], ensure_ascii=False),
        json.dumps(syn_applied or [], ensure_ascii=False),
        match_detail or "",
        routing_department or "",
        source or "",
        json.dumps(searched_departments or [], ensure_ascii=False),
        hit_department or "",
        hit_row_id or "",
        json.dumps(candidates or [], ensure_ascii=False),
        selection_id or "",
        solved or "unknown",
        client_version or "",
        rate_limit_status or "",
        error_code or "",
        json.dumps(meta or {}, ensure_ascii=False),
    ]


def maybe_log_unresolved(
    request_id: str,
    tsj: str,
    department_guess: str,
    query: str,
    candidates_ids: List[str],
    searched_departments: List[str],
    user_feedback: str,
    client_version: str,
    selection_id: str,
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    if UNRESOLVED_SHEET_ID.strip() == "":
        return ""
    if not request_id:
        return ""
    try:
        if unresolved_already_logged(request_id):
            return ""

        query_masked = mask_and_summarize_query(query)
        candidates_json = json.dumps(candidates_ids or [], ensure_ascii=False)
        searched_json = json.dumps(searched_departments or [], ensure_ascii=False)

        notes_parts: List[str] = []
        if searched_departments:
            notes_parts.append(f"searched={searched_json}")
        if client_version:
            notes_parts.append(f"client={client_version}")
        if selection_id:
            notes_parts.append(f"selection_id={selection_id}")
        if meta:
            qn = str(meta.get("query_norm") or "").strip()
            if qn:
                notes_parts.append(f"q_norm={qn}")
                tks = tokenize_for_keyword(qn)
                if tks:
                    notes_parts.append(f"tok_sig={token_signature(tks)}")
            md = str(meta.get("match_detail") or "").strip()
            if md:
                notes_parts.append(f"match_detail={md}")
            routing = str(meta.get("routing_department") or "").strip()
            if routing:
                notes_parts.append(f"routing={routing}")
            exp = meta.get("expanded_used")
            if isinstance(exp, list) and exp:
                exp2 = [str(x) for x in exp if str(x).strip()]
                exp2 = exp2[:10]
                if exp2:
                    notes_parts.append(f"expanded={json.dumps(exp2, ensure_ascii=False)}")
            syn = meta.get("syn_applied")
            if isinstance(syn, list) and syn:
                syn2 = [str(x) for x in syn if str(x).strip()]
                syn2 = syn2[:10]
                if syn2:
                    notes_parts.append(f"syn_applied={json.dumps(syn2, ensure_ascii=False)}")
        notes = " / ".join(notes_parts)

        row = [
            request_id,
            tsj,
            department_guess or "",
            query_masked,
            candidates_json,
            user_feedback or "",
            "NEW",
            "",
            notes,
            "",
            "",
            "",
            "",
        ]

        append_unresolved_row(row)
        _unresolved_recent[request_id] = True
        return ""
    except Exception:
        return "unresolved_append_failed"


def build_allowed_origins() -> List[str]:
    origins = list(CORS_ORIGINS_ENV)
    if ENV == "dev":
        defaults = [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ]
        for o in defaults:
            if o not in origins:
                origins.append(o)
    if not origins and ENV == "dev":
        origins = ["http://127.0.0.1:5173", "http://localhost:5173"]
    return origins


def build_origin_regex() -> Optional[str]:
    if CORS_ORIGIN_REGEX_ENV:
        return CORS_ORIGIN_REGEX_ENV
    if ENV == "dev":
        return r"^chrome-extension://[a-p]{32}$"
    return None


_closed_requests = TTLCache(maxsize=50000, ttl=86400)


def new_request_id() -> str:
    return uuid.uuid4().hex


def ensure_request_id(rid: Optional[str]) -> str:
    s = (rid or "").strip()
    if s == "":
        return new_request_id()
    return s


def verify_google_and_get_subject(id_token_str: str) -> str:
    if not id_token_str or not str(id_token_str).strip():
        raise HTTPException(status_code=401, detail="missing id_token")

    if not GOOGLE_OAUTH_CLIENT_ID or GOOGLE_OAUTH_CLIENT_ID.strip() == "":
        raise HTTPException(status_code=500, detail="GOOGLE_OAUTH_CLIENT_ID is required for id_token mode")

    try:
        req = google_requests.Request()
        info = google_id_token.verify_oauth2_token(
            id_token_str,
            req,
            audience=GOOGLE_OAUTH_CLIENT_ID
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"invalid id_token: {str(e)}")

    if not info.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")

    hd = str(info.get("hd") or "").strip().lower()

    if not hd:
        raise HTTPException(status_code=403, detail="Personal accounts are not allowed. Only Google Workspace accounts are permitted.")

    if GOOGLE_ALLOWED_DOMAINS:
        if hd not in set(GOOGLE_ALLOWED_DOMAINS):
            raise HTTPException(status_code=403, detail="Domain not authorized.")

    sub = str(info.get("sub") or "").strip()
    if not sub:
        raise HTTPException(status_code=401, detail="invalid id_token sub")

    return sub


def _http_get_json(url: str, headers: Dict[str, str], timeout: int = 10) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError:
        raise HTTPException(status_code=401, detail="invalid access_token")
    except Exception:
        raise HTTPException(status_code=401, detail="invalid access_token")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=build_allowed_origins(),
    allow_origin_regex=build_origin_regex(),
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True, "env": ENV, "auth_mode": AUTH_MODE}


@app.get("/health")
def health():
    return {"ok": True, "env": ENV, "auth_mode": AUTH_MODE}


def _ms_since(t0: float) -> int:
    try:
        return int((time.time() - t0) * 1000.0)
    except Exception:
        return 0


def _pick_event_tab(tab_hint: str, source: str) -> str:
    if tab_hint and str(tab_hint).strip():
        return str(tab_hint).strip()
    if not EVENTS_SPLIT_TABS:
        return EVENTS_SHEET_TAB
    s = (source or "").strip()
    if s == "auth_exchange" or s == "auth_refresh" or s == "auth_logout" or s == "auth_relog":
        return EVENTS_TAB_AUTH
    if s == "app_event":
        return EVENTS_TAB_APP
    return EVENTS_TAB_API


def safe_append_event_row(values: List[Any], *, source: str = "", tab_hint: str = "") -> str:
    if not EVENTS_SHEET_ID:
        audit_log(
            {
                "log_type": "events_error",
                "error_code": "events_disabled",
                "reason": "EVENTS_SHEET_ID is empty",
                "source": source,
                "tab_hint": tab_hint,
            }
        )
        return "events_disabled"

    primary = _pick_event_tab(tab_hint, source)

    try:
        append_event_row(values, primary)
        return ""
    except Exception as e1:
        audit_log(
            {
                "log_type": "events_error",
                "error_code": "events_append_failed",
                "phase": "append_primary",
                "source": source,
                "tab": primary,
                "sheet_id": EVENTS_SHEET_ID,
                "append_range": EVENTS_APPEND_RANGE,
                "values_len": len(values) if isinstance(values, list) else None,
                "exc": repr(e1),
            }
        )

        try:
            if primary != EVENTS_SHEET_TAB:
                append_event_row(values, EVENTS_SHEET_TAB)
                return ""
        except Exception as e2:
            audit_log(
                {
                    "log_type": "events_error",
                    "error_code": "events_append_failed",
                    "phase": "append_fallback",
                    "source": source,
                    "tab": EVENTS_SHEET_TAB,
                    "sheet_id": EVENTS_SHEET_ID,
                    "append_range": EVENTS_APPEND_RANGE,
                    "values_len": len(values) if isinstance(values, list) else None,
                    "exc": repr(e2),
                }
            )

        return "events_append_failed"


@app.post("/api/auth/exchange", response_model=AuthResponse)
def auth_exchange(req: AuthRequest):
    t0 = time.time()
    tsu, tsj = now_utc_iso(), now_jst_iso()
    rid = new_request_id()

    subject: str = ""
    user_hash: str = ""
    mode = AUTH_MODE

    if mode not in ("auto", "google", "dev"):
        mode = "auto"

    can_use_google = GOOGLE_OAUTH_CLIENT_ID.strip() != ""
    has_id_token = bool(getattr(req, "id_token", None) and str(getattr(req, "id_token", "")).strip())

    try:
        if mode == "google":
            if has_id_token:
                subject = verify_google_and_get_subject(req.id_token)
            else:
                raise HTTPException(status_code=401, detail="id_token required")

        elif mode == "auto":
            if has_id_token and can_use_google:
                subject = verify_google_and_get_subject(req.id_token)
            else:
                if ENV != "dev":
                    raise HTTPException(status_code=403, detail="OAuth required in production. Check configuration.")
                subject = str(req.user_id or "").strip()
                if subject == "":
                    raise HTTPException(status_code=401, detail="user_id required")
        else:
            if ENV != "dev":
                raise HTTPException(status_code=403, detail="dev-mode auth blocked in production")
            subject = str(req.user_id or "").strip()
            if subject == "":
                raise HTTPException(status_code=401, detail="user_id required")

        user_hash = hash_subject(subject)
        token = issue_jwt_for_user_hash(user_hash)

        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=user_hash,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_exchange",
                routing_department="",
                source="auth_exchange",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version=str(getattr(req, "client_version", "") or ""),
                rate_limit_status="n/a",
                error_code="",
                meta={
                    "kind": "auth_exchange",
                    "endpoint": "/api/auth/exchange",
                    "status_code": 200,
                    "duration_ms": _ms_since(t0),
                    "auth_mode": mode,
                    "can_use_google": can_use_google,
                    "has_id_token": has_id_token,
                    "sv": get_session_version(user_hash),
                    "result": "ok",
                },
            ),
            source="auth_exchange",
        )

        return {"token": token, "expires_in_seconds": int(JWT_TTL_SECONDS)}

    except HTTPException as e:
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=user_hash,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_exchange",
                routing_department="",
                source="auth_exchange",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version=str(getattr(req, "client_version", "") or ""),
                rate_limit_status="n/a",
                error_code=f"http_{e.status_code}",
                meta={
                    "kind": "auth_exchange",
                    "endpoint": "/api/auth/exchange",
                    "status_code": e.status_code,
                    "duration_ms": _ms_since(t0),
                    "auth_mode": mode,
                    "can_use_google": can_use_google,
                    "has_id_token": has_id_token,
                    "result": "http_error",
                },
            ),
            source="auth_exchange",
        )
        raise

    except Exception:
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=user_hash,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_exchange",
                routing_department="",
                source="auth_exchange",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version=str(getattr(req, "client_version", "") or ""),
                rate_limit_status="n/a",
                error_code="internal_error",
                meta={
                    "kind": "auth_exchange",
                    "endpoint": "/api/auth/exchange",
                    "status_code": 500,
                    "duration_ms": _ms_since(t0),
                    "auth_mode": mode,
                    "can_use_google": can_use_google,
                    "has_id_token": has_id_token,
                    "result": "exception",
                },
            ),
            source="auth_exchange",
        )
        raise HTTPException(status_code=500, detail="internal error")


@app.post("/api/auth/refresh", response_model=AuthResponse)
def auth_refresh(authorization: str = Header(default="")):
    t0 = time.time()
    tsu, tsj = now_utc_iso(), now_jst_iso()
    rid = new_request_id()
    user_hash = ""
    try:
        payload = verify_bearer(authorization)
        sub = str(payload.get("sub") or "").strip()
        if not sub:
            raise HTTPException(status_code=401, detail="invalid token sub")
        user_hash = sub

        token = issue_jwt_for_user_hash(sub)

        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=sub,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_refresh",
                routing_department="",
                source="auth_refresh",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code="",
                meta={
                    "kind": "auth_refresh",
                    "endpoint": "/api/auth/refresh",
                    "status_code": 200,
                    "duration_ms": _ms_since(t0),
                    "sv": get_session_version(sub),
                    "result": "ok",
                },
            ),
            source="auth_refresh",
        )

        return {"token": token, "expires_in_seconds": int(JWT_TTL_SECONDS)}
    except HTTPException as e:
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=user_hash,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_refresh",
                routing_department="",
                source="auth_refresh",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code=f"http_{e.status_code}",
                meta={
                    "kind": "auth_refresh",
                    "endpoint": "/api/auth/refresh",
                    "status_code": e.status_code,
                    "duration_ms": _ms_since(t0),
                    "result": "http_error",
                },
            ),
            source="auth_refresh",
        )
        raise
    except Exception:
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=user_hash,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_refresh",
                routing_department="",
                source="auth_refresh",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code="internal_error",
                meta={
                    "kind": "auth_refresh",
                    "endpoint": "/api/auth/refresh",
                    "status_code": 500,
                    "duration_ms": _ms_since(t0),
                    "result": "exception",
                },
            ),
            source="auth_refresh",
        )
        raise HTTPException(status_code=500, detail="internal error")


@app.post("/api/auth/logout")
def auth_logout(authorization: str = Header(default="")):
    t0 = time.time()
    tsu, tsj = now_utc_iso(), now_jst_iso()
    rid = new_request_id()
    user_hash = ""
    try:
        payload = verify_bearer(authorization)
        sub = str(payload.get("sub") or "").strip()
        if not sub:
            raise HTTPException(status_code=401, detail="invalid token sub")
        user_hash = sub

        new_sv = bump_session_version(sub)

        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=sub,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_logout",
                routing_department="",
                source="auth_logout",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code="",
                meta={
                    "kind": "auth_logout",
                    "endpoint": "/api/auth/logout",
                    "status_code": 200,
                    "duration_ms": _ms_since(t0),
                    "new_sv": int(new_sv),
                    "result": "ok",
                },
            ),
            source="auth_logout",
        )

        return {"ok": True}
    except HTTPException as e:
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=user_hash,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_logout",
                routing_department="",
                source="auth_logout",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code=f"http_{e.status_code}",
                meta={
                    "kind": "auth_logout",
                    "endpoint": "/api/auth/logout",
                    "status_code": e.status_code,
                    "duration_ms": _ms_since(t0),
                    "result": "http_error",
                },
            ),
            source="auth_logout",
        )
        raise
    except Exception:
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=user_hash,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_logout",
                routing_department="",
                source="auth_logout",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code="internal_error",
                meta={
                    "kind": "auth_logout",
                    "endpoint": "/api/auth/logout",
                    "status_code": 500,
                    "duration_ms": _ms_since(t0),
                    "result": "exception",
                },
            ),
            source="auth_logout",
        )
        raise HTTPException(status_code=500, detail="internal error")


@app.post("/api/auth/relog")
def auth_relog(authorization: str = Header(default="")):
    t0 = time.time()
    tsu, tsj = now_utc_iso(), now_jst_iso()
    rid = new_request_id()
    user_hash = ""
    try:
        payload = verify_bearer(authorization)
        sub = str(payload.get("sub") or "").strip()
        if not sub:
            raise HTTPException(status_code=401, detail="invalid token sub")
        user_hash = sub

        new_sv = bump_session_version(sub)

        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=sub,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_relog",
                routing_department="",
                source="auth_relog",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code="",
                meta={
                    "kind": "auth_relog",
                    "endpoint": "/api/auth/relog",
                    "status_code": 200,
                    "duration_ms": _ms_since(t0),
                    "new_sv": int(new_sv),
                    "result": "ok",
                },
            ),
            source="auth_relog",
        )

        return {"ok": True}
    except HTTPException as e:
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=user_hash,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_relog",
                routing_department="",
                source="auth_relog",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code=f"http_{e.status_code}",
                meta={
                    "kind": "auth_relog",
                    "endpoint": "/api/auth/relog",
                    "status_code": e.status_code,
                    "duration_ms": _ms_since(t0),
                    "result": "http_error",
                },
            ),
            source="auth_relog",
        )
        raise
    except Exception:
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=user_hash,
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="auth_relog",
                routing_department="",
                source="auth_relog",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code="internal_error",
                meta={
                    "kind": "auth_relog",
                    "endpoint": "/api/auth/relog",
                    "status_code": 500,
                    "duration_ms": _ms_since(t0),
                    "result": "exception",
                },
            ),
            source="auth_relog",
        )
        raise HTTPException(status_code=500, detail="internal error")


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, bg_tasks: BackgroundTasks, authorization: str = Header(default="")):
    t0 = time.time()
    payload = verify_bearer(authorization)
    sub = payload.get("sub", "")

    if hash_subject(req.user_id) != sub:
        raise HTTPException(status_code=401, detail="user mismatch")

    rid = ensure_request_id(req.request_id)
    if rid in _closed_requests:
        raise HTTPException(status_code=409, detail="request closed; issue new request_id")

    rl = check_rate_limit(sub, limit_per_minute=RATE_LIMIT_PER_MIN)
    tsu, tsj = now_utc_iso(), now_jst_iso()

    source = "error"
    answer = ""
    candidates: List[Dict[str, Any]] = []
    hit_dept = ""
    hit_row = ""
    searched: List[str] = []
    guidance = ""
    error_code = ""
    routing_department = ""

    query_norm = normalize_q(req.query)
    expanded_used: List[str] = []
    syn_applied: List[str] = []
    match_detail = ""

    tokens = tokenize_for_keyword(query_norm)
    tok_sig = token_signature(tokens)

    try:
        if req.selection_id:
            resolved = resolve_candidate(req.selection_id)
            source = "keyword"
            answer = resolved["answer"]
            hit_dept = resolved["hit_department"]
            hit_row = resolved["hit_row_id"]
            candidates = []
            searched = []
            routing_department = choose_routing_department(source, hit_dept, candidates, searched, query_norm=query_norm)
            match_detail = "selected_candidate"
            expanded_used = [query_norm] if query_norm else []
        else:
            res = search_all_departments(req.query, exclude_ids=req.exclude_ids)
            source = res["source"]
            candidates = res["candidates"]
            answer = res["answer"]
            hit_dept = res["hit_department"]
            hit_row = res["hit_row_id"]
            searched = res["searched_departments"]
            routing_department = str(res.get("routing_department") or "")
            query_norm = str(res.get("query_norm") or query_norm)
            expanded_used = list(res.get("expanded_used") or [])
            syn_applied = list(res.get("syn_applied") or [])
            match_detail = str(res.get("match_detail") or "")

            tokens = tokenize_for_keyword(query_norm)
            tok_sig = token_signature(tokens)

        if not routing_department:
            routing_department = guess_department_by_keyword(query_norm) or FALLBACK_DEPT_KEY

        if source == "candidate":
            guidance = "候補から選んでください。どれも違う場合は「該当なし」を選択してください。"
        elif source == "none":
            routing_department = choose_routing_department("none", "", [], searched, query_norm=query_norm)
            dept_info = DEPT_DISPLAY.get(routing_department, {})
            dept_name = dept_info.get("name", "総務")
            guidance = unresolved_guidance_text(dept_name)

        if source == "none":
            dept_guess = routing_department or guess_department_by_keyword(query_norm) or FALLBACK_DEPT_KEY

            bg_tasks.add_task(
                maybe_log_unresolved,
                request_id=rid,
                tsj=tsj,
                department_guess=dept_guess,
                query=req.query,
                candidates_ids=[],
                searched_departments=searched,
                user_feedback="none",
                client_version=req.client_version or "",
                selection_id=req.selection_id or "",
                meta={
                    "query_norm": query_norm,
                    "expanded_used": expanded_used,
                    "syn_applied": syn_applied,
                    "match_detail": match_detail or "none",
                    "routing_department": dept_guess,
                },
            )

        audit_log(
            {
                "log_type": "audit",
                "request_id": rid,
                "timestamp_utc": tsu,
                "timestamp_jst": tsj,
                "user_hash": sub,
                "query_raw": req.query,
                "query_norm": query_norm,
                "token_sig": tok_sig,
                "expanded_used": expanded_used,
                "syn_applied": syn_applied,
                "match_detail": match_detail,
                "routing_department": routing_department,
                "source": source,
                "searched_departments": searched,
                "hit_department": hit_dept,
                "hit_row_id": hit_row,
                "candidates": [c.get("id") for c in candidates] if candidates else [],
                "selection_id": req.selection_id or "",
                "solved": "unknown",
                "client_version": req.client_version,
                "rate_limit_status": rl,
                "error_code": error_code,
            }
        )

        bg_tasks.add_task(
            safe_append_event_row,
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=sub,
                query_raw=(req.query if EVENTS_STORE_QUERY_RAW else ""),
                query_norm=query_norm,
                expanded_used=expanded_used,
                syn_applied=syn_applied,
                match_detail=match_detail,
                routing_department=routing_department,
                source=source,
                searched_departments=searched,
                hit_department=hit_dept,
                hit_row_id=hit_row,
                candidates=[c.get("id") for c in candidates] if candidates else [],
                selection_id=req.selection_id or "",
                solved="unknown",
                client_version=req.client_version or "",
                rate_limit_status=rl,
                error_code="",
                meta={
                    "kind": "api_chat",
                    "endpoint": "/api/chat",
                    "status_code": 200,
                    "duration_ms": _ms_since(t0),
                    "token_sig": tok_sig,
                    "query_summary_masked": mask_and_summarize_query(req.query or ""),
                    "candidate_count": len(candidates) if candidates else 0,
                },
            ),
            source=source,
        )

        return {
            "request_id": rid,
            "source": source,
            "candidates": candidates,
            "answer": answer,
            "guidance": guidance,
            "routing_department": routing_department,
            "hit_department": hit_dept,
            "hit_row_id": str(hit_row),
        }

    except HTTPException as e:
        bg_tasks.add_task(
            safe_append_event_row,
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=sub,
                query_raw=(req.query if EVENTS_STORE_QUERY_RAW else ""),
                query_norm=query_norm,
                expanded_used=expanded_used,
                syn_applied=syn_applied,
                match_detail=match_detail,
                routing_department=routing_department or "",
                source="error",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id=req.selection_id or "",
                solved="unknown",
                client_version=req.client_version or "",
                rate_limit_status=rl,
                error_code=f"http_{e.status_code}",
                meta={
                    "kind": "api_chat",
                    "endpoint": "/api/chat",
                    "status_code": e.status_code,
                    "duration_ms": _ms_since(t0),
                    "error_type": "http",
                    "token_sig": tok_sig,
                    "query_summary_masked": mask_and_summarize_query(req.query or ""),
                },
            ),
            source="error",
        )

        audit_log(
            {
                "log_type": "audit",
                "request_id": rid,
                "timestamp_utc": tsu,
                "timestamp_jst": tsj,
                "user_hash": sub,
                "query_raw": req.query,
                "query_norm": query_norm,
                "token_sig": tok_sig,
                "expanded_used": expanded_used,
                "syn_applied": syn_applied,
                "match_detail": match_detail,
                "routing_department": routing_department,
                "source": "error",
                "searched_departments": [],
                "hit_department": "",
                "hit_row_id": "",
                "candidates": [],
                "selection_id": req.selection_id or "",
                "solved": "unknown",
                "client_version": req.client_version,
                "rate_limit_status": rl,
                "error_code": f"http_{e.status_code}",
            }
        )
        raise

    except Exception:
        bg_tasks.add_task(
            safe_append_event_row,
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash=sub,
                query_raw=(req.query if EVENTS_STORE_QUERY_RAW else ""),
                query_norm=query_norm,
                expanded_used=expanded_used,
                syn_applied=syn_applied,
                match_detail=match_detail,
                routing_department=routing_department or "",
                source="error",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id=req.selection_id or "",
                solved="unknown",
                client_version=req.client_version or "",
                rate_limit_status=rl,
                error_code="internal_error",
                meta={
                    "kind": "api_chat",
                    "endpoint": "/api/chat",
                    "status_code": 500,
                    "duration_ms": _ms_since(t0),
                    "error_type": "exception",
                    "token_sig": tok_sig,
                    "query_summary_masked": mask_and_summarize_query(req.query or ""),
                },
            ),
            source="error",
        )

        audit_log(
            {
                "log_type": "audit",
                "request_id": rid,
                "timestamp_utc": tsu,
                "timestamp_jst": tsj,
                "user_hash": sub,
                "query_raw": req.query,
                "query_norm": query_norm,
                "token_sig": tok_sig,
                "expanded_used": expanded_used,
                "syn_applied": syn_applied,
                "match_detail": match_detail,
                "routing_department": routing_department,
                "source": "error",
                "searched_departments": [],
                "hit_department": "",
                "hit_row_id": "",
                "candidates": [],
                "selection_id": req.selection_id or "",
                "solved": "unknown",
                "client_version": req.client_version,
                "rate_limit_status": rl,
                "error_code": "internal_error",
            }
        )
        raise HTTPException(status_code=500, detail="internal error")


def _routing_from_candidate_ids(candidate_ids: List[str], query_norm: str = "") -> str:
    if not candidate_ids:
        return guess_department_by_keyword(query_norm) or FALLBACK_DEPT_KEY

    depts: List[str] = []
    for cid in candidate_ids:
        s = str(cid or "").strip()
        if ":" in s:
            dk = s.split(":", 1)[0].strip()
            if dk:
                depts.append(dk)

    return choose_candidate_routing(depts, query_norm=query_norm)


def _dept_from_selection_id(selection_id: str) -> str:
    s = str(selection_id or "").strip()
    if ":" in s:
        dk = s.split(":", 1)[0].strip()
        if dk:
            return dk
    return ""


@app.post("/api/feedback")
def feedback(req: FeedbackRequest, bg_tasks: BackgroundTasks, authorization: str = Header(default="")):
    t0 = time.time()
    payload = verify_bearer(authorization)
    sub = payload.get("sub", "")

    if hash_subject(req.user_id) != sub:
        raise HTTPException(status_code=401, detail="user mismatch")

    tsu, tsj = now_utc_iso(), now_jst_iso()
    solved_val = "true" if req.solved is True else ("false" if req.solved is False else "unknown")
    query_norm = normalize_q(req.query or "")
    tokens = tokenize_for_keyword(query_norm)
    tok_sig = token_signature(tokens)
    error_code = ""

    need_unresolved = (req.solved is False) or (req.user_feedback in ("not_match", "not_solved", "none"))

    if req.solved is True:
        _closed_requests[req.request_id] = True

    routing_department = ""
    if need_unresolved:
        if req.candidates_ids:
            routing_department = _routing_from_candidate_ids(req.candidates_ids, query_norm=query_norm)
        else:
            dk = _dept_from_selection_id(req.selection_id or "")
            if dk:
                routing_department = dk
            else:
                routing_department = guess_department_by_keyword(query_norm) or FALLBACK_DEPT_KEY

    dept_guess = routing_department or guess_department_by_keyword(query_norm) or FALLBACK_DEPT_KEY

    bg_tasks.add_task(
        maybe_log_unresolved,
        request_id=req.request_id,
        tsj=tsj,
        department_guess=dept_guess,
        query=req.query or "",
        candidates_ids=req.candidates_ids or [],
        searched_departments=req.searched_departments or [],
        user_feedback=req.user_feedback or "feedback",
        client_version=req.client_version or "unknown",
        selection_id=req.selection_id or "",
        meta={
            "query_norm": query_norm,
            "match_detail": "feedback",
            "routing_department": dept_guess,
        },
    )

    audit_log(
        {
            "log_type": "audit",
            "request_id": req.request_id,
            "timestamp_utc": tsu,
            "timestamp_jst": tsj,
            "user_hash": sub,
            "query_raw": req.query or "",
            "query_norm": query_norm,
            "token_sig": tok_sig,
            "routing_department": routing_department if need_unresolved else "",
            "source": "feedback",
            "searched_departments": req.searched_departments or [],
            "hit_department": "",
            "hit_row_id": "",
            "candidates": req.candidates_ids or [],
            "selection_id": req.selection_id or "",
            "solved": solved_val,
            "client_version": req.client_version or "unknown",
            "rate_limit_status": "n/a",
            "error_code": error_code,
        }
    )

    bg_tasks.add_task(
        safe_append_event_row,
        build_event_row(
            tsu=tsu,
            tsj=tsj,
            request_id=req.request_id,
            user_hash=sub,
            query_raw=(req.query if EVENTS_STORE_QUERY_RAW else ""),
            query_norm=query_norm,
            expanded_used=[],
            syn_applied=[],
            match_detail="feedback",
            routing_department=(routing_department if need_unresolved else ""),
            source="feedback",
            searched_departments=req.searched_departments or [],
            hit_department="",
            hit_row_id="",
            candidates=req.candidates_ids or [],
            selection_id=req.selection_id or "",
            solved=solved_val,
            client_version=req.client_version or "unknown",
            rate_limit_status="n/a",
            error_code=error_code,
            meta={
                "kind": "api_feedback",
                "endpoint": "/api/feedback",
                "status_code": 200,
                "duration_ms": _ms_since(t0),
                "token_sig": tok_sig,
                "need_unresolved": need_unresolved,
                "user_feedback": req.user_feedback or "",
                "query_summary_masked": mask_and_summarize_query(req.query or ""),
            },
        ),
        source="feedback",
    )

    return {"ok": True}


class AppEventRequest(BaseModel):
    request_id: Optional[str] = Field(default=None)
    user_id: str = Field(...)
    event_name: str = Field(...)
    client_version: Optional[str] = Field(default=None)
    meta: Optional[Dict[str, Any]] = Field(default=None)


@app.post("/api/events/app")
def app_event(req: AppEventRequest, authorization: str = Header(default="")):
    t0 = time.time()
    payload = verify_bearer(authorization)
    sub = payload.get("sub", "")
    if hash_subject(req.user_id) != sub:
        raise HTTPException(status_code=401, detail="user mismatch")

    rid = ensure_request_id(req.request_id)
    rl = check_rate_limit(sub, limit_per_minute=RATE_LIMIT_PER_MIN)

    tsu, tsj = now_utc_iso(), now_jst_iso()
    safe_append_event_row(
        build_event_row(
            tsu=tsu,
            tsj=tsj,
            request_id=rid,
            user_hash=sub,
            query_raw="",
            query_norm="",
            expanded_used=[],
            syn_applied=[],
            match_detail="app_event",
            routing_department="",
            source="app_event",
            searched_departments=[],
            hit_department="",
            hit_row_id="",
            candidates=[],
            selection_id="",
            solved="unknown",
            client_version=str(req.client_version or ""),
            rate_limit_status=rl,
            error_code="",
            meta={
                "kind": "app_event",
                "endpoint": "/api/events/app",
                "status_code": 200,
                "duration_ms": _ms_since(t0),
                "event_name": req.event_name,
                "meta": req.meta or {},
            },
        ),
        source="app_event",
    )
    return {"ok": True}


@app.post("/admin/cache/refresh")
def admin_cache_refresh(
    request: Request,
    department: Optional[str] = None,
    x_admin_token: str = Header(default="", alias="X-Admin-Token"),
    x_admin_actor: str = Header(default="", alias="X-Admin-Actor"),
):
    t0 = time.time()
    tsu, tsj = now_utc_iso(), now_jst_iso()
    rid = new_request_id()

    actor = str(x_admin_actor or "").strip()
    client_host = str(getattr(getattr(request, "client", None), "host", "") or "")
    user_agent = str(request.headers.get("user-agent") or "")
    xff_raw = str(request.headers.get("x-forwarded-for") or "")
    client_ip = (xff_raw.split(",")[0].strip() if xff_raw else "") or client_host
    client_ip_is_public = False
    try:
        import ipaddress
        if client_ip:
            ip = ipaddress.ip_address(client_ip)
            client_ip_is_public = not (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            )
    except Exception:
        pass

    if not ADMIN_TOKEN:
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash="admin",
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="admin_cache_refresh",
                routing_department="",
                source="admin_refresh",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code="admin_token_not_configured",
                meta={
                    "kind": "admin_cache_refresh",
                    "endpoint": "/admin/cache/refresh",
                    "status_code": 500,
                    "duration_ms": _ms_since(t0),
                    "department": (department or ""),
                    "admin_actor": actor,
                    "client_host": client_host,
                    "result": "admin_token_not_configured",
                },
            ),
            source="admin_refresh",
        )
        raise HTTPException(
            status_code=500,
            detail="ADMIN_TOKEN is not configured. Set Cloud Run env var ADMIN_TOKEN (or Secret) and redeploy.",
        )

    if not x_admin_token or str(x_admin_token).strip() == "":
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash="admin",
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="admin_cache_refresh",
                routing_department="",
                source="admin_refresh",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code="missing_admin_token",
                meta={
                    "kind": "admin_cache_refresh",
                    "endpoint": "/admin/cache/refresh",
                    "status_code": 401,
                    "duration_ms": _ms_since(t0),
                    "department": (department or ""),
                    "admin_actor": actor,
                    "client_host": client_host,
                    "client_ip": client_ip,
                    "client_ip_is_public": client_ip_is_public,
                    "xff_raw": xff_raw,
                    "user_agent": user_agent,
                    "security_alert": True,
                    "alert_reason": "missing_admin_token",
                    "result": "missing_admin_token",
                },
            ),
            source="admin_refresh",
        )
        raise HTTPException(
            status_code=401,
            detail="Missing header: X-Admin-Token. Provide the admin token in request header.",
        )

    import hmac

    expected = str(ADMIN_TOKEN or "").strip()
    got = str(x_admin_token or "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN is not configured")

    if not hmac.compare_digest(got, expected):
        safe_append_event_row(
            build_event_row(
                tsu=tsu,
                tsj=tsj,
                request_id=rid,
                user_hash="admin",
                query_raw="",
                query_norm="",
                expanded_used=[],
                syn_applied=[],
                match_detail="admin_cache_refresh",
                routing_department="",
                source="admin_refresh",
                searched_departments=[],
                hit_department="",
                hit_row_id="",
                candidates=[],
                selection_id="",
                solved="unknown",
                client_version="",
                rate_limit_status="n/a",
                error_code="forbidden_admin_token",
                meta={
                    "kind": "admin_cache_refresh",
                    "endpoint": "/admin/cache/refresh",
                    "status_code": 403,
                    "duration_ms": _ms_since(t0),
                    "department": (department or ""),
                    "admin_actor": actor,
                    "client_host": client_host,
                    "client_ip": client_ip,
                    "client_ip_is_public": client_ip_is_public,
                    "xff_raw": xff_raw,
                    "user_agent": user_agent,
                    "security_alert": True,
                    "alert_reason": "forbidden_admin_token",
                    "result": "forbidden_admin_token",
                },
            ),
            source="admin_refresh",
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid X-Admin-Token (forbidden). Check the token value and Cloud Run ADMIN_TOKEN.",
        )

    result = admin_refresh_cache(department)

    safe_append_event_row(
        build_event_row(
            tsu=tsu,
            tsj=tsj,
            request_id=rid,
            user_hash="admin",
            query_raw="",
            query_norm="",
            expanded_used=[],
            syn_applied=[],
            match_detail="admin_cache_refresh",
            routing_department="",
            source="admin_refresh",
            searched_departments=[],
            hit_department="",
            hit_row_id="",
            candidates=[],
            selection_id="",
            solved="unknown",
            client_version="",
            rate_limit_status="n/a",
            error_code="",
            meta={
                "kind": "admin_cache_refresh",
                "endpoint": "/admin/cache/refresh",
                "status_code": 200,
                "duration_ms": _ms_since(t0),
                "department": (department or ""),
                "admin_actor": actor,
                "client_host": client_host,
                "refreshed": result.get("refreshed", []),
                "skipped": result.get("skipped", []),
                "refreshed_count": len(result.get("refreshed", []) or []),
                "skipped_count": len(result.get("skipped", []) or []),
                "result": "ok",
            },
        ),
        source="admin_refresh",
    )

    return result
