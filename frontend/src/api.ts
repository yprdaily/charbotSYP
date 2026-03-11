type CorpBotConfig = {
  API_BASE: string;
  CLIENT_VERSION: string;
  ID_TOKEN?: string;
  OAUTH_CLIENT_ID?: string;
  OAUTH_SCOPES?: string[];
};

declare global {
  interface Window {
    CORPBOT_CONFIG?: Partial<CorpBotConfig>;
  }
}

declare const chrome: any;

function getConfig(): CorpBotConfig {
  const cfg = window.CORPBOT_CONFIG || {};
  return {
    API_BASE: cfg.API_BASE || "http://127.0.0.1:8000",
    CLIENT_VERSION: cfg.CLIENT_VERSION || "ext-dev",
    ID_TOKEN: cfg.ID_TOKEN ? String(cfg.ID_TOKEN) : undefined,
    OAUTH_CLIENT_ID: cfg.OAUTH_CLIENT_ID ? String(cfg.OAUTH_CLIENT_ID) : undefined,
    OAUTH_SCOPES: Array.isArray(cfg.OAUTH_SCOPES) ? cfg.OAUTH_SCOPES.map(String) : undefined
  };
}

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(`api failed: ${status} ${body}`);
    this.status = status;
    this.body = body;
  }
}

export class AuthRequiredError extends Error {
  constructor(message = "login_required") {
    super(message);
    this.name = "AuthRequiredError";
  }
}

type AuthState = {
  idToken: string;
  userId: string;
  email?: string;
  expMs: number;
};

const SKEY_ID_TOKEN = "corpbot_id_token";
const SKEY_USER_ID = "corpbot_user_id";
const SKEY_EMAIL = "corpbot_user_email";
const SKEY_IDEXP = "corpbot_id_token_exp_ms";
const SKEY_JWT = "corpbot_jwt";
const SKEY_JWTEXP = "corpbot_jwt_exp_ms";
const SKEY_INTERACTIVE_AT = "corpbot_interactive_login_at_ms";

let memJwt: string | null = null;
let memJwtExpMs = 0;
let memAuth: AuthState | null = null;

const AUTH_SKEW_MS = 10_000;
const JWT_FALLBACK_TTL_MS = 12 * 60 * 60 * 1000;
const JWT_REFRESH_BEFORE_MS = 10 * 60 * 1000;
const INTERACTIVE_SESSION_TTL_MS = 12 * 60 * 60 * 1000;

function nowMs(): number {
  return Date.now();
}

function hasChromeSessionStorage(): boolean {
  try {
    return !!chrome?.storage?.session?.get;
  } catch {
    return false;
  }
}

function hasWebSessionStorage(): boolean {
  try {
    return typeof sessionStorage !== "undefined" && !!sessionStorage?.getItem;
  } catch {
    return false;
  }
}

async function sessionGet<T = any>(key: string): Promise<T | undefined> {
  if (hasChromeSessionStorage()) {
    try {
      const obj = await chrome.storage.session.get(key);
      return obj ? (obj[key] as T) : undefined;
    } catch {}
  }

  if (hasWebSessionStorage()) {
    try {
      const raw = sessionStorage.getItem(key);
      if (raw == null) return undefined;
      return JSON.parse(raw) as T;
    } catch {
      try {
        const raw = sessionStorage.getItem(key);
        return (raw as any) as T;
      } catch {}
    }
  }

  return undefined;
}

async function sessionSet(key: string, value: any): Promise<void> {
  if (hasChromeSessionStorage()) {
    try {
      await chrome.storage.session.set({ [key]: value });
      return;
    } catch {}
  }

  if (hasWebSessionStorage()) {
    try {
      sessionStorage.setItem(key, JSON.stringify(value));
    } catch {
      try {
        sessionStorage.setItem(key, String(value));
      } catch {}
    }
  }
}

async function sessionRemove(keys: string[]): Promise<void> {
  if (hasChromeSessionStorage()) {
    try {
      await chrome.storage.session.remove(keys);
    } catch {}
  }

  if (hasWebSessionStorage()) {
    try {
      keys.forEach((k) => {
        try {
          sessionStorage.removeItem(k);
        } catch {}
      });
    } catch {}
  }
}

function base64UrlDecodeToJson(seg: string): any {
  const b64 = seg.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((seg.length + 3) % 4);
  const bin = atob(b64);
  const json = decodeURIComponent(
    Array.prototype
      .map
      .call(bin, (c: string) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
      .join("")
  );
  return JSON.parse(json);
}

function tryParseJwtPayload(token: string): any | null {
  try {
    const parts = String(token || "").split(".");
    if (parts.length !== 3) return null;
    return base64UrlDecodeToJson(parts[1]);
  } catch {
    return null;
  }
}

function getJwtExpMs(token: string): number {
  const payload = tryParseJwtPayload(token);
  const expSec = Number(payload?.exp || 0);
  return expSec ? expSec * 1000 : 0;
}

function getIdTokenExpMs(idToken: string): number {
  const payload = tryParseJwtPayload(idToken);
  const expSec = Number(payload?.exp || 0);
  return expSec ? expSec * 1000 : 0;
}

function getIdTokenSub(idToken: string): string {
  const payload = tryParseJwtPayload(idToken);
  return String(payload?.sub || "").trim();
}

function getIdTokenEmail(idToken: string): string {
  const payload = tryParseJwtPayload(idToken);
  return String(payload?.email || "").trim();
}

function joinUrl(base: string, path: string): string {
  const b = String(base || "").replace(/\/+$/, "");
  const p = String(path || "");
  if (!p) return b;
  return p.startsWith("/") ? b + p : b + "/" + p;
}

async function readBodyText(res: Response): Promise<string> {
  try {
    return await res.text();
  } catch {
    return "";
  }
}

function canUseChromeRuntime(): boolean {
  try {
    return !!chrome?.runtime?.sendMessage;
  } catch {
    return false;
  }
}

function sendRuntimeMessage<TReq extends Record<string, any>, TRes = any>(msg: TReq): Promise<TRes> {
  return new Promise((resolve, reject) => {
    try {
      chrome.runtime.sendMessage(msg, (resp: any) => {
        const err = chrome.runtime?.lastError?.message;
        if (err) {
          reject(new Error(err));
          return;
        }
        resolve(resp as TRes);
      });
    } catch (e: any) {
      reject(e);
    }
  });
}

function isInteractionRequiredErrorMessage(msg: string): boolean {
  const m = String(msg || "").toLowerCase();
  return (
    m.includes("interaction required") ||
    m.includes("interaction_required") ||
    m.includes("user interaction required") ||
    m.includes("login_required") ||
    m.includes("consent_required")
  );
}

async function getIdTokenFromBackground(interactive: boolean): Promise<AuthState> {
  if (!canUseChromeRuntime()) {
    throw new Error("chrome.runtime is not available");
  }

  const resp = (await sendRuntimeMessage({ type: "CORPBOT_GET_ID_TOKEN", interactive })) as any;

  if (!resp?.ok) {
    const errMsg = String(resp?.error || "CORPBOT_GET_ID_TOKEN_failed");
    if (!interactive && isInteractionRequiredErrorMessage(errMsg)) {
      throw new AuthRequiredError();
    }
    throw new Error(errMsg);
  }

  const idToken = String(resp.id_token || "").trim();
  const sub = String(resp.sub || "").trim();
  const email = String(resp.email || "").trim();
  const expSec = Number(resp.exp || 0);

  if (!idToken || !sub) throw new Error("invalid_id_token_response");

  const expMs = expSec ? expSec * 1000 : getIdTokenExpMs(idToken) || nowMs() + 2 * 60 * 60 * 1000;
  return { idToken, userId: sub, email: email || undefined, expMs };
}

async function readInteractiveAtMs(): Promise<number> {
  return Number((await sessionGet<number>(SKEY_INTERACTIVE_AT)) || 0);
}

function isInteractiveWindowValid(interactiveAtMs: number): boolean {
  if (!interactiveAtMs) return false;
  return nowMs() < interactiveAtMs + INTERACTIVE_SESSION_TTL_MS - AUTH_SKEW_MS;
}

async function requireInteractiveIfWindowExpired(interactive: boolean): Promise<void> {
  if (interactive) return;
  const at = await readInteractiveAtMs();
  if (!at) return;
  if (!isInteractiveWindowValid(at)) {
    throw new AuthRequiredError();
  }
}

async function ensureAuth(opts?: { interactive?: boolean }): Promise<AuthState> {
  const interactive = Boolean(opts?.interactive);

  await requireInteractiveIfWindowExpired(interactive);

  if (memAuth && nowMs() < memAuth.expMs - AUTH_SKEW_MS) return memAuth;

  const storedIdToken = (await sessionGet<string>(SKEY_ID_TOKEN)) || "";
  const storedUserId = (await sessionGet<string>(SKEY_USER_ID)) || "";
  const storedEmail = (await sessionGet<string>(SKEY_EMAIL)) || "";
  const storedExpMs = Number((await sessionGet<number>(SKEY_IDEXP)) || 0);

  if (storedIdToken && storedUserId && storedExpMs && nowMs() < storedExpMs - AUTH_SKEW_MS) {
    memAuth = { idToken: storedIdToken, userId: storedUserId, email: storedEmail || undefined, expMs: storedExpMs };
    return memAuth;
  }

  const cfg = getConfig();
  const cfgIdToken = String(cfg.ID_TOKEN || "").trim();
  if (cfgIdToken) {
    const expMs = getIdTokenExpMs(cfgIdToken) || nowMs() + 2 * 60 * 60 * 1000;
    const sub = getIdTokenSub(cfgIdToken);
    if (!sub) throw new Error("invalid ID_TOKEN (missing sub)");
    const email = getIdTokenEmail(cfgIdToken) || undefined;

    const st: AuthState = { idToken: cfgIdToken, userId: sub, email, expMs };
    memAuth = st;
    return st;
  }

  const st = await getIdTokenFromBackground(interactive);
  memAuth = st;

  await sessionSet(SKEY_ID_TOKEN, st.idToken);
  await sessionSet(SKEY_USER_ID, st.userId);
  await sessionSet(SKEY_EMAIL, st.email || "");
  await sessionSet(SKEY_IDEXP, st.expMs);

  if (interactive) {
    await sessionSet(SKEY_INTERACTIVE_AT, nowMs());
  }

  return st;
}

async function clearAuth(): Promise<void> {
  memAuth = null;
  memJwt = null;
  memJwtExpMs = 0;

  await sessionRemove([SKEY_ID_TOKEN, SKEY_USER_ID, SKEY_EMAIL, SKEY_IDEXP, SKEY_JWT, SKEY_JWTEXP, SKEY_INTERACTIVE_AT]);

  try {
    if (canUseChromeRuntime()) {
      await sendRuntimeMessage({ type: "CORPBOT_CLEAR_ID_TOKEN" });
    }
  } catch {}
}

function expMsFromResponseTokenOrExpiresIn(token: string, expiresInSeconds: any): number {
  const expFromJwt = getJwtExpMs(token);
  if (expFromJwt) return expFromJwt;

  const sec = Number(expiresInSeconds || 0);
  if (sec && sec > 0) return nowMs() + sec * 1000;

  return nowMs() + JWT_FALLBACK_TTL_MS;
}

async function exchangeJwt(auth: AuthState): Promise<{ token: string; expMs: number }> {
  const { API_BASE, CLIENT_VERSION } = getConfig();
  const url = joinUrl(API_BASE, "/api/auth/exchange");

  const payload = {
    user_id: auth.userId,
    client_version: CLIENT_VERSION,
    id_token: auth.idToken
  };

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const text = await readBodyText(res);
    if (res.status === 401 || res.status === 403) {
      memJwt = null;
      memJwtExpMs = 0;
      await sessionRemove([SKEY_JWT, SKEY_JWTEXP]);
      throw new AuthRequiredError();
    }
    throw new ApiError(res.status, text);
  }

  const data = (await res.json()) as any;
  const token = String(data?.token || data?.access_token || "").trim();
  if (!token) throw new Error("exchange_response_missing_token");

  const expMs = expMsFromResponseTokenOrExpiresIn(token, data?.expires_in_seconds ?? data?.expires_in ?? data?.expires);
  return { token, expMs };
}

async function refreshJwt(currentJwt: string): Promise<{ token: string; expMs: number }> {
  const { API_BASE } = getConfig();
  const url = joinUrl(API_BASE, "/api/auth/refresh");

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      Authorization: `Bearer ${currentJwt}`
    },
    body: JSON.stringify({})
  });

  if (!res.ok) {
    const text = await readBodyText(res);
    if (res.status === 401 || res.status === 403) {
      memJwt = null;
      memJwtExpMs = 0;
      await sessionRemove([SKEY_JWT, SKEY_JWTEXP]);
      throw new AuthRequiredError();
    }
    throw new ApiError(res.status, text);
  }

  const data = (await res.json()) as any;
  const token = String(data?.token || data?.access_token || "").trim();
  if (!token) throw new Error("refresh_response_missing_token");

  const expMs = expMsFromResponseTokenOrExpiresIn(token, data?.expires_in_seconds ?? data?.expires_in ?? data?.expires);
  return { token, expMs };
}

async function backendLogout(currentJwt: string): Promise<void> {
  const { API_BASE } = getConfig();
  const url = joinUrl(API_BASE, "/api/auth/logout");

  try {
    await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        Authorization: `Bearer ${currentJwt}`
      },
      body: JSON.stringify({})
    });
  } catch {}
}

function shouldRefreshJwtSoon(expMs: number): boolean {
  const leftMs = expMs - nowMs();
  return leftMs > 0 && leftMs < JWT_REFRESH_BEFORE_MS;
}

async function ensureJwt(opts?: { interactive?: boolean }): Promise<{ token: string; userId: string }> {
  const interactive = Boolean(opts?.interactive);

  if (memJwt && memAuth?.userId && nowMs() < memJwtExpMs - AUTH_SKEW_MS) {
    if (shouldRefreshJwtSoon(memJwtExpMs)) {
      try {
        const ex = await refreshJwt(memJwt);
        memJwt = ex.token;
        memJwtExpMs = ex.expMs;
        await sessionSet(SKEY_JWT, memJwt);
        await sessionSet(SKEY_JWTEXP, memJwtExpMs);
      } catch (e: any) {
        if (nowMs() >= memJwtExpMs - AUTH_SKEW_MS) {
          memJwt = null;
          memJwtExpMs = 0;
          await sessionRemove([SKEY_JWT, SKEY_JWTEXP]);
          throw e instanceof AuthRequiredError ? e : new AuthRequiredError();
        }
      }
    }
    return { token: memJwt, userId: memAuth.userId };
  }

  const storedJwt = (await sessionGet<string>(SKEY_JWT)) || "";
  const storedJwtExp = Number((await sessionGet<number>(SKEY_JWTEXP)) || 0);
  const storedUserId = (await sessionGet<string>(SKEY_USER_ID)) || "";

  if (storedJwt && storedJwtExp && nowMs() < storedJwtExp - AUTH_SKEW_MS && storedUserId) {
    memJwt = storedJwt;
    memJwtExpMs = storedJwtExp;

    if (shouldRefreshJwtSoon(memJwtExpMs)) {
      try {
        const ex = await refreshJwt(memJwt);
        memJwt = ex.token;
        memJwtExpMs = ex.expMs;
        await sessionSet(SKEY_JWT, memJwt);
        await sessionSet(SKEY_JWTEXP, memJwtExpMs);
      } catch (e: any) {
        if (nowMs() >= memJwtExpMs - AUTH_SKEW_MS) {
          memJwt = null;
          memJwtExpMs = 0;
          await sessionRemove([SKEY_JWT, SKEY_JWTEXP]);
          throw e instanceof AuthRequiredError ? e : new AuthRequiredError();
        }
      }
    }

    return { token: memJwt, userId: storedUserId };
  }

  const auth = await ensureAuth({ interactive });
  const { token, expMs } = await exchangeJwt(auth);

  memJwt = token;
  memJwtExpMs = expMs;

  await sessionSet(SKEY_JWT, memJwt);
  await sessionSet(SKEY_JWTEXP, memJwtExpMs);

  return { token: memJwt, userId: auth.userId };
}

function normalizeBody<T extends Record<string, any>>(userId: string, body: T): T {
  const cfg = getConfig();
  const payload: any = { ...(body || {}) };
  if (!payload.user_id) payload.user_id = userId;
  if (!payload.client_version) payload.client_version = cfg.CLIENT_VERSION || "ext-dev";
  return payload as T;
}

async function apiFetchOnce<TReq extends Record<string, any>, TRes>(path: string, body: TReq): Promise<TRes> {
  const { API_BASE } = getConfig();
  const url = joinUrl(API_BASE, path);

  const doFetch = async (jwt: string, pl: any): Promise<Response> => {
    return await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        Authorization: `Bearer ${jwt}`
      },
      body: JSON.stringify(pl)
    });
  };

  const { token, userId } = await ensureJwt({ interactive: false });
  const payload = normalizeBody(userId, body);
  const res = await doFetch(token, payload);

  if (res.status === 401 || res.status === 403) {
    memJwt = null;
    memJwtExpMs = 0;
    await sessionRemove([SKEY_JWT, SKEY_JWTEXP]);
    throw new AuthRequiredError();
  }

  if (!res.ok) {
    const text = await readBodyText(res);
    throw new ApiError(res.status, text);
  }

  return (await res.json()) as TRes;
}

async function apiFetch<TReq extends Record<string, any>, TRes>(path: string, body: TReq): Promise<TRes> {
  try {
    return await apiFetchOnce<TReq, TRes>(path, body);
  } catch (e: any) {
    const msg = String(e?.message || e);
    if (e instanceof AuthRequiredError || msg === "login_required") {
      try {
        await requireInteractiveIfWindowExpired(false);
        const a = await ensureAuth({ interactive: false });
        const ex = await exchangeJwt(a);
        memJwt = ex.token;
        memJwtExpMs = ex.expMs;
        await sessionSet(SKEY_JWT, memJwt);
        await sessionSet(SKEY_JWTEXP, memJwtExpMs);
        return await apiFetchOnce<TReq, TRes>(path, body);
      } catch (e2: any) {
        throw e2;
      }
    }
    throw e;
  }
}

export type Candidate = {
  id: string;
  department: string;
  question: string;
  owner?: string;
};

export type ChatRequest = {
  request_id?: string | null;
  query: string;
  selection_id?: string | null;
  exclude_ids?: string[];
};

export type ChatResponse = {
  request_id: string;
  source: "exact" | "keyword" | "candidate" | "none" | "error";
  candidates: Candidate[];
  answer: string;
  guidance: string;
  routing_department?: string;
};

export type FeedbackRequest = {
  request_id: string;
  user_feedback?: string;
  solved?: boolean | null;
  selection_id?: string | null;
  query?: string | null;
  client_version?: string | null;
  candidates_ids?: string[] | null;
  searched_departments?: string[] | null;
};

export async function chat(payload: ChatRequest): Promise<ChatResponse> {
  return await apiFetch<ChatRequest, ChatResponse>("/api/chat", payload);
}

export async function feedback(payload: FeedbackRequest): Promise<{ ok: boolean }> {
  return await apiFetch<FeedbackRequest, { ok: boolean }>("/api/feedback", payload);
}

export async function getAuthUser(): Promise<{ userId: string; email?: string } | null> {
  try {
    const at = await readInteractiveAtMs();
    if (at && !isInteractiveWindowValid(at)) return null;
    const a = await ensureAuth({ interactive: false });
    return { userId: a.userId, email: a.email };
  } catch {
    return null;
  }
}

export async function login(): Promise<{ userId: string; email?: string } | null> {
  const a = await ensureAuth({ interactive: true });
  memAuth = a;
  memJwt = null;
  memJwtExpMs = 0;
  await sessionRemove([SKEY_JWT, SKEY_JWTEXP]);
  await sessionSet(SKEY_INTERACTIVE_AT, nowMs());
  return { userId: a.userId, email: a.email };
}

export async function logout(): Promise<void> {
  try {
    const jwt = memJwt || ((await sessionGet<string>(SKEY_JWT)) || "");
    if (jwt) await backendLogout(jwt);
  } catch {}
  await clearAuth();
}

export async function relog(): Promise<{ userId: string; email?: string } | null> {
  await logout();
  return await login();
}

export async function relogin(): Promise<{ userId: string; email?: string } | null> {
  return await relog();
}

export async function signOut(): Promise<void> {
  await logout();
}
