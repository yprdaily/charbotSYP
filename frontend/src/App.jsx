import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
  forwardRef,
  useImperativeHandle
} from "react";
import { chat, feedback, getAuthUser, login, AuthRequiredError } from "./api";
import "./App.css";

function newRequestId() {
  try {
    return crypto.randomUUID();
  } catch {
    return String(Date.now());
  }
}

function readCfg() {
  return window.CORPBOT_CONFIG || {};
}

function newMessageId(prefix = "m") {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function safeBuildLogoUrl(cfg) {
  const direct = String(cfg.BRAND_LOGO_URL || "").trim();
  if (direct) return direct;

  const path = String(cfg.BRAND_LOGO_PATH || "").trim();
  if (!path) return "";

  try {
    if (typeof chrome !== "undefined" && chrome?.runtime?.getURL) {
      return chrome.runtime.getURL(path);
    }
  } catch {
    return path;
  }
  return path;
}

function isStandaloneWindow() {
  try {
    const sp = new URLSearchParams(window.location.search);
    if (sp.get("standalone") === "1") return true;
  } catch { }
  try {
    return window.self === window.top;
  } catch {
    return true;
  }
}

function normalizeDeptKey(s) {
  return String(s || "").trim().toLowerCase();
}

function buildDeptDisplayResolver(cfg) {
  const raw = cfg?.DEPARTMENT_DISPLAY_MAP;
  const map = raw && typeof raw === "object" ? raw : null;

  const preset = {
    system: "システム課",
    general_affairs: "総務",
    labor: "労務",
    legal: "法務",
    hr: "人事"
  };

  return (deptKeyOrName) => {
    const k = normalizeDeptKey(deptKeyOrName);
    if (!k) return String(deptKeyOrName || "").trim();
    if (map && Object.prototype.hasOwnProperty.call(map, k)) return String(map[k] || "").trim() || k;
    if (Object.prototype.hasOwnProperty.call(preset, k)) return preset[k];
    return String(deptKeyOrName || "").trim() || k;
  };
}

const LinkifiedText = ({ text }) => {
  if (!text) return null;
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = text.split(urlRegex);
  return (
    <span>
      {parts.map((part, i) =>
        /^https?:\/\//.test(part) ? (
          <a
            key={i}
            href={part}
            target="_blank"
            rel="noreferrer"
            className="linkified-link"
            onClick={(e) => e.stopPropagation()}
          >
            {part}
          </a>
        ) : (
          part
        )
      )}
    </span>
  );
};

const ChatWidget = forwardRef(function ChatWidget({ standalone }, ref) {
  const [cfg, setCfg] = useState(() => readCfg());
  useEffect(() => {
    setCfg(readCfg());
  }, []);

  const clientVersion = useMemo(() => String(cfg.CLIENT_VERSION || "ext-dev"), [cfg]);

  const brandName = useMemo(() => String(cfg.BRAND_NAME || "管理本部 問い合わせ窓口"), [cfg]);
  const brandFallbackText = useMemo(() => String(cfg.BRAND_FALLBACK_TEXT || "CB"), [cfg]);
  const brandLogoUrl = useMemo(() => safeBuildLogoUrl(cfg), [cfg]);

  const resolveDeptDisplay = useMemo(() => buildDeptDisplayResolver(cfg), [cfg]);

  const COPY = useMemo(() => {
    const pick = "当てはまるものを選んでください。見当たらない場合は［該当なし］を押してください。";
    const unresolvedDefault =
      "この内容に一致する案内が見つかりませんでした。まずは総務へお問い合わせください。\n" +
      "この内容は今後の改善に活用します。";
    const unresolved = String(cfg.UNRESOLVED_TEXT || "").trim() || unresolvedDefault;

    return {
      hello: "こんにちは。お困りごとを入力してください。",
      pick,
      notMatchBtn: "該当なし",
      unresolved,
      solvedAsk: "状況は改善しましたか？",
      solvedYesBtn: "解決した",
      solvedNoBtn: "解決しない",
      searchingAlt: "別の候補を探します。少々お待ちください。",
      closed: "受付をクローズしました。別のご用件があればこのまま入力してください。",
      processing: "処理中…",
      netErr: "通信エラーが発生しました。もう一度お試しください。",
      pickErr: "候補確定でエラーが発生しました。",
      fbErr: "未解決連携（feedback）でエラーが発生しました。",
      retryErr: "再検索でエラーが発生しました。",
      closeErr: "クローズ処理でエラーが発生しました。",
      loginRequired: "ログインが必要です。"
    };
  }, [cfg]);

  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [messages, setMessages] = useState([{ id: newMessageId("bot"), role: "bot", text: COPY.hello }]);

  const [ticket, setTicket] = useState({
    requestId: "",
    query: "",
    status: "idle",
    excludeIds: []
  });

  const [authUser, setAuthUser] = useState(null);
  const [needsLogin, setNeedsLogin] = useState(false);

  const syncAuthState = async () => {
    const u = await getAuthUser();
    setAuthUser(u);
    setNeedsLogin(!u);
    return u;
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const u = await getAuthUser();
      if (cancelled) return;
      setAuthUser(u);
      setNeedsLogin(!u);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setMessages([{ id: newMessageId("bot"), role: "bot", text: COPY.hello }]);
    setTicket({ requestId: "", query: "", status: "idle", excludeIds: [] });
    setQ("");
    setErr("");
    setLoading(false);
  }, [COPY.hello]);

  const listRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading, needsLogin]);

  const pushMsg = (m) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (m?.role === "sys" && last?.role === "sys" && String(last?.text || "") === String(m?.text || "")) {
        return prev;
      }
      return [...prev, m];
    });
  };

  const hideCandidatesByMessageId = (messageId) => {
    if (!messageId) return;
    setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, candidates: [] } : m)));
  };

  const disableActionByMessageId = (messageId) => {
    if (!messageId) return;
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, meta: { ...(m.meta || {}), disabled: true } } : m))
    );
  };

  const sendChat = async ({ requestId, query, selectionId, excludeIds }) => {
    const payload = {
      request_id: requestId,
      query,
      exclude_ids: Array.isArray(excludeIds) ? excludeIds : [],
      ...(selectionId ? { selection_id: selectionId } : {})
    };
    return await chat(payload);
  };

  const pushSolvedAsk = ({ requestId, queryText, selectionId }) => {
    const msgId = newMessageId("solve");
    pushMsg({
      id: msgId,
      role: "bot",
      text: COPY.solvedAsk,
      meta: {
        action: "solve_check",
        messageId: msgId,
        requestId,
        query: queryText,
        selectionId: selectionId || "",
        disabled: false
      }
    });
  };

  const handleChatResult = ({ ridFallback, queryText, res }) => {
    const rid = res?.request_id || ridFallback;

    if (Array.isArray(res?.candidates) && res.candidates.length > 0) {
      const msgId = newMessageId("cand");
      setTicket((t) => ({ ...t, requestId: rid, query: queryText, status: "candidates" }));
      pushMsg({
        id: msgId,
        role: "bot",
        text: COPY.pick,
        candidates: res.candidates,
        meta: { requestId: rid, query: queryText, messageId: msgId }
      });
      return;
    }

    setTicket((t) => ({ ...t, requestId: rid, query: queryText, status: "answered" }));

    if (res?.answer) {
      pushMsg({ id: newMessageId("bot"), role: "bot", text: res.answer });
    }

    if (res?.source === "none") {
      const g = String(res?.guidance || "").trim();
      pushMsg({ id: newMessageId("sys"), role: "sys", text: g || COPY.unresolved });
      return;
    }

    if (res?.guidance) {
      pushMsg({ id: newMessageId("sys"), role: "sys", text: res.guidance });
    }

    let solvedSelectionId = "";
    if (res?.hit_department && res?.hit_row_id) {
      solvedSelectionId = `${res.hit_department}:${res.hit_row_id}`;
    } else if (res?.routing_department) {
      const deptKey = String(res.routing_department).trim();
      if (deptKey) {
        solvedSelectionId = `${deptKey}:0`;
      }
    }

    pushSolvedAsk({ requestId: rid, queryText, selectionId: solvedSelectionId });
  };

  const markLoginRequired = async () => {
    setNeedsLogin(true);
    await syncAuthState();
  };

  const doLogin = async () => {
    setErr("");
    try {
      const u = await login();
      setAuthUser(u);
      setNeedsLogin(!u);
      return u;
    } catch (e) {
      setErr(String(e?.message || e));
      return await syncAuthState();
    }
  };

  const doSendText = async (text) => {
    const t = String(text || "").trim();
    if (!t || loading || needsLogin) return;

    setErr("");
    setLoading(true);

    const rid = newRequestId();
    setTicket({ requestId: rid, query: t, status: "idle", excludeIds: [] });

    pushMsg({ id: newMessageId("user"), role: "user", text: t });

    try {
      const r = await sendChat({ requestId: rid, query: t, excludeIds: [] });
      setNeedsLogin(false);
      handleChatResult({ ridFallback: rid, queryText: t, res: r });
      setQ("");
      await syncAuthState();
    } catch (e) {
      const msg = String(e?.message || e);
      setErr(msg);

      if (e instanceof AuthRequiredError || msg === "login_required") {
        await markLoginRequired();
      } else {
        pushMsg({ id: newMessageId("sys"), role: "sys", text: COPY.netErr });
      }
    } finally {
      setLoading(false);
    }
  };

  const onSend = async () => {
    await doSendText(q);
  };

  const onPickCandidate = async (selectionId, meta) => {
    if (loading || needsLogin) return;

    const rid = meta?.requestId || ticket.requestId || newRequestId();
    const queryText = meta?.query || ticket.query || "";
    const messageId = meta?.messageId;

    setErr("");
    setLoading(true);

    try {
      const r = await sendChat({
        requestId: rid,
        query: queryText,
        selectionId,
        excludeIds: ticket.excludeIds
      });

      setNeedsLogin(false);
      hideCandidatesByMessageId(messageId);
      setTicket((t) => ({ ...t, requestId: r.request_id || rid, query: queryText, status: "answered" }));

      if (r?.answer) pushMsg({ id: newMessageId("bot"), role: "bot", text: r.answer });

      if (r?.source === "none") {
        const g = String(r?.guidance || "").trim();
        pushMsg({ id: newMessageId("sys"), role: "sys", text: g || COPY.unresolved });
        await syncAuthState();
        return;
      }

      if (r?.guidance) pushMsg({ id: newMessageId("sys"), role: "sys", text: r.guidance });

      try {
        await feedback({
          request_id: rid,
          solved: null,
          selection_id: selectionId,
          user_feedback: "candidate_selected",
          query: queryText,
          client_version: clientVersion
        });
      } catch { }

      pushSolvedAsk({ requestId: r.request_id || rid, queryText, selectionId });
      await syncAuthState();
    } catch (e) {
      const msg = String(e?.message || e);
      setErr(msg);

      if (e instanceof AuthRequiredError || msg === "login_required") {
        await markLoginRequired();
      } else {
        pushMsg({ id: newMessageId("sys"), role: "sys", text: COPY.pickErr });
      }
    } finally {
      setLoading(false);
    }
  };

  const onNotMatch = async (meta, candidatesCount, candidateIds) => {
    if (loading || needsLogin) return;

    const rid = meta?.requestId || ticket.requestId || newRequestId();
    const queryText = meta?.query || ticket.query || "";
    const messageId = meta?.messageId;

    const ids = Array.isArray(candidateIds) ? candidateIds.filter(Boolean) : [];
    const cnt = Number(candidatesCount || 0);

    setErr("");
    setLoading(true);

    try {
      await feedback({
        request_id: rid,
        solved: false,
        user_feedback: "not_match",
        query: queryText,
        client_version: clientVersion,
        candidates_ids: ids
      });

      setNeedsLogin(false);
      hideCandidatesByMessageId(messageId);

      if (cnt >= 2 && ids.length > 0) {
        const merged = new Set([...(ticket.excludeIds || []), ...ids]);
        const nextExclude = Array.from(merged).slice(-100);

        pushMsg({ id: newMessageId("sys"), role: "sys", text: COPY.searchingAlt });

        const rid2 = newRequestId();
        setTicket({ requestId: rid2, query: queryText, status: "idle", excludeIds: nextExclude });

        const r2 = await sendChat({
          requestId: rid2,
          query: queryText,
          excludeIds: nextExclude
        });

        if (Array.isArray(r2?.candidates) && r2.candidates.length > 0) {
          const msgId2 = newMessageId("cand");
          setTicket({
            requestId: r2.request_id || rid2,
            query: queryText,
            status: "candidates",
            excludeIds: nextExclude
          });
          pushMsg({
            id: msgId2,
            role: "bot",
            text: COPY.pick,
            candidates: r2.candidates,
            meta: { requestId: r2.request_id || rid2, query: queryText, messageId: msgId2 }
          });
          await syncAuthState();
          return;
        }

        setTicket({
          requestId: r2.request_id || rid2,
          query: queryText,
          status: "escalated",
          excludeIds: nextExclude
        });

        pushMsg({ id: newMessageId("sys"), role: "sys", text: String(r2?.guidance || "").trim() || COPY.unresolved });
        await syncAuthState();
        return;
      }

      setTicket((t) => ({ ...t, requestId: rid, query: queryText, status: "escalated" }));
      pushMsg({ id: newMessageId("sys"), role: "sys", text: COPY.unresolved });
      await syncAuthState();
    } catch (e) {
      const msg = String(e?.message || e);
      setErr(msg);

      if (e instanceof AuthRequiredError || msg === "login_required") {
        await markLoginRequired();
      } else {
        pushMsg({ id: newMessageId("sys"), role: "sys", text: COPY.fbErr });
      }
    } finally {
      setLoading(false);
    }
  };

  const onSolvedYes = async (meta) => {
    if (loading || needsLogin) return;

    const rid = meta?.requestId || ticket.requestId || "";
    const queryText = meta?.query || ticket.query || "";
    const messageId = meta?.messageId;
    const selectionId = meta?.selectionId || "";

    setErr("");
    setLoading(true);

    try {
      disableActionByMessageId(messageId);

      try {
        await feedback({
          request_id: rid,
          solved: true,
          ...(selectionId ? { selection_id: selectionId } : {}),
          user_feedback: "solved_confirm",
          query: queryText,
          client_version: clientVersion
        });
      } catch { }

      setNeedsLogin(false);
      setTicket((t) => ({ ...t, requestId: rid, query: queryText, status: "closed" }));
      pushMsg({ id: newMessageId("sys"), role: "sys", text: COPY.closed });
      await syncAuthState();
    } catch (e) {
      const msg = String(e?.message || e);
      setErr(msg);

      if (e instanceof AuthRequiredError || msg === "login_required") {
        await markLoginRequired();
      } else {
        pushMsg({ id: newMessageId("sys"), role: "sys", text: COPY.closeErr });
      }
    } finally {
      setLoading(false);
    }
  };

  const onSolvedNo = async (meta) => {
    if (loading || needsLogin) return;

    const prevRid = meta?.requestId || ticket.requestId || "";
    const queryText = meta?.query || ticket.query || "";
    const messageId = meta?.messageId;
    const selectionId = meta?.selectionId || "";

    setErr("");
    setLoading(true);

    try {
      disableActionByMessageId(messageId);

      try {
        await feedback({
          request_id: prevRid,
          solved: false,
          ...(selectionId ? { selection_id: selectionId } : {}),
          user_feedback: "not_solved",
          query: queryText,
          client_version: clientVersion
        });
      } catch { }

      const merged = new Set([...(ticket.excludeIds || [])]);
      if (selectionId) merged.add(selectionId);
      const nextExclude = Array.from(merged).slice(-100);

      pushMsg({ id: newMessageId("sys"), role: "sys", text: COPY.searchingAlt });

      const rid2 = newRequestId();
      setTicket((t) => ({ ...t, requestId: rid2, query: queryText, status: "idle", excludeIds: nextExclude }));

      const r2 = await sendChat({
        requestId: rid2,
        query: queryText,
        excludeIds: nextExclude
      });

      setNeedsLogin(false);

      if (Array.isArray(r2?.candidates) && r2.candidates.length > 0) {
        const msgId2 = newMessageId("cand");
        setTicket((t) => ({
          ...t,
          requestId: r2.request_id || rid2,
          query: queryText,
          status: "candidates",
          excludeIds: nextExclude
        }));
        pushMsg({
          id: msgId2,
          role: "bot",
          text: COPY.pick,
          candidates: r2.candidates,
          meta: { requestId: r2.request_id || rid2, query: queryText, messageId: msgId2 }
        });
        await syncAuthState();
      } else {
        setTicket((t) => ({
          ...t,
          requestId: r2.request_id || rid2,
          query: queryText,
          status: "escalated",
          excludeIds: nextExclude
        }));
        pushMsg({ id: newMessageId("sys"), role: "sys", text: String(r2?.guidance || "").trim() || COPY.unresolved });
        await syncAuthState();
      }
    } catch (e) {
      const msg = String(e?.message || e);
      setErr(msg);

      if (e instanceof AuthRequiredError || msg === "login_required") {
        await markLoginRequired();
      } else {
        pushMsg({ id: newMessageId("sys"), role: "sys", text: COPY.retryErr });
      }
    } finally {
      setLoading(false);
    }
  };

  const BotAvatar = () => {
    if (brandLogoUrl) {
      return (
        <div className="msgAvatar">
          <img src={brandLogoUrl} alt="logo" />
        </div>
      );
    }
    return (
      <div className="msgAvatar txt">
        <span>{brandFallbackText}</span>
      </div>
    );
  };

  const canSend = !loading && !needsLogin;

  useImperativeHandle(ref, () => ({
    focusInput: () => {
      try {
        inputRef.current?.focus?.();
      } catch { }
    },
    send: async (text) => {
      await doSendText(text);
    }
  }));

  return (
    <div className={`App ${standalone ? "standalone" : ""}`}>
      <header className="portalHeader">
        <div className="portalBrand">
          <div className="portalLogo">{brandLogoUrl ? <img src={brandLogoUrl} alt="logo" /> : brandFallbackText}</div>
          <div>
            <div className="portalTitle">{brandName}</div>
          </div>
        </div>

        {needsLogin && (
          <div className="portalUser">
            <span className="dotOnline" />
            <span>ログインが必要です</span>
            <button className="btnGhost" style={{ marginLeft: 8 }} onClick={doLogin}>
              ログイン
            </button>
          </div>
        )}
      </header>

      <main className="chatMain">
        <div ref={listRef} className="chatList">
          {messages.map((m, i) => {
            const isUser = m.role === "user";
            const isSys = m.role === "sys";
            const isBot = !isUser && !isSys;

            return (
              <div key={m.id || i} className={`msgRow ${isUser ? "right" : "left"}`}>
                {!isUser && isBot && <BotAvatar />}

                <div className={`msgBubble ${isUser ? "user" : isSys ? "sys" : "bot"}`}>
                  <div className="msgText">
                    <LinkifiedText text={m.text} />
                  </div>

                  {Array.isArray(m.candidates) && m.candidates.length > 0 && (
                    <div className="candWrap">
                      {m.candidates.map((c) => (
                        <button
                          key={c.id}
                          className="candBtn"
                          disabled={loading || needsLogin}
                          onClick={() => onPickCandidate(c.id, m.meta)}
                        >
                          <div className="candTop">
                            <span className="candDept">{resolveDeptDisplay(c.department)}</span>
                            <span className="candOwner">{c.owner || "-"}</span>
                          </div>
                          <div className="candQ">{c.question}</div>
                        </button>
                      ))}
                      <button
                        className="candBtn danger"
                        disabled={loading || needsLogin}
                        onClick={() =>
                          onNotMatch(
                            m.meta,
                            m.candidates.length,
                            m.candidates.map((x) => x.id).filter(Boolean)
                          )
                        }
                      >
                        {COPY.notMatchBtn}
                      </button>
                    </div>
                  )}

                  {m.meta?.action === "solve_check" && (
                    <div className="actionRow">
                      <button
                        className="btnPrimary"
                        disabled={loading || needsLogin || !!m.meta.disabled}
                        onClick={() => onSolvedYes(m.meta)}
                      >
                        {COPY.solvedYesBtn}
                      </button>
                      <button
                        className="btnGhost"
                        disabled={loading || needsLogin || !!m.meta.disabled}
                        onClick={() => onSolvedNo(m.meta)}
                      >
                        {COPY.solvedNoBtn}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {needsLogin && (
            <div className="msgRow left">
              <div className="msgBubble sys">
                <div className="msgText">{COPY.loginRequired}</div>
              </div>
            </div>
          )}

          {loading && (
            <div className="msgRow left">
              <BotAvatar />
              <div className="msgBubble bot">
                <div className="msgText">{COPY.processing}</div>
              </div>
            </div>
          )}

          {err && (
            <div className="msgRow left">
              <div className="msgBubble sys">
                <div className="msgText">{err}</div>
              </div>
            </div>
          )}
        </div>

        <div className="chatInputBar">
          <input
            ref={inputRef}
            className="chatInput"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={needsLogin ? "ログインしてください" : "質問を入力"}
            disabled={!canSend}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSend();
              }
            }}
          />
          <button className="btnPrimary" onClick={onSend} disabled={!canSend}>
            送信
          </button>
        </div>
      </main>
    </div>
  );
});

function StandaloneCenter() {
  const [cfg, setCfg] = useState(() => readCfg());
  useEffect(() => {
    setCfg(readCfg());
  }, []);

  const brandName = useMemo(() => String(cfg.BRAND_NAME || "管理本部 問い合わせ窓口"), [cfg]);
  const brandFallbackText = useMemo(() => String(cfg.BRAND_FALLBACK_TEXT || "CB"), [cfg]);
  const brandLogoUrl = useMemo(() => safeBuildLogoUrl(cfg), [cfg]);

  const [leadText, setLeadText] = useState("");
  const chatRef = useRef(null);

  return (
    <div className="standRoot">
      <div className="standShell">
        <div className="standHero">
          <div className="standHeroBrand">
            <div className="standHeroLogo">
              {brandLogoUrl ? <img src={brandLogoUrl} alt="logo" /> : <span>{brandFallbackText}</span>}
            </div>
            <div className="standHeroText">
              <div className="standHeroKicker">社内ヘルプ</div>
              <div className="standHeroTitle">{brandName}</div>
              <div className="standHeroSub">よくある社内ルール・申請・手続きを検索できます。</div>
            </div>
          </div>

          <div className="standHeroSearch">
            <input
              className="standHeroInput"
              value={leadText}
              onChange={(e) => setLeadText(e.target.value)}
              placeholder="例：出張申請の手順は？"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  const t = String(leadText || "").trim();
                  if (!t) {
                    chatRef.current?.focusInput?.();
                    return;
                  }
                  chatRef.current?.send?.(t);
                  setLeadText("");
                }
              }}
            />
            <button
              className="btnPrimary standHeroBtn"
              onClick={() => {
                const t = String(leadText || "").trim();
                if (!t) {
                  chatRef.current?.focusInput?.();
                  return;
                }
                chatRef.current?.send?.(t);
                setLeadText("");
              }}
            >
              送信
            </button>
          </div>
        </div>

        <div className="standCard">
          <ChatWidget ref={chatRef} standalone />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const standalone = isStandaloneWindow();
  if (standalone) return <StandaloneCenter />;
  return <ChatWidget standalone={false} />;
}
