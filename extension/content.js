(function () {
  const HOST_ID = "corpbot-shadow-host";
  if (document.getElementById(HOST_ID)) return;

  function waitForBody(maxMs = 8000) {
    return new Promise((resolve) => {
      const start = Date.now();
      const t = setInterval(() => {
        if (document.body) {
          clearInterval(t);
          resolve(true);
          return;
        }
        if (Date.now() - start > maxMs) {
          clearInterval(t);
          resolve(false);
        }
      }, 50);
    });
  }

  async function boot() {
    await waitForBody();

    if (document.getElementById(HOST_ID)) return;

    const host = document.createElement("div");
    host.id = HOST_ID;

    const mount = document.body || document.documentElement;
    mount.appendChild(host);

    const shadow = host.attachShadow({ mode: "open" });

    const style = document.createElement("style");
    style.textContent = `
      :host { all: initial; }

	  @keyframes bounce {
		  0%, 80%, 100% { transform: scale(1); }
		  85% { transform: scale(1.1); }
		  90% { transform: scale(0.95); }
		  95% { transform: scale(1.05); }
		}

      .btn {
        position: fixed;
        right: 16px;
        bottom: 30px;
        width: 60px;
        height: 60px;
        border-radius: 999px;
        border: 1px solid rgba(0,0,0,0.12);

        background: linear-gradient(135deg, #4285f4 0%, #ff73b3 100%);
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
        cursor: pointer;
        display: grid;
        place-items: center;
        overflow: hidden;
        z-index: 2147483647;
		animation: bounce 3s infinite;
      }

	  .btn:hover {
		  transform: scale(1.1);
		  animation: none;
		}

      .btn img { width: 44px; height: 44px; }

      .panel {
        position: fixed;
        right: 16px;
        bottom: 92px;
        width: 460px;
        height: min(840px, calc(100vh - 140px));
        max-height: calc(100vh - 140px);
        border-radius: 12px;
        border: 1px solid rgba(0,0,0,0.12);
        box-shadow: 0 16px 40px rgba(0,0,0,0.25);
        background: #fff;
        overflow: hidden;
        opacity: 0;
        transform: translateY(8px);
        transition: opacity 0.2s ease, transform 0.2s ease;
        pointer-events: none;
        z-index: 2147483647;
      }
      .panel.open {
        opacity: 1;
        transform: translateY(0);
        pointer-events: auto;
      }

      .iframe { width: 100%; height: 100%; border: 0; }

      @media (max-height: 840px) {
        .panel { bottom: 76px; height: calc(100vh - 120px); }
      }
    `;
    shadow.appendChild(style);

    try {
      const cssUrl = chrome.runtime.getURL("content.css");
      fetch(cssUrl)
        .then((r) => (r.ok ? r.text() : ""))
        .then((cssText) => {
          if (!cssText) return;
          const extStyle = document.createElement("style");
          extStyle.textContent = cssText;
          if (style.parentNode === shadow) shadow.insertBefore(extStyle, style);
          else shadow.appendChild(extStyle);
        })
        .catch(() => {});
    } catch {}

    const button = document.createElement("button");
    button.id = "corpbot-fab";
    button.className = "btn";
    button.type = "button";
    button.setAttribute("aria-label", "CorpBot を開く");

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

    const closePanel = () => panel.classList.remove("open");
    const togglePanel = () => panel.classList.toggle("open");

    button.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      togglePanel();
    });

    document.addEventListener(
      "click",
      (e) => {
        if (!panel.classList.contains("open")) return;
        const path = typeof e.composedPath === "function" ? e.composedPath() : [];
        const clickedInside = path.includes(host) || host.contains(e.target);
        if (!clickedInside) closePanel();
      },
      true
    );

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closePanel();
    });

    shadow.appendChild(panel);
    shadow.appendChild(button);

    if (document.body && host.parentElement !== document.body) {
      try {
        document.body.appendChild(host);
      } catch {}
    }
  }

  boot();
})();
