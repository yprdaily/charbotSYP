import { CORPBOT_RUNTIME } from "./config.runtime.js";

let lastWindowId = null;

const SESSION_KEY = "corpbot_oidc_v1";
const FORCE_INTERACTIVE_KEY = "corpbot_force_interactive_v1";
const INTERACTION_REQUIRED_AT_KEY = "corpbot_interaction_required_at_sec_v1";
const INTERACTION_COOLDOWN_SEC = 300;
const TOKEN_SKEW_SEC = 60;

function nowSec() {
  return Math.floor(Date.now() / 1000);
}

function getUiUrl() {
  if (CORPBOT_RUNTIME.UI_MODE === "dev") return CORPBOT_RUNTIME.DEV_UI_URL;
  return chrome.runtime.getURL(CORPBOT_RUNTIME.PROD_UI_PATH);
}

function canUseWindowsApi() {
  try {
    return !!chrome?.windows?.create && !!chrome?.windows?.get && !!chrome?.windows?.update;
  } catch {
    return false;
  }
}

async function focusIfExists() {
  if (!lastWindowId) return false;
  if (!canUseWindowsApi()) return false;

  try {
    const w = await chrome.windows.get(lastWindowId, { populate: false });
    if (w?.id) {
      await chrome.windows.update(w.id, { focused: true });
      return true;
    }
  } catch {
    lastWindowId = null;
  }
  return false;
}

function b64urlDecodeToJson(seg) {
  const s = String(seg || "");
  const pad = "=".repeat((4 - (s.length % 4)) % 4);
  const b64 = (s + pad).replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  const text = new TextDecoder().decode(bytes);
  return JSON.parse(text);
}

function decodeJwtPayload(jwt) {
  const parts = String(jwt || "").split(".");
  if (parts.length !== 3) throw new Error("invalid_jwt");
  return b64urlDecodeToJson(parts[1]);
}

function isInteractionRequiredErrorMessage(msg) {
  const m = String(msg || "").toLowerCase();
  return (
    m.includes("interaction required") ||
    m.includes("interaction_required") ||
    m.includes("user interaction required") ||
    m.includes("login_required") ||
    m.includes("consent_required")
  );
}

function parseAuthResultFromUrl(url, expectedState) {
  const u = new URL(url);

  const authError = u.searchParams.get("authError");
  const flowName = u.searchParams.get("flowName");
  const clientId = u.searchParams.get("client_id");

  if (u.pathname.includes("/signin/oauth/error") || authError) {
    return {
      kind: "oauth_error_page",
      authError: authError || "",
      flowName: flowName || "",
      clientId: clientId || "",
      url,
    };
  }

  const qErr = u.searchParams.get("error");
  const qDesc = u.searchParams.get("error_description");
  if (qErr) {
    return { kind: "oauth_error", error: qErr, error_description: qDesc || "", url };
  }

  const hash = u.hash && u.hash.startsWith("#") ? u.hash.slice(1) : u.hash || "";
  const h = new URLSearchParams(hash);

  const hErr = h.get("error");
  const hDesc = h.get("error_description");
  if (hErr) {
    return { kind: "oauth_error", error: hErr, error_description: hDesc || "", url };
  }

  const returnedState = String(h.get("state") || "");
  if (expectedState && returnedState !== expectedState) {
    return { kind: "state_mismatch", expectedState, returnedState, url };
  }

  const idToken = h.get("id_token");
  if (!idToken) {
    return { kind: "unknown_no_id_token", url };
  }

  let payload;
  try {
    payload = decodeJwtPayload(idToken);
  } catch {
    return { kind: "invalid_id_token", url };
  }

  return {
    kind: "success",
    idToken,
    sub: String(payload.sub || ""),
    email: String(payload.email || ""),
    hd: String(payload.hd || ""),
    exp: Number(payload.exp || 0),
    aud: String(payload.aud || ""),
    iss: String(payload.iss || ""),
  };
}

async function getCachedIdToken() {
  const { [SESSION_KEY]: v } = await chrome.storage.session.get([SESSION_KEY]);
  if (!v?.idToken) return null;
  const exp = Number(v.exp || 0);
  if (exp && exp > nowSec() + TOKEN_SKEW_SEC) return v;
  return null;
}

async function setCachedIdToken(v) {
  await chrome.storage.session.set({ [SESSION_KEY]: v });
}

async function getForceInteractive() {
  const { [FORCE_INTERACTIVE_KEY]: v } = await chrome.storage.session.get([FORCE_INTERACTIVE_KEY]);
  return Boolean(v);
}

async function setForceInteractive(v) {
  await chrome.storage.session.set({ [FORCE_INTERACTIVE_KEY]: Boolean(v) });
}

async function clearSessionAll() {
  await chrome.storage.session.remove([SESSION_KEY, FORCE_INTERACTIVE_KEY, INTERACTION_REQUIRED_AT_KEY]);
}

async function getInteractionRequiredAt() {
  const { [INTERACTION_REQUIRED_AT_KEY]: v } = await chrome.storage.session.get([INTERACTION_REQUIRED_AT_KEY]);
  return Number(v || 0);
}

async function setInteractionRequiredAt(sec) {
  await chrome.storage.session.set({ [INTERACTION_REQUIRED_AT_KEY]: Number(sec || 0) });
}

function buildAuthUrl({ clientId, redirectUri, scope, nonce, state, prompt }) {
  const authUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authUrl.searchParams.set("client_id", clientId);
  authUrl.searchParams.set("response_type", "id_token");
  authUrl.searchParams.set("redirect_uri", redirectUri);
  authUrl.searchParams.set("scope", scope);
  authUrl.searchParams.set("nonce", nonce);
  authUrl.searchParams.set("state", state);
  authUrl.searchParams.set("prompt", prompt || "select_account");
  authUrl.searchParams.set("response_mode", "fragment");
  if (CORPBOT_RUNTIME.OAUTH_HD_HINT) authUrl.searchParams.set("hd", CORPBOT_RUNTIME.OAUTH_HD_HINT);
  return authUrl.toString();
}

function normalizeAllowedDomains(v) {
  if (Array.isArray(v)) {
    return v.map((x) => String(x || "").trim()).filter(Boolean);
  }
  const s = String(v || "").trim();
  if (!s) return [];
  return s
    .split(/[,\s]+/g)
    .map((x) => String(x || "").trim())
    .filter(Boolean);
}

function getAllowedDomains() {
  const fromList = normalizeAllowedDomains(CORPBOT_RUNTIME.OAUTH_ALLOWED_DOMAINS);
  if (fromList.length > 0) return fromList;

  const hint = String(CORPBOT_RUNTIME.OAUTH_HD_HINT || "").trim();
  if (hint) return [hint];

  return [];
}

function validateIdToken(parsed, expectedClientId) {
  if (!parsed?.idToken || !parsed.sub) throw new Error("missing_sub_in_id_token");
  if (!parsed.exp || parsed.exp <= nowSec()) throw new Error("expired_id_token");

  const aud = String(parsed.aud || "").trim();
  if (expectedClientId && aud && aud !== expectedClientId) {
    throw new Error("aud_mismatch");
  }

  const iss = String(parsed.iss || "").trim();
  if (iss && iss !== "accounts.google.com" && iss !== "https://accounts.google.com") {
    throw new Error("iss_mismatch");
  }

  const allowed = getAllowedDomains();
  if (allowed.length > 0) {
    const hd = String(parsed.hd || "").trim();
    if (!hd) throw new Error("hd_missing");
    if (!allowed.includes(hd)) throw new Error("hd_mismatch");
  }
}

function normalizeScopes(v) {
  const raw = Array.isArray(v) ? v.map(String) : [];
  const set = new Set(raw.map((s) => String(s || "").trim()).filter(Boolean));
  set.add("openid");
  if (!set.has("email")) set.add("email");
  if (!set.has("profile")) set.add("profile");
  return Array.from(set);
}

async function oidcGetIdToken({ interactive }) {
  const forced = await getForceInteractive();
  const wantInteractive = Boolean(interactive) || forced;

  if (!wantInteractive) {
    const cached = await getCachedIdToken();
    if (cached) return cached;

    const at = await getInteractionRequiredAt();
    if (at && nowSec() < at + INTERACTION_COOLDOWN_SEC) {
      throw new Error("interaction_required");
    }
  }

  const clientId = String(CORPBOT_RUNTIME.OAUTH_CLIENT_ID || "").trim();
  if (!clientId) throw new Error("missing_oauth_client_id");

  const redirectUri = chrome.identity.getRedirectURL("oauth2");
  const nonce = crypto.randomUUID();
  const state = crypto.randomUUID();

  const scopes = normalizeScopes(CORPBOT_RUNTIME.OAUTH_SCOPES || ["openid", "email", "profile"]);
  const scope = scopes.join(" ");

  const prompt = wantInteractive ? "select_account" : "none";
  const url = buildAuthUrl({ clientId, redirectUri, scope, nonce, state, prompt });

  let redirectedTo;
  try {
    redirectedTo = await chrome.identity.launchWebAuthFlow({
      url,
      interactive: Boolean(wantInteractive),
    });
  } catch (e) {
    const msg = String(e?.message || e);
    if (!wantInteractive && isInteractionRequiredErrorMessage(msg)) {
      await setInteractionRequiredAt(nowSec());
      throw new Error("interaction_required");
    }
    throw new Error(`launchWebAuthFlow_failed:${msg}`);
  }

  const parsed = parseAuthResultFromUrl(redirectedTo, state);
  if (parsed.kind !== "success") {
    if (parsed.kind === "oauth_error") {
      if (!wantInteractive && isInteractionRequiredErrorMessage(parsed.error || "")) {
        await setInteractionRequiredAt(nowSec());
      }
      throw new Error(`oauth_failed:${parsed.error}:${parsed.error_description || ""}`);
    }
    if (parsed.kind === "state_mismatch") {
      throw new Error(`oauth_failed:${parsed.kind}:${parsed.expectedState}:${parsed.returnedState}`);
    }
    throw new Error(`oauth_failed:${parsed.kind}`);
  }

  validateIdToken(parsed, clientId);

  const stored = {
    idToken: parsed.idToken,
    sub: parsed.sub,
    email: parsed.email,
    hd: parsed.hd,
    exp: parsed.exp,
    aud: parsed.aud,
    iss: parsed.iss,
  };

  await setCachedIdToken(stored);
  await setInteractionRequiredAt(0);

  if (forced) {
    await setForceInteractive(false);
  }

  return stored;
}

globalThis.__corpbotDebug = {
  getRedirectURL: () => chrome.identity.getRedirectURL("oauth2"),
  getRuntimeId: () => chrome.runtime.id,
  oidcGetIdToken,
  getForceInteractive,
  setForceInteractive,
  clearSessionAll,
};

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  let responded = false;
  const safeRespond = (payload) => {
    if (responded) return;
    responded = true;
    try {
      sendResponse(payload);
    } catch {}
  };

  (async () => {
    const type = msg?.type;

    if (type === "OPEN_CORPBOT") {
      const uiUrl = getUiUrl();

      const wantPopup = msg?.open_mode === "popup" || msg?.popup === true;
      if (!wantPopup) {
        safeRespond({ ok: true, opened: false, uiUrl });
        return;
      }

      try {
        if (await focusIfExists()) {
          safeRespond({ ok: true, reused: true, opened: true, uiUrl, windowId: lastWindowId });
          return;
        }

        if (!canUseWindowsApi()) {
          safeRespond({ ok: true, opened: false, uiUrl });
          return;
        }

        const w = await chrome.windows.create({
          url: uiUrl,
          type: "popup",
          width: 420,
          height: 680,
        });

        lastWindowId = w?.id ?? null;
        safeRespond({ ok: true, reused: false, opened: true, uiUrl, windowId: lastWindowId });
        return;
      } catch (e) {
        safeRespond({ ok: true, opened: false, uiUrl, fallback: true, error: String(e?.message || e) });
        return;
      }
    }

    if (type === "CORPBOT_GET_ID_TOKEN") {
      try {
        const interactive = msg?.interactive === true;
        const v = await oidcGetIdToken({ interactive });
        safeRespond({
          ok: true,
          id_token: v.idToken,
          sub: v.sub,
          email: v.email,
          hd: v.hd,
          exp: v.exp,
          aud: v.aud,
          iss: v.iss,
        });
      } catch (e) {
        safeRespond({ ok: false, error: String(e?.message || e) });
      }
      return;
    }

    if (type === "CORPBOT_CLEAR_ID_TOKEN") {
      try {
        await chrome.storage.session.remove([SESSION_KEY]);
        safeRespond({ ok: true });
      } catch (e) {
        safeRespond({ ok: false, error: String(e?.message || e) });
      }
      return;
    }

    if (type === "CORPBOT_SET_FORCE_INTERACTIVE") {
      try {
        await setForceInteractive(Boolean(msg?.value));
        safeRespond({ ok: true, value: await getForceInteractive() });
      } catch (e) {
        safeRespond({ ok: false, error: String(e?.message || e) });
      }
      return;
    }

    if (type === "CORPBOT_GET_FORCE_INTERACTIVE") {
      try {
        safeRespond({ ok: true, value: await getForceInteractive() });
      } catch (e) {
        safeRespond({ ok: false, error: String(e?.message || e) });
      }
      return;
    }

    if (type === "CORPBOT_CLEAR_SESSION_ALL") {
      try {
        await clearSessionAll();
        safeRespond({ ok: true });
      } catch (e) {
        safeRespond({ ok: false, error: String(e?.message || e) });
      }
      return;
    }

    safeRespond({ ok: false, error: `Unknown message type: ${String(type)}` });
  })().catch((e) => {
    safeRespond({ ok: false, error: String(e?.message || e) });
  });

  return true;
});
