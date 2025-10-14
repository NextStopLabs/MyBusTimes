(() => {
  const ENDPOINT_HOST = "https://status.mybustimes.cc";
  const HEARTBEAT_ENDPOINT = `${ENDPOINT_HOST}/api/status-page/heartbeat/mbt`;
  const STATUSPAGE_ENDPOINT = `${ENDPOINT_HOST}/api/status-page/mbt`;
  const POLL_INTERVAL_SECONDS = 30;
  let autoIntervalId = null;

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    const content = document.getElementById("content");
    if (!content) {
      console.error(
        'status.js: required element #content not found. Insert <div id="content"></div> in your template.'
      );
      return;
    }

    // Find a parent .status container to host controls; fallback to content.parentElement
    const statusContainer =
      document.querySelector(".status") ||
      content.parentElement ||
      document.body;

    // Try to locate existing controls, otherwise create a minimal controls bar
    let lastUpdated = document.getElementById("lastUpdated");
    let intervalLabel = document.getElementById("intervalLabel");

    if (!lastUpdated || !intervalLabel) {
      // create a small controls bar and insert it before #content
      const controls = document.createElement("div");
      controls.id = "status-controls";
      controls.style.display = "flex";
      controls.style.gap = "8px";
      controls.style.alignItems = "center";
      controls.style.marginBottom = "10px";

      intervalLabel = document.createElement("span");
      intervalLabel.id = "intervalLabel";
      intervalLabel.className = "small";
      intervalLabel.style.marginLeft = "6px";
      intervalLabel.textContent = String(POLL_INTERVAL_SECONDS);

      lastUpdated = document.createElement("div");
      lastUpdated.id = "lastUpdated";
      lastUpdated.className = "small muted";
      lastUpdated.style.marginLeft = "auto";
      lastUpdated.textContent = "Never updated";

      controls.appendChild(lastUpdated);

      statusContainer.insertBefore(controls, content);
    } else {
      intervalLabel.textContent = String(POLL_INTERVAL_SECONDS);
    }

    // Optional site-level elements (may or may not exist in your base template)
    const siteTitleEl = document.getElementById("siteTitle") || null;
    const siteDescEl = document.getElementById("siteDesc") || null;
    const siteIconEl = document.getElementById("siteIcon") || null;
    const footerEl = document.getElementById("footer") || null;

    // initial load + auto refresh
    fetchAndRender();
    if (autoIntervalId) clearInterval(autoIntervalId);
    autoIntervalId = setInterval(fetchAndRender, POLL_INTERVAL_SECONDS * 1000);

    // core fetch + render
    async function fetchAndRender() {
      try {
        const [hbRes, spRes] = await Promise.all([
          fetch(HEARTBEAT_ENDPOINT, { cache: "no-store" }),
          fetch(STATUSPAGE_ENDPOINT, { cache: "no-store" }),
        ]);

        if (!hbRes.ok) throw new Error(`Heartbeat HTTP ${hbRes.status}`);
        if (!spRes.ok) throw new Error(`Status page HTTP ${spRes.status}`);

        const heartbeatJson = await hbRes.json();
        const statusJson = await spRes.json();

        renderAll(heartbeatJson, statusJson, content, {
          siteTitleEl,
          siteDescEl,
          siteIconEl,
          footerEl,
        });

        lastUpdated.textContent = "Updated: " + new Date().toLocaleString();

      } catch (err) {
        renderError(err, content);
        lastUpdated.textContent = "";
        statusContainer.style.display = "none";
        lastUpdated.style.display = "none";
        console.error("status.js fetch error:", err);
      }
    }
  }

  // Render helpers
  function renderError(err, container) {
    container.innerHTML = "";
    const card = document.createElement("div");
    card.className = "card";
    card.style.padding = "12px";
    card.style.background = "#0000";
    card.style.borderRadius = "8px";
    card.innerHTML = ``;
    container.appendChild(card);
  }

  function renderAll(heartbeatData, statusData, contentEl, siteEls) {
    const cfg = statusData.config || {};
    if (siteEls.siteTitleEl)
      siteEls.siteTitleEl.textContent =
        cfg.title || siteEls.siteTitleEl.textContent;
    if (siteEls.siteDescEl)
      siteEls.siteDescEl.textContent =
        cfg.description || siteEls.siteDescEl.textContent;
    if (siteEls.siteIconEl && cfg.icon) {
      try {
        siteEls.siteIconEl.src = new URL(cfg.icon, ENDPOINT_HOST).toString();
        siteEls.siteIconEl.hidden = false;
      } catch {
        siteEls.siteIconEl.hidden = true;
      }
    }
    if (siteEls.footerEl && cfg.footerText) {
      siteEls.footerEl.innerHTML = cfg.footerText;
    }

    const monitorMap = {};
    (statusData.publicGroupList || []).forEach((g) => {
      (g.monitorList || []).forEach((m) => {
        monitorMap[String(m.id)] = {
          name: m.name || `Monitor ${m.id}`,
          url: m.url || "",
          type: m.type || "",
        };
      });
    });

    const heartbeatList = heartbeatData.heartbeatList || {};
    const uptimeList = heartbeatData.uptimeList || {};
    const maintenanceList = statusData.maintenanceList || [];

    contentEl.innerHTML = "";

    // --- Maintenance section ---
    if (maintenanceList.length > 0) {
      maintenanceList
        .filter((m) => m.active || m.status === "under-maintenance")
        .forEach((m) => {
          const card = document.createElement("div");
          card.className = "card";
          card.style.padding = "12px";
          card.style.borderRadius = "8px";
          card.style.marginBottom = "8px";
          card.style.background = "#0000";

          card.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <div>
              <div style="font-weight:700">${escapeHtml(m.title)}</div>
              <div style="font-size:13px;color:var(--text-color)">${escapeHtml(
                m.description || ""
              )}</div>
            </div>
            <div style="text-align:right">
              <span style="display:inline-block;padding:2px 6px;border-radius:4px;background:#3498db;color:#fff;font-size:12px;font-weight:600">
                Under Maintenance
              </span>
            </div>
          </div>
        `;

          contentEl.appendChild(card);
        });
        if (m < 1) {
          lastUpdated.textContent = "";
          statusContainer.style.display = "none";
          lastUpdated.style.display = "none";
        }
    }

    // --- Monitor section ---
    const ids = Object.keys(heartbeatList)
      .filter((id) => {
        const entries = heartbeatList[id] || [];
        const last = entries[entries.length - 1];
        return last?.status !== 1; // exclude UP (status 1)
      })
      .sort((a, b) => Number(a) - Number(b));

    if (ids.length === 0 && maintenanceList.length === 0) {
      statusContainer.style.display = "none";
      lastUpdated.style.display = "none";
      contentEl.innerHTML = ""; // clear old content
      return;
    } else {
      statusContainer.style.display = "block";
      lastUpdated.style.display = "block";
    }

    ids.forEach((id) => {
      const entries = heartbeatList[id] || [];
      const last = entries[entries.length - 1];
      const avgPing = average(entries.map((e) => e.ping));
      const upKey24 = `${id}_24`;
      const uptime24 = uptimeList[upKey24];
      const info = monitorMap[id] || {
        name: `Monitor ${id}`,
        url: "",
        type: "",
      };

      const card = document.createElement("div");
      card.className = "card";
      card.style.padding = "12px";
      card.style.borderRadius = "8px";
      card.style.marginBottom = "8px";
      card.style.background = "#0000";

      console.log(last?.status);

      const statusLabel = statusToLabel(last?.status ?? null);
      const dotColor = statusToColor(last?.status ?? null);

      const SEGMENTS = 40;
      const recent = entries.slice(-SEGMENTS);
      const segmentHtml = recent
        .map((e) => {
          const status = e.status;
          const ping = Number(e.ping) || 0;
          const hhmm = formatTimeShort(e.time);
          const color = statusToColor(status);
          const title = `${statusToLabel(status)} • ${hhmm} • ${ping} ms`;
          return `<span class="sb-seg" title="${escapeHtml(
            title
          )}" style="background:${color};"></span>`;
        })
        .join("");
      const placeholders = Math.max(0, SEGMENTS - recent.length);
      const placeholderHtml = Array.from({ length: placeholders })
        .map(() => `<span class="sb-seg sb-empty" title="no data"></span>`)
        .join("");

      card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <div>
          <div style="font-weight:700">${escapeHtml(
            info.name
          )} <span class="small" style="color:var(--text-color);font-weight:400">${
        info.type ? " • " + escapeHtml(info.type) : ""
      }</span></div>
          <div style="font-size:13px;color:var(--text-color)">${
            info.url
              ? `<a href="${escapeHtml(
                  info.url
                )}" target="_blank" rel="noopener">${escapeHtml(info.url)}</a>`
              : ""
          }</div>
        </div>
        <div style="text-align:right">
          <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${dotColor};margin-right:6px;vertical-align:middle"></span><span style="font-weight:700">${statusLabel}</span></div>
          <div style="font-size:12px;color:var(--text-color)">${
            uptime24 !== undefined
              ? `<strong style="color:var(--text-color,#06b6d4)">${(
                  uptime24 * 100
                ).toFixed(2)}%</strong> (24h)`
              : `<span style="color:#94a3b8">no uptime</span>`
          }</div>
        </div>
      </div>

      <div class="status-bar" style="display:flex;gap:2px;height:14px;border-radius:6px;overflow:hidden;margin-bottom:8px">
        ${segmentHtml}${placeholderHtml}
      </div>

      <div style="display:flex;justify-content:space-between;align-items:center;font-size:13px;color:var(--text-color);">
        <div>Avg ping: <strong style="color:inherit">${Number(avgPing).toFixed(
          0
        )} ms</strong></div>
        <div>Last: ${formatTimeShort(last?.time)} ${
        last?.msg ? "• " + escapeHtml(last.msg) : ""
      }</div>
      </div>
    `;

      const style = document.createElement("style");
      style.textContent = `
      .sb-seg { flex:1 1 0; display:inline-block; height:100%; border-radius:1px; opacity:0.95; }
      .sb-empty { background: linear-gradient(90deg, rgba(148,163,184,0.08), rgba(148,163,184,0.04)); }
    `;
      card.appendChild(style);

      contentEl.appendChild(card);
    });
  }

  // small helpers
  function formatTimeShort(timestr) {
    if (!timestr) return "";

    try {
      let d;

      // Case: "2025-09-16 12:34:56" → treat as UTC
      if (typeof timestr === "string" && timestr.includes(" ")) {
        d = new Date(timestr.replace(" ", "T") + "Z");
      }
      // Case: already ISO string or timestamp
      else {
        d = new Date(timestr);
      }

      return d.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    } catch {
      return String(timestr);
    }
  }

  function average(arr) {
    if (!arr || arr.length === 0) return 0;
    const sum = arr.reduce((s, v) => s + (Number(v) || 0), 0);
    return sum / arr.length;
  }

  function statusToLabel(status) {
    switch (status) {
      case 0:
        return "DOWN";
      case 1:
        return "UP";
      case 2:
        return "DEGRADED";
      case 3:
        return "UNDER MAINTENANCE";
      case 4:
        return "UNKNOWN";
      default:
        return "N/A";
    }
  }

  function statusToColor(status) {
    switch (status) {
      case 0:
        return "#e74c3c";
      case 1:
        return "#27ae60";
      case 2:
        return "#f39c12";
      case 3:
        return "#3498db";
      case 4:
        return "#fff";
      default:
        return "#94a3b8";
    }
  }

  function escapeHtml(text) {
    if (text === undefined || text === null) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
})();
