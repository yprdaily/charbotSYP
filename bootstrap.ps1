# bootstrap.ps1
# repo root: C:\chatbot-react 縺ｧ螳溯｡後＠縺ｦ縺上□縺輔＞

$ErrorActionPreference = "Stop"

function Write-TextFile($path, $content) {
  $dir = Split-Path $path -Parent
  if ($dir -and !(Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  Set-Content -Path $path -Value $content -Encoding UTF8
}

# ====== Directories ======
$dirs = @(
  ".\backend",
  ".\frontend\src",
  ".\extension\icons",
  ".\scripts"
)
foreach ($d in $dirs) { if (!(Test-Path $d)) { New-Item -ItemType Directory -Force -Path $d | Out-Null } }

# ====== ROOT files ======
Write-TextFile ".\.gitignore" @"
# --- secrets ---
.env
.env.*
*.key
*.pem
*credential*.json
*service-account*.json
*sa*.json

# --- node ---
node_modules
dist
.vite
*.log

# frontend build output into extension (generated)
extension/widget

# --- python ---
__pycache__/
*.pyc
.venv/
.venv

# --- OS/IDE ---
.DS_Store
Thumbs.db
.vscode/*
!.vscode/extensions.json
!.vscode/settings.json
"@

Write-TextFile ".\SECURITY.md" @"
# SECURITY・磯幕逋ｺ繝ｻ驕狗畑繝ｫ繝ｼ繝ｫ・・

## 邨ｶ蟇ｾ繝ｫ繝ｼ繝ｫ・域怙荳贋ｽ搾ｼ・
- Secrets・・PI繧ｭ繝ｼ/JWT鄂ｲ蜷埼嵯/ADMIN_TOKEN/Google SA JSON/.env・峨ｒGit縺ｫ蜈･繧後↑縺・
- main 逶ｴpush遖∵ｭ｢・亥ｿ・★繝悶Λ繝ｳ繝≫・PR竊偵Ξ繝薙Η繝ｼ・・
- 2FA蠢・茨ｼ育､ｾ蜀・Ν繝ｼ繝ｫ縺ｨ縺励※譛ｪ險ｭ螳壹・蜿ょ刈荳榊庄・・

## 繧ｳ繝ｼ繝我ｸ翫・螳牙・蛛ｴ蜑肴署
- Gmail譛ｬ譁・繝・せ繧ｯ繝阪ャ繝・判髱｢諠・ｱ繧呈僑蠑ｵ縺九ｉ蜿門ｾ励・騾∽ｿ｡縺励↑縺・ｼ医Θ繝ｼ繧ｶ繝ｼ蜈･蜉帙・縺ｿ騾∽ｿ｡・・
- 蜀・ｷ壹・蝗ｺ螳壹ョ繝ｼ繧ｿ・育函謌千ｦ∵ｭ｢・・
- 蝗樒ｭ疲悽譁・・繧ｷ繝ｼ繝亥崋螳夲ｼ育函謌千ｦ∵ｭ｢・・
- 逶｣譟ｻ繝ｭ繧ｰ縺ｨ譛ｪ隗｣豎ｺ繝ｭ繧ｰ縺ｯ蛻・屬・育岼逧・・讓ｩ髯舌・菫晏ｭ倬・岼縺檎焚縺ｪ繧具ｼ・

## Secrets豺ｷ蜈･髦ｲ豁｢・育┌譁吶〒縺ｧ縺阪ｋ譛螟ｧ髯撰ｼ・
- .gitignore 縺ｧ .env / SA JSON / keys 繧帝勁螟・
- pre-commit(gitleaks) 繧貞ｰ主・縺励√さ繝溘ャ繝亥燕縺ｫ遘伜ｯ・､懃衍
- 隱､繧ｳ繝溘ャ繝域凾縺ｯ RUNBOOK 縺ｫ蠕薙＞蜊ｳ繝ｭ繝ｼ繝・・繧ｷ繝ｧ繝ｳ
"@

Write-TextFile ".\RUNBOOK.md" @"
# RUNBOOK・育ｷ頑･蟇ｾ蠢懈焔鬆・ｼ・

## 1. Secrets繧定ｪ､繧ｳ繝溘ャ繝・貍上∴縺・＠縺溽桝縺・′縺ゅｋ蝣ｴ蜷茨ｼ域怙蜆ｪ蜈茨ｼ・
1) 貍上∴縺・ｯｾ雎｡繧堤音螳夲ｼ・WT骰ｵ/ADMIN_TOKEN/Google SA骰ｵ/螟夜ΚAPI繧ｭ繝ｼ/.env遲会ｼ・
2) 蠖ｱ髻ｿ遽・峇繧貞・繧雁・縺托ｼ・loud Run / Sheets / GitHub / 遶ｯ譛ｫ・・
3) 骰ｵ繧貞叉譎ゅΟ繝ｼ繝・・繧ｷ繝ｧ繝ｳ

### 繝ｭ繝ｼ繝・・繧ｷ繝ｧ繝ｳ
- JWT鄂ｲ蜷埼嵯・・WT_SIGNING_KEY_BASE64・峨ｒ譁ｰ隕冗匱陦・竊・backend迺ｰ蠅・､画焚繧呈峩譁ｰ 竊・蜀崎ｵｷ蜍・蜀阪ョ繝励Ο繧､
- ADMIN_TOKEN 繧呈眠隕冗匱陦・竊・backend迺ｰ蠅・､画焚繧呈峩譁ｰ
- Google SA JSON・・
  - 縺昴・繧ｭ繝ｼ繧堤┌蜉ｹ蛹・蜑企勁
  - 蠢・ｦ√↑繧画眠縺励＞繧ｭ繝ｼ繧堤匱陦・
- 螟夜ΚAPI繧ｭ繝ｼ縺ｯprovider蛛ｴ縺ｧ revoke/rotate

## 2. Git螻･豁ｴ蟇ｾ蠢懶ｼ・ush貂医∩縺ｮ蝣ｴ蜷茨ｼ・
- 螻･豁ｴ縺九ｉ髯､蜴ｻ縺悟ｿ・ｦ・ｼ亥腰縺ｪ繧句炎髯､縺ｯ荳榊庄・・
- 螳滓命蠕後・繝｡繝ｳ繝舌・蜈ｨ蜩｡縺悟・clone謗ｨ螂ｨ

## 3. 逶｣譟ｻ繝ｻ蝣ｱ蜻・
- 縺・▽/隱ｰ縺・菴輔ｒ/縺ｩ縺薙↓ 繧定ｨ倬鹸
- 遉ｾ蜀・・蝣ｱ蜻翫ヵ繝ｭ繝ｼ・域ュ繧ｷ繧ｹ/逶｣譟ｻ/豕募漁・峨↓蠕薙≧

## 4. 蜀咲匱髦ｲ豁｢
- pre-commit(gitleaks) 繧貞ｿ・亥喧
- Secrets 縺ｯ Secret Manager・域悽逡ｪ・峨∈
"@

Write-TextFile ".\.pre-commit-config.yaml" @"
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
"@

Write-TextFile ".\run_dev.ps1" @"
# repo root 縺ｧ螳溯｡・
# 1) backend襍ｷ蜍・2) frontend build・域僑蠑ｵ縺ｸ蜷梧｢ｱ・・

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd $PSScriptRoot\backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install --upgrade pip; pip install -r requirements.txt; if(!(Test-Path .env)){ Copy-Item .env.example .env }; uvicorn main:app --host 0.0.0.0 --port 8000"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd $PSScriptRoot\frontend; npm install; npm run build"
"@

# ====== scripts ======
Write-TextFile ".\scripts\copy-config.mjs" @"
import fs from "node:fs";
import path from "node:path";

const src = path.resolve(process.cwd(), "../extension/config.js");
const dst = path.resolve(process.cwd(), "../extension/widget/config.js");

fs.mkdirSync(path.dirname(dst), { recursive: true });
fs.copyFileSync(src, dst);
console.log("Copied config.js -> extension/widget/config.js");
"@

# ====== FRONTEND ======
Write-TextFile ".\frontend\package.json" @"
{
  "name": "corpbot-widget",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build && node ../scripts/copy-config.mjs",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^5.4.11"
  }
}
"@

Write-TextFile ".\frontend\vite.config.js" @"
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { host: "127.0.0.1", strictPort: true },
  preview: { host: "127.0.0.1", strictPort: true },
  build: {
    outDir: path.resolve(__dirname, "../extension/widget"),
    emptyOutDir: true
  }
});
"@

Write-TextFile ".\frontend\index.html" @"
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CorpBot</title>
  </head>
  <body>
    <!-- build蠕・ extension/widget/config.js 繧定ｪｭ繧・亥酔髫主ｱ､・・-->
    <script src="./config.js"></script>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"@

Write-TextFile ".\frontend\src\main.jsx" @"
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"@

Write-TextFile ".\frontend\src\api.js" @"
function getConfig() {
  return (window.CORPBOT_CONFIG || { API_BASE: "http://localhost:8000", CLIENT_VERSION: "ext-dev" });
}

let jwt = null;
let jwtExpMs = 0;

function nowMs() { return Date.now(); }

async function ensureJwt(userId) {
  if (jwt && nowMs() < jwtExpMs - 10_000) return jwt;
  const { API_BASE, CLIENT_VERSION } = getConfig();
  const res = await fetch(`${API_BASE}/api/auth/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, client_version: CLIENT_VERSION })
  });
  if (!res.ok) throw new Error(`auth failed: ${res.status}`);
  const data = await res.json();
  jwt = data.token;
  jwtExpMs = nowMs() + (data.expires_in_seconds * 1000);
  return jwt;
}

async function apiFetch(path, userId, body) {
  const { API_BASE } = getConfig();
  const token = await ensureJwt(userId);
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify(body || {})
  });
  if (res.status === 401) {
    jwt = null; jwtExpMs = 0;
    const token2 = await ensureJwt(userId);
    const res2 = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token2}` },
      body: JSON.stringify(body || {})
    });
    if (!res2.ok) throw new Error(`api failed: ${res2.status}`);
    return await res2.json();
  }
  if (!res.ok) throw new Error(`api failed: ${res.status}`);
  return await res.json();
}

export async function chat(userId, payload) {
  return await apiFetch("/api/chat", userId, payload);
}

export async function feedback(userId, payload) {
  return await apiFetch("/api/feedback", userId, payload);
}
"@

Write-TextFile ".\frontend\src\App.jsx" @"
import React, { useEffect, useMemo, useRef, useState } from "react";
import { chat, feedback } from "./api.js";

function uuidv4() {
  // lightweight UUIDv4
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (crypto.getRandomValues(new Uint8Array(1))[0] & 15) >> 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function getOrCreateUserId() {
  const key = "corpbot_user_id";
  let v = localStorage.getItem(key);
  if (!v) {
    v = uuidv4();
    localStorage.setItem(key, v); // 險ｱ蜿ｯ縺輔ｌ縺ｦ縺・ｋ縺ｮ縺ｯ user_id 縺ｮ縺ｿ
  }
  return v;
}

export default function App() {
  const userId = useMemo(() => getOrCreateUserId(), []);
  const [requestId, setRequestId] = useState(null);
  const [messages, setMessages] = useState([
    { role: "system", text: "蛟倶ｺｺ諠・ｱ繝ｻ讖溷ｯ・ｒ蜈･蜉帙＠縺ｪ縺・〒縺上□縺輔＞縲よ悴隗｣豎ｺ縺ｮ蝣ｴ蜷医・諡・ｽ馴Κ髢縺ｮ蜀・ｷ壹ｒ縺疲｡亥・縺励∪縺吶・ }
  ]);
  const [input, setInput] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [awaitingFeedback, setAwaitingFeedback] = useState(false);
  const [loading, setLoading] = useState(false);

  const chatRef = useRef(null);
  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages, candidates, awaitingFeedback]);

  async function sendQuestion() {
    const q = input.trim();
    if (!q) return;
    setInput("");
    setLoading(true);
    setAwaitingFeedback(false);
    setCandidates([]);
    setMessages((m) => [...m, { role: "user", text: q }]);

    try {
      const res = await chat(userId, { question: q });
      setRequestId(res.request_id);
      if (res.type === "candidates") {
        setCandidates(res.candidates || []);
        setMessages((m) => [...m, { role: "bot", text: "霑代＞蛟呵｣懊′隕九▽縺九ｊ縺ｾ縺励◆縲る∈謚槭＠縺ｦ縺上□縺輔＞縲・ }]);
      } else if (res.type === "answer") {
        setMessages((m) => [...m, { role: "bot", text: res.answer }]);
        setAwaitingFeedback(true);
      } else {
        setMessages((m) => [...m, { role: "bot", text: res.message }]);
        setAwaitingFeedback(true);
      }
    } catch (e) {
      setMessages((m) => [...m, { role: "system", text: `繧ｨ繝ｩ繝ｼ: ${String(e.message || e)}` }]);
    } finally {
      setLoading(false);
    }
  }

  async function chooseCandidate(id) {
    setLoading(true);
    try {
      const res = await chat(userId, { selection_id: id });
      setRequestId(res.request_id);
      setCandidates([]);
      setMessages((m) => [...m, { role: "bot", text: res.answer || res.message }]);
      setAwaitingFeedback(true);
    } catch (e) {
      setMessages((m) => [...m, { role: "system", text: `繧ｨ繝ｩ繝ｼ: ${String(e.message || e)}` }]);
    } finally {
      setLoading(false);
    }
  }

  async function notMatch() {
    setLoading(true);
    try {
      const res = await chat(userId, { action: "not_match", candidates_shown: candidates.map(c => c.id) });
      setRequestId(res.request_id);
      setCandidates([]);
      setMessages((m) => [...m, { role: "bot", text: res.message }]);
      setAwaitingFeedback(true);
    } catch (e) {
      setMessages((m) => [...m, { role: "system", text: `繧ｨ繝ｩ繝ｼ: ${String(e.message || e)}` }]);
    } finally {
      setLoading(false);
    }
  }

  async function sendFeedback(solved) {
    if (!requestId) return;
    setLoading(true);
    try {
      await feedback(userId, { request_id: requestId, solved });
      setAwaitingFeedback(false);
      setMessages((m) => [...m, { role: "system", text: solved ? "繝輔ぅ繝ｼ繝峨ヰ繝・け縺ゅｊ縺後→縺・＃縺悶＞縺ｾ縺呻ｼ郁ｧ｣豎ｺ・峨・ : "譛ｪ隗｣豎ｺ縺ｨ縺励※險倬鹸縺励∪縺励◆縲・ }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "system", text: `繝輔ぅ繝ｼ繝峨ヰ繝・け騾∽ｿ｡繧ｨ繝ｩ繝ｼ: ${String(e.message || e)}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <div className="header">
        <div className="title">遉ｾ蜀・撫縺・粋繧上○Bot</div>
        <div className="subtitle">蛟倶ｺｺ諠・ｱ繝ｻ讖溷ｯ・ｒ蜈･蜉帙＠縺ｪ縺・〒縺上□縺輔＞</div>
      </div>

      <div className="chat" ref={chatRef}>
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">{m.text}</div>
          </div>
        ))}

        {candidates.length > 0 && (
          <div className="candidates">
            <div className="candidatesTitle">蛟呵｣懶ｼ井ｸ贋ｽ搾ｼ・/div>
            <div className="candidatesList">
              {candidates.map((c) => (
                <button className="candidateBtn" key={c.id} disabled={loading} onClick={() => chooseCandidate(c.id)}>
                  {c.title}
                </button>
              ))}
            </div>
            <button className="notMatchBtn" disabled={loading} onClick={notMatch}>
              縺ｩ繧後ｂ驕輔≧
            </button>
          </div>
        )}

        {awaitingFeedback && (
          <div className="feedback">
            <div className="feedbackTitle">隗｣豎ｺ縺励∪縺励◆縺具ｼ滂ｼ亥ｿ・茨ｼ・/div>
            <div className="feedbackBtns">
              <button className="good" disabled={loading} onClick={() => sendFeedback(true)}>隗｣豎ｺ縺励◆ 総</button>
              <button className="bad" disabled={loading} onClick={() => sendFeedback(false)}>隗｣豎ｺ縺励↑縺・綜</button>
            </div>
          </div>
        )}

        {loading && <div className="loading">蜃ｦ逅・ｸｭ...</div>}
      </div>

      <div className="inputArea">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="雉ｪ蝠上ｒ蜈･蜉・
          onKeyDown={(e) => { if (e.key === "Enter") sendQuestion(); }}
        />
        <button disabled={loading} onClick={sendQuestion}>騾∽ｿ｡</button>
      </div>
    </div>
  );
}
"@

Write-TextFile ".\frontend\src\styles.css" @"
:root {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans JP",
    "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
  color: #111;
}
html, body, #root { height: 100%; margin: 0; }
.app { height: 100%; display: flex; flex-direction: column; background: #fff; }
.header { padding: 10px 12px; border-bottom: 1px solid #eee; }
.title { font-weight: 700; font-size: 14px; }
.subtitle { margin-top: 4px; font-size: 12px; color: #666; }
.chat { flex: 1; overflow: auto; padding: 12px; background: #fafafa; }
.msg { display: flex; margin: 6px 0; }
.msg.user { justify-content: flex-end; }
.msg.bot, .msg.system { justify-content: flex-start; }
.bubble { max-width: 90%; padding: 10px 12px; border-radius: 12px; background: #fff; border: 1px solid #eee; font-size: 13px; line-height: 1.4; }
.msg.user .bubble { background: #eaf3ff; border-color: #d4e7ff; }
.candidates { margin-top: 10px; padding: 10px; border: 1px dashed #ddd; border-radius: 10px; background: #fff; }
.candidatesTitle { font-size: 12px; color: #444; margin-bottom: 6px; }
.candidatesList { display: grid; gap: 8px; }
.candidateBtn { text-align: left; padding: 10px; border-radius: 10px; border: 1px solid #ddd; background: #fff; cursor: pointer; }
.candidateBtn:disabled { opacity: 0.6; cursor: not-allowed; }
.notMatchBtn { margin-top: 10px; width: 100%; padding: 10px; border-radius: 10px; border: 1px solid #f0c6c6; background: #fff4f4; cursor: pointer; }
.feedback { margin-top: 10px; padding: 10px; border: 1px solid #eee; border-radius: 10px; background: #fff; }
.feedbackTitle { font-size: 12px; color: #444; margin-bottom: 8px; }
.feedbackBtns { display: flex; gap: 8px; }
.feedbackBtns button { flex: 1; padding: 10px; border-radius: 10px; border: 1px solid #ddd; cursor: pointer; }
.feedbackBtns button.good { background: #eef9f0; border-color: #cfe9d5; }
.feedbackBtns button.bad { background: #fff4f4; border-color: #f0c6c6; }
.loading { margin-top: 10px; font-size: 12px; color: #666; }
.inputArea { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #eee; background: #fff; }
.inputArea input { flex: 1; padding: 10px; border-radius: 10px; border: 1px solid #ddd; font-size: 13px; }
.inputArea button { width: 72px; border-radius: 10px; border: 1px solid #ddd; background: #fff; cursor: pointer; }
.inputArea button:disabled { opacity: 0.6; cursor: not-allowed; }
"@

# ====== EXTENSION ======
Write-TextFile ".\extension\config.js" @"
window.CORPBOT_CONFIG = {
  API_BASE: "http://localhost:8000",
  CLIENT_VERSION: "ext-0.1.0"
};
"@

Write-TextFile ".\extension\manifest.json" @"
{
  "manifest_version": 3,
  "name": "CorpBot Widget",
  "version": "0.1.0",
  "description": "Gmail/Desknet's Neo 縺ｫ蜿ｳ荳句ｸｸ鬧舌・遉ｾ蜀・撫縺・粋繧上○繝懊ャ繝医ｒ陦ｨ遉ｺ縺励∪縺吶・,
  "icons": { "128": "icons/logo.png" },
  "content_scripts": [
    {
      "matches": [
        "https://mail.google.com/*",
        "https://REPLACE-YOUR-DESKNETS-DOMAIN/cgi-bin/dneo/*"
      ],
      "js": ["content.js"],
      "css": ["content.css"],
      "run_at": "document_idle"
    }
  ],
  "host_permissions": [
    "https://mail.google.com/*",
    "https://REPLACE-YOUR-DESKNETS-DOMAIN/cgi-bin/dneo/*",
    "http://localhost:8000/*"
  ],
  "web_accessible_resources": [
    {
      "resources": ["widget/*", "config.js", "icons/logo.png"],
      "matches": ["<all_urls>"]
    }
  ]
}
"@

Write-TextFile ".\extension\content.css" @"
#corpbot-shadow-host {
  all: initial;
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 2147483647;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans JP", Meiryo, sans-serif;
}
"@

Write-TextFile ".\extension\content.js" @"
(function () {
  const HOST_ID = "corpbot-shadow-host";
  if (document.getElementById(HOST_ID)) return;

  const host = document.createElement("div");
  host.id = HOST_ID;
  document.documentElement.appendChild(host);

  const shadow = host.attachShadow({ mode: "open" });

  const style = document.createElement("style");
  style.textContent = `
    .btn {
      width: 60px; height: 60px; border-radius: 999px;
      border: 1px solid rgba(0,0,0,0.12);
      background: #fff;
      box-shadow: 0 8px 24px rgba(0,0,0,0.18);
      cursor: pointer;
      display: grid;
      place-items: center;
      overflow: hidden;
    }
    .btn img { width: 44px; height: 44px; }
    .panel {
      position: fixed;
      right: 16px;
      bottom: 90px;
      width: 420px;
      height: 650px;
      border-radius: 12px;
      border: 1px solid rgba(0,0,0,0.12);
      box-shadow: 0 16px 40px rgba(0,0,0,0.25);
      background: #fff;
      overflow: hidden;
      opacity: 0;
      transform: translateY(8px);
      transition: opacity 0.3s ease, transform 0.3s ease;
      pointer-events: none;
    }
    .panel.open {
      opacity: 1;
      transform: translateY(0);
      pointer-events: auto;
    }
    .iframe { width: 100%; height: 100%; border: 0; }
    @media (max-width: 520px) {
      .panel { width: calc(100vw - 32px); height: min(650px, calc(100vh - 140px)); }
    }
  `;
  shadow.appendChild(style);

  const button = document.createElement("button");
  button.className = "btn";
  button.type = "button";
  const img = document.createElement("img");
  img.src = chrome.runtime.getURL("icons/logo.png");
  img.alt = "CorpBot";
  button.appendChild(img);

  const panel = document.createElement("div");
  panel.className = "panel";
  const iframe = document.createElement("iframe");
  iframe.className = "iframe";
  iframe.src = chrome.runtime.getURL("widget/index.html");
  panel.appendChild(iframe);

  button.addEventListener("click", () => {
    panel.classList.toggle("open");
  });

  shadow.appendChild(panel);
  shadow.appendChild(button);
})();
"@

# ====== BACKEND ======
Write-TextFile ".\backend\requirements.txt" @"
fastapi==0.115.6
uvicorn[standard]==0.32.1
python-dotenv==1.0.1
cachetools==5.5.0
PyJWT==2.10.1
google-api-python-client==2.157.0
google-auth==2.37.0
google-auth-httplib2==0.2.0
pydantic==2.10.4
"@

Write-TextFile ".\backend\.env.example" @"
ENV=dev

CORS_ORIGINS=
CORS_ORIGIN_REGEX=^chrome-extension://[a-p]{32}$

JWT_ISSUER=corpbot
JWT_AUDIENCE=corpbot-users
JWT_TTL_SECONDS=300
JWT_SIGNING_KEY_BASE64=__SET_STRONG_RANDOM_BASE64__

USER_HASH_SALT=__SET_STRONG_RANDOM__

ADMIN_TOKEN=__SET_STRONG_RANDOM__
CACHE_TTL_SECONDS=3600

VERSION_CELL_A1=E1
DATA_RANGE_A1=A:F

# 繝ｭ繝ｼ繧ｫ繝ｫ縺ｧSA JSON繧剃ｽｿ縺・↑繧峨√％縺薙↓繝輔ぃ繧､繝ｫ繝代せ
GOOGLE_APPLICATION_CREDENTIALS=C:\secrets\corpbot-sa.json

# 譛ｪ隗｣豎ｺ繝ｭ繧ｰ・磯°逕ｨ謾ｹ蝟・畑・・
UNRESOLVED_SHEET_ID=__SPREADSHEET_ID__
UNRESOLVED_SHEET_TAB=Unresolved
UNRESOLVED_APPEND_RANGE=A:K

# 驛ｨ髢蛻･繝翫Ξ繝・ず・域悴菴懈・縺ｯ遨ｺ谺・〒OK・昴せ繧ｭ繝・・・・
SYS_SHEET_ID=
GA_SHEET_ID=
LABOR_SHEET_ID=
LEGAL_SHEET_ID=
HR_SHEET_ID=
"@

Write-TextFile ".\backend\main.py" @"
import base64
import hashlib
import json
import os
import re
import time
import unicodedata
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import jwt
from cachetools import TTLCache
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from googleapiclient.discovery import build
from google.oauth2 import service_account

# ============================================================
# Load env
# ============================================================
load_dotenv()

ENV = os.getenv("ENV", "dev")

CORS_ORIGINS = [x.strip() for x in (os.getenv("CORS_ORIGINS") or "").split(",") if x.strip()]
CORS_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX", r"^chrome-extension://[a-p]{32}$")

JWT_ISSUER = os.getenv("JWT_ISSUER", "corpbot")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "corpbot-users")
JWT_TTL_SECONDS = int(os.getenv("JWT_TTL_SECONDS", "300"))
JWT_SIGNING_KEY_BASE64 = os.getenv("JWT_SIGNING_KEY_BASE64", "")
USER_HASH_SALT = os.getenv("USER_HASH_SALT", "")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

VERSION_CELL_A1 = os.getenv("VERSION_CELL_A1", "E1")
DATA_RANGE_A1 = os.getenv("DATA_RANGE_A1", "A:F")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

UNRESOLVED_SHEET_ID = os.getenv("UNRESOLVED_SHEET_ID", "")
UNRESOLVED_SHEET_TAB = os.getenv("UNRESOLVED_SHEET_TAB", "Unresolved")
UNRESOLVED_APPEND_RANGE = os.getenv("UNRESOLVED_APPEND_RANGE", "A:K")

DEPT_SHEETS = {
    "繧ｷ繧ｹ繝・Β隱ｲ": os.getenv("SYS_SHEET_ID", ""),
    "邱丞漁": os.getenv("GA_SHEET_ID", ""),
    "蜉ｴ蜍・: os.getenv("LABOR_SHEET_ID", ""),
    "豕募漁": os.getenv("LEGAL_SHEET_ID", ""),
    "莠ｺ莠・: os.getenv("HR_SHEET_ID", ""),
}

EXTENSIONS = {
    "繧ｷ繧ｹ繝・Β隱ｲ": "1001",
    "邱丞漁": "1002",
    "蜉ｴ蜍・: "1003",
    "豕募漁": "1004",
    "莠ｺ莠・: "1005",
}

# ============================================================
# Helpers
# ============================================================
def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def now_jst() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))

def iso(dt: datetime) -> str:
    return dt.isoformat()

def normalize_text(s: str) -> str:
    s = s or ""
    s = unicodedata.normalize("NFKC", s)
    s = s.strip().lower()
    s = re.sub(r"\\s+", " ", s)
    return s

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
DIGIT_RE = re.compile(r"\\d")
PHONE_RE = re.compile(r"\\b\\d{2,4}-\\d{2,4}-\\d{3,4}\\b")

def mask_query(s: str, n: int = 60) -> str:
    s = (s or "")[:n]
    s = EMAIL_RE.sub("[email]", s)
    s = PHONE_RE.sub("[phone]", s)
    s = DIGIT_RE.sub("X", s)
    return s

def user_hash(user_id: str) -> str:
    # 蜴滓枚菫晏ｭ倡ｦ∵ｭ｢・嘖alt + user_id 繧痴ha256
    raw = (USER_HASH_SALT + "|" + (user_id or "")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def load_jwt_key() -> bytes:
    if not JWT_SIGNING_KEY_BASE64:
        raise RuntimeError("JWT_SIGNING_KEY_BASE64 is not set")
    return base64.b64decode(JWT_SIGNING_KEY_BASE64.encode("utf-8"))

def issue_jwt(sub: str) -> Tuple[str, int]:
    key = load_jwt_key()
    exp = int(time.time()) + JWT_TTL_SECONDS
    payload = {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": sub,
        "iat": int(time.time()),
        "exp": exp,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, key, algorithm="HS256")
    return token, JWT_TTL_SECONDS

def verify_jwt(token: str) -> str:
    key = load_jwt_key()
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["HS256"],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
        return str(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

# ============================================================
# Google Sheets client
# ============================================================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/spreadsheets"]

def build_sheets_client():
    if GOOGLE_APPLICATION_CREDENTIALS and os.path.isfile(GOOGLE_APPLICATION_CREDENTIALS):
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES
        )
    else:
        # ADC・・loud Run謗ｨ螂ｨ・・
        creds = None
    return build("sheets", "v4", credentials=creds, cache_discovery=False)

sheets = build_sheets_client()

def get_values(spreadsheet_id: str, range_a1: str) -> List[List[str]]:
    resp = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_a1,
        valueRenderOption="UNFORMATTED_VALUE",
    ).execute()
    return resp.get("values", []) or []

def append_values(spreadsheet_id: str, range_a1: str, row: List[Any]) -> None:
    sheets.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_a1,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()

# ============================================================
# Cache (TTL 60min + version-cell auto refresh)
# ============================================================
dept_cache = TTLCache(maxsize=32, ttl=CACHE_TTL_SECONDS)  # dept -> {version, rows}
version_cache = TTLCache(maxsize=64, ttl=60)  # E1 check is light; cache 60s to reduce API

def read_dept_version(dept: str, sheet_id: str) -> str:
    if not sheet_id:
        return ""
    key = f"{dept}:{sheet_id}"
    if key in version_cache:
        return version_cache[key]
    v = ""
    try:
        vals = get_values(sheet_id, f"{VERSION_CELL_A1}")
        if vals and vals[0]:
            v = str(vals[0][0])
    except Exception:
        v = ""
    version_cache[key] = v
    return v

def load_dept_rows(dept: str, sheet_id: str) -> Dict[str, Any]:
    # Full load A:F
    rows_raw = get_values(sheet_id, DATA_RANGE_A1)
    # Expect header row, but tolerate missing
    rows = []
    for idx, r in enumerate(rows_raw):
        # row number in sheet is idx+1
        a = str(r[0]) if len(r) > 0 else ""
        b = str(r[1]) if len(r) > 1 else ""
        c = str(r[2]) if len(r) > 2 else ""
        d = str(r[3]) if len(r) > 3 else ""
        e = str(r[4]) if len(r) > 4 else ""
        f = str(r[5]) if len(r) > 5 else ""
        if idx == 0 and normalize_text(b) in ("雉ｪ蝠・, "q", "question"):
            continue
        # 蜈ｬ髢九ヵ繝ｩ繧ｰ縺後≠繧九↑繧欝RUE縺ｮ縺ｿ蜿ら・・育ｩｺ谺・・蜈ｬ髢区桶縺・↓縺吶ｋ・壼ｮ牙・蛛ｴ縺ｧ螟峨∴繧九↑繧峨％縺薙ｒFALSE謇ｱ縺・↓・・
        is_public = True
        if f != "":
            is_public = str(f).strip().upper() == "TRUE"
        if not is_public:
            continue
        rows.append({
            "row_no": idx + 1,
            "keywords": a,
            "q": b,
            "a": c,
            "dept": d or dept,
            "version_row": e,
        })
    version = read_dept_version(dept, sheet_id)
    return {"version": version, "rows": rows}

def get_dept_data(dept: str, sheet_id: str) -> Optional[Dict[str, Any]]:
    if not sheet_id:
        return None
    cached = dept_cache.get(dept)
    current_v = read_dept_version(dept, sheet_id)
    if cached and cached.get("version") == current_v:
        return cached
    # reload
    data = load_dept_rows(dept, sheet_id)
    dept_cache[dept] = data
    return data

def refresh_cache(dept: Optional[str] = None) -> None:
    if dept:
        dept_cache.pop(dept, None)
        return
    dept_cache.clear()

# ============================================================
# Search
# ============================================================
def exact_match(query: str, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    nq = normalize_text(query)
    for r in rows:
        if normalize_text(r.get("q", "")) == nq:
            return r
    return None

def keyword_score(query: str, row: Dict[str, Any]) -> float:
    nq = normalize_text(query)
    raw = row.get("keywords", "") or ""
    parts = [normalize_text(x) for x in raw.split(",") if normalize_text(x)]
    if not parts:
        return 0.0
    hit = 0
    for kw in parts:
        if kw and kw in nq:
            hit += 1
    return hit / max(len(parts), 1)

def top_candidates(query: str, rows: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    scored = []
    for r in rows:
        s = keyword_score(query, r)
        if s > 0:
            scored.append((s, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for s, r in scored[:limit]:
        out.append(r)
    return out

# ============================================================
# Audit logging (structured JSON -> Cloud Logging on Cloud Run)
# ============================================================
def audit_log(payload: Dict[str, Any]) -> None:
    # Cloud Run: stdout JSON -> jsonPayload
    print(json.dumps(payload, ensure_ascii=False))

# ============================================================
# Rate limiting (simple in-memory)
# ============================================================
rate_cache = TTLCache(maxsize=4096, ttl=60)  # key -> count

def rate_limit(key: str, limit: int = 30) -> Tuple[bool, str]:
    c = int(rate_cache.get(key, 0)) + 1
    rate_cache[key] = c
    if c > limit:
        return False, "blocked"
    return True, "ok"

# ============================================================
# FastAPI
# ============================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else [],
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

class AuthExchangeReq(BaseModel):
    user_id: str = Field(..., min_length=8)
    client_version: str = Field(..., min_length=1, max_length=64)

class AuthExchangeRes(BaseModel):
    token: str
    expires_in_seconds: int

class ChatReq(BaseModel):
    question: Optional[str] = None
    selection_id: Optional[str] = None
    action: Optional[str] = None  # not_match
    candidates_shown: Optional[List[str]] = None

class CandidateItem(BaseModel):
    id: str
    title: str

class ChatRes(BaseModel):
    request_id: str
    type: str  # candidates/answer/none
    message: Optional[str] = None
    answer: Optional[str] = None
    candidates: Optional[List[CandidateItem]] = None

class FeedbackReq(BaseModel):
    request_id: str
    solved: bool

@app.get("/healthz")
def healthz():
    return {"ok": True}

def require_admin(x_admin_token: Optional[str]) -> None:
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="admin token not configured")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")

@app.post("/admin/cache/refresh")
def admin_cache_refresh(department: Optional[str] = None, x_admin_token: Optional[str] = Header(default=None)):
    require_admin(x_admin_token)
    if department and department not in DEPT_SHEETS:
        raise HTTPException(status_code=400, detail="unknown department")
    refresh_cache(department)
    return {"ok": True, "refreshed": department or "ALL"}

@app.post("/api/auth/exchange", response_model=AuthExchangeRes)
def auth_exchange(req: AuthExchangeReq, request: Request):
    rid = str(uuid.uuid4())
    uhash = user_hash(req.user_id)

    ip = request.client.host if request.client else ""
    ok, st = rate_limit(f"auth:{uhash}:{ip}", limit=60)
    if not ok:
        audit_log({
            "kind": "audit",
            "event": "auth_exchange",
            "request_id": rid,
            "timestamp_utc": iso(now_utc()),
            "timestamp_jst": iso(now_jst()),
            "user_hash": uhash,
            "client_version": req.client_version,
            "rate_limit_status": st,
            "error_code": "RATE_LIMIT",
        })
        raise HTTPException(status_code=429, detail="rate limited")

    token, ttl = issue_jwt(uhash)

    audit_log({
        "kind": "audit",
        "event": "auth_exchange",
        "request_id": rid,
        "timestamp_utc": iso(now_utc()),
        "timestamp_jst": iso(now_jst()),
        "user_hash": uhash,
        "client_version": req.client_version,
        "rate_limit_status": st,
    })
    return AuthExchangeRes(token=token, expires_in_seconds=ttl)

def parse_selection_id(sel: str) -> Tuple[str, int]:
    # format: <dept>|<row_no>
    try:
        dept, row = sel.split("|", 1)
        return dept, int(row)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid selection_id")

def build_selection_id(dept: str, row_no: int) -> str:
    return f"{dept}|{row_no}"

def extension_guide_message() -> str:
    # 蝗ｺ螳壹ョ繝ｼ繧ｿ蜿ら・・育函謌千ｦ∵ｭ｢・・
    lines = ["隧ｲ蠖薙☆繧九リ繝ｬ繝・ず縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ縺ｧ縺励◆縲よ球蠖馴Κ髢縺ｸ縺企崕隧ｱ縺上□縺輔＞・亥・邱壹・蝗ｺ螳壹ョ繝ｼ繧ｿ縺ｧ縺呻ｼ峨・]
    for d, ext in EXTENSIONS.items():
        lines.append(f"- {d}・壼・邱・{ext}")
    return "\\n".join(lines)

# 譛ｪ隗｣豎ｺ繝√こ繝・ヨ驥崎､・亟豁｢・・equest_id蜊倅ｽ搾ｼ・
unresolved_dedupe = TTLCache(maxsize=4096, ttl=24*3600)

def append_unresolved(ticket: Dict[str, Any]) -> None:
    if not UNRESOLVED_SHEET_ID:
        return
    tid = ticket.get("ticket_id")
    if not tid:
        return
    if tid in unresolved_dedupe:
        return
    unresolved_dedupe[tid] = True

    row = [
        ticket.get("ticket_id"),
        ticket.get("created_at"),
        ticket.get("department_guess"),
        ticket.get("query_summary"),
        json.dumps(ticket.get("candidates_shown") or [], ensure_ascii=False),
        ticket.get("user_feedback"),
        ticket.get("status"),
        ticket.get("assignee"),
        ticket.get("notes"),
        ticket.get("resolution_link"),
        ticket.get("closed_at"),
    ]
    try:
        append_values(
            UNRESOLVED_SHEET_ID,
            f"{UNRESOLVED_SHEET_TAB}!{UNRESOLVED_APPEND_RANGE}",
            row
        )
    except Exception:
        # 逶｣譟ｻ繝ｭ繧ｰ縺ｫ縺ｯ繧ｨ繝ｩ繝ｼ繧ｳ繝ｼ繝峨□縺托ｼ磯℃蜑ｰ諠・ｱ繧定ｿ斐＆縺ｪ縺・ｼ・
        pass

@app.post("/api/chat", response_model=ChatRes)
def api_chat(
    req: ChatReq,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    rid = str(uuid.uuid4())
    tsu = iso(now_utc()); tsj = iso(now_jst())

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    sub = verify_jwt(authorization.split(" ", 1)[1])

    ip = request.client.host if request.client else ""
    ok, rl = rate_limit(f"chat:{sub}:{ip}", limit=60)
    if not ok:
        audit_log({
            "kind": "audit",
            "event": "chat",
            "request_id": rid,
            "timestamp_utc": tsu,
            "timestamp_jst": tsj,
            "user_hash": sub,
            "source": "none",
            "searched_departments": [],
            "hit_department": None,
            "hit_row_id": None,
            "candidates": [],
            "selection_id": req.selection_id,
            "solved": "unknown",
            "client_version": None,
            "rate_limit_status": rl,
            "error_code": "RATE_LIMIT"
        })
        raise HTTPException(status_code=429, detail="rate limited")

    searched = []
    candidates_ids = []
    hit_dept = None
    hit_row = None
    source = "none"
    selection_id = req.selection_id

    # 1) selection flow
    if req.selection_id:
        dept, row_no = parse_selection_id(req.selection_id)
        sheet_id = DEPT_SHEETS.get(dept, "")
        if not sheet_id:
            raise HTTPException(status_code=400, detail="department not configured")
        data = get_dept_data(dept, sheet_id) or {"rows": []}
        searched = [dept]
        row = next((r for r in data["rows"] if r["row_no"] == row_no), None)
        if not row:
            raise HTTPException(status_code=404, detail="row not found")
        hit_dept = dept
        hit_row = row_no
        source = "candidate"
        ans = row.get("a") or extension_guide_message()

        audit_log({
            "kind": "audit",
            "event": "chat",
            "request_id": rid,
            "timestamp_utc": tsu,
            "timestamp_jst": tsj,
            "user_hash": sub,
            "source": source,
            "searched_departments": searched,
            "hit_department": hit_dept,
            "hit_row_id": hit_row,
            "candidates": [],
            "selection_id": selection_id,
            "solved": "unknown",
            "rate_limit_status": rl
        })
        return ChatRes(request_id=rid, type="answer", answer=ans)

    # not_match action -> unresolved
    if req.action == "not_match":
        msg = extension_guide_message()
        audit_log({
            "kind": "audit",
            "event": "chat",
            "request_id": rid,
            "timestamp_utc": tsu,
            "timestamp_jst": tsj,
            "user_hash": sub,
            "source": "none",
            "searched_departments": [],
            "hit_department": None,
            "hit_row_id": None,
            "candidates": req.candidates_shown or [],
            "selection_id": None,
            "solved": "unknown",
            "rate_limit_status": rl
        })

        ticket = {
            "ticket_id": rid,
            "created_at": tsj,
            "department_guess": "unknown",
            "query_summary": "",
            "candidates_shown": req.candidates_shown or [],
            "user_feedback": "not_match",
            "status": "NEW",
            "assignee": "",
            "notes": "",
            "resolution_link": "",
            "closed_at": ""
        }
        append_unresolved(ticket)
        return ChatRes(request_id=rid, type="none", message=msg)

    # 2) question search
    q = (req.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="missing question")

    all_rows = []
    for dept, sheet_id in DEPT_SHEETS.items():
        if not sheet_id:
            continue
        searched.append(dept)
        data = get_dept_data(dept, sheet_id)
        if not data:
            continue
        for r in data["rows"]:
            r2 = dict(r)
            r2["_dept"] = dept
            all_rows.append(r2)

    # exact
    ex = exact_match(q, all_rows)
    if ex:
        hit_dept = ex["_dept"]
        hit_row = ex["row_no"]
        source = "exact"
        ans = ex.get("a") or extension_guide_message()
        audit_log({
            "kind": "audit",
            "event": "chat",
            "request_id": rid,
            "timestamp_utc": tsu,
            "timestamp_jst": tsj,
            "user_hash": sub,
            "source": source,
            "searched_departments": searched,
            "hit_department": hit_dept,
            "hit_row_id": hit_row,
            "candidates": [],
            "selection_id": None,
            "solved": "unknown",
            "rate_limit_status": rl
        })
        return ChatRes(request_id=rid, type="answer", answer=ans)

    # keyword candidates
    cands = top_candidates(q, all_rows, limit=5)
    if cands:
        source = "keyword"
        items = []
        for r in cands:
            cid = build_selection_id(r["_dept"], r["row_no"])
            candidates_ids.append(cid)
            title = (r.get("q") or "").strip()
            if len(title) > 80:
                title = title[:80] + "窶ｦ"
            items.append(CandidateItem(id=cid, title=title or f"{r['_dept']} row {r['row_no']}"))

        audit_log({
            "kind": "audit",
            "event": "chat",
            "request_id": rid,
            "timestamp_utc": tsu,
            "timestamp_jst": tsj,
            "user_hash": sub,
            "source": source,
            "searched_departments": searched,
            "hit_department": None,
            "hit_row_id": None,
            "candidates": candidates_ids,
            "selection_id": None,
            "solved": "unknown",
            "rate_limit_status": rl
        })
        return ChatRes(request_id=rid, type="candidates", candidates=items)

    # none -> unresolved ticket
    msg = extension_guide_message()
    audit_log({
        "kind": "audit",
        "event": "chat",
        "request_id": rid,
        "timestamp_utc": tsu,
        "timestamp_jst": tsj,
        "user_hash": sub,
        "source": "none",
        "searched_departments": searched,
        "hit_department": None,
        "hit_row_id": None,
        "candidates": [],
        "selection_id": None,
        "solved": "unknown",
        "rate_limit_status": rl
    })

    ticket = {
        "ticket_id": rid,
        "created_at": tsj,
        "department_guess": "unknown",
        "query_summary": mask_query(q),
        "candidates_shown": [],
        "user_feedback": "none",
        "status": "NEW",
        "assignee": "",
        "notes": "",
        "resolution_link": "",
        "closed_at": ""
    }
    append_unresolved(ticket)
    return ChatRes(request_id=rid, type="none", message=msg)

@app.post("/api/feedback")
def api_feedback(
    req: FeedbackReq,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    rid = str(uuid.uuid4())
    tsu = iso(now_utc()); tsj = iso(now_jst())

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    sub = verify_jwt(authorization.split(" ", 1)[1])

    ip = request.client.host if request.client else ""
    ok, rl = rate_limit(f"fb:{sub}:{ip}", limit=120)
    if not ok:
        raise HTTPException(status_code=429, detail="rate limited")

    solved_val = True if req.solved else False

    audit_log({
        "kind": "audit",
        "event": "feedback",
        "request_id": rid,
        "timestamp_utc": tsu,
        "timestamp_jst": tsj,
        "user_hash": sub,
        "solved": solved_val,
        "rate_limit_status": rl
    })

    if not solved_val:
        ticket = {
            "ticket_id": req.request_id,  # 蜈ビequest_id縺ｧ繝√こ繝・ヨ蛹厄ｼ磯㍾隍・亟豁｢・・
            "created_at": tsj,
            "department_guess": "unknown",
            "query_summary": "",
            "candidates_shown": [],
            "user_feedback": "not_solved",
            "status": "NEW",
            "assignee": "",
            "notes": "",
            "resolution_link": "",
            "closed_at": ""
        }
        append_unresolved(ticket)

    return {"ok": True}
"@

Write-Host "DONE. Files generated/overwritten."
# Write-Host "Next:"
# Write-Host "  1) backend\.env 繧剃ｽ懈・縺励※蛟､繧定ｨｭ螳・
# Write-Host "  2) frontend: npm install / npm run build"
# Write-Host "  3) chrome://extensions 縺ｧ extension 繧定ｪｭ縺ｿ霎ｼ縺ｿ"
