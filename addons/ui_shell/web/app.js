const t = (key, vars) => window.LS_I18N.t(key, vars);
const app = document.getElementById("app");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
function viewFromPath(pathname) {
  const match = String(pathname || "").match(/^\/app\/(posts|tasks|memory|inbox|site|settings|projects)\/?$/);
  return match ? match[1] : "posts";
}
function viewPath(next) {
  return next === "posts" ? "/app/posts" : `/app/${next}`;
}
let view = viewFromPath(location.pathname);
let pendingFiles = [];
let documentPasteBound = false;
let site = {site_name: "loomsci", logo_url: "https://www.loomsci.com/nav-logo.png", links: [], footer: ""};

function showError(message) { errorEl.hidden = !message; errorEl.textContent = message || ""; }
function stateLabel(prefix, value) {
  const key = `${prefix}.${value}`;
  const translated = t(key);
  return translated === key ? value : translated;
}
function esc(value) { return String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function safeUrl(url) { return /^(https?:\/\/|mailto:)/i.test(url) ? url : "#"; }
function inline(text) {
  return text.replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) =>
      `<a href="${esc(safeUrl(url))}" rel="noreferrer noopener">${label}</a>`);
}

function markdown(source) {
  const lines = esc(source).split("\n");
  const out = [];
  let code = false, list = null, para = [], i = 0;
  const flush = () => { if (para.length) { out.push(`<p>${inline(para.join(" "))}</p>`); para = []; } };
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };

  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("```")) {
      flush(); closeList();
      out.push(code ? "</code></pre>" : '<pre><code>');
      code = !code; i++; continue;
    }
    if (code) { out.push(line + "\n"); i++; continue; }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flush(); closeList();
      const level = heading[1].length + 1;
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`); i++; continue;
    }

    if (/^\s*---+\s*$/.test(line)) { flush(); closeList(); out.push("<hr>"); i++; continue; }

    const tableSep = lines[i + 1] || "";
    if (line.trim().startsWith("|") && /^\s*\|?[\s:|-]+\|?\s*$/.test(tableSep) && tableSep.includes("-")) {
      flush(); closeList();
      const cells = (row) => row.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
      const head = cells(line); i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) { rows.push(cells(lines[i])); i++; }
      out.push("<table><thead><tr>" + head.map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead><tbody>");
      for (const row of rows) out.push("<tr>" + row.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>");
      out.push("</tbody></table>"); continue;
    }

    const quote = line.match(/^\s*>\s?(.*)$/);
    if (quote) { flush(); closeList(); out.push(`<blockquote>${inline(quote[1])}</blockquote>`); i++; continue; }

    const ol = line.match(/^\s*\d+\.\s+(.*)$/);
    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    if (ol || ul) {
      flush();
      const kind = ol ? "ol" : "ul";
      if (list !== kind) { closeList(); out.push(`<${kind}>`); list = kind; }
      out.push(`<li>${inline((ol || ul)[1])}</li>`); i++; continue;
    }

    if (!line.trim()) {
      flush();
      let next = i + 1;
      while (next < lines.length && !lines[next].trim()) next++;
      const candidate = lines[next] || "";
      const sameList = list === "ol"
        ? /^\s*\d+[.)]\s+/.test(candidate)
        : list === "ul" ? /^\s*[-*+]\s+/.test(candidate) : false;
      if (!sameList) closeList();
      i++;
      continue;
    }
    para.push(line.trim()); i++;
  }
  flush(); closeList(); if (code) out.push("</code></pre>");
  return out.join("");
}

function renderMath(root) {
  if (window.renderMathInElement) {
    try {
      window.renderMathInElement(root, {
        delimiters: [
          {left: "$$", right: "$$", display: true},
          {left: "$", right: "$", display: false},
        ],
        throwOnError: false,
      });
    } catch { /* keep source */ }
  }
}

function attachmentHtml(item) {
  const src = `/api/v1/attachments/${encodeURIComponent(item.id)}`;
  const type = String(item.content_type || "");
  if (type.startsWith("image/")) return `<img class="attachment-image" src="${src}" alt="${esc(item.filename)}" loading="lazy">`;
  if (type.startsWith("audio/")) return `<audio controls preload="metadata" src="${src}"></audio>`;
  if (type.startsWith("video/")) return `<video controls preload="metadata" src="${src}"></video>`;
  return `<a href="${src}">${esc(item.filename)}</a>`;
}

async function api(path, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  if (opts.body && typeof opts.body !== "string") { opts.body = JSON.stringify(opts.body); opts.headers["Content-Type"] = "application/json"; }
  const response = await fetch("/api/v1/" + path, opts);
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { error: text }; }
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function item(title, meta, body, actions = "", attachments = []) {
  const files = (attachments || []).map((a) => `<div class="attachment">${attachmentHtml(a)}</div>`).join("");
  const heading = title ? `<h3>${esc(title)}</h3>` : "";
  return `<article class="item">${heading}<div class="meta">${esc(meta)}</div><div class="md">${markdown(body || "")}</div>${files}${actions}</article>`;
}

function postItem(post) {
  const summary = post.summary || {};
  const long = Boolean(post.has_more);
  const text = long ? (summary.text || "") : (post.body || "");
  const state = long && summary.status === "pending"
    ? ` · ${t("posts.summaryPending")}`
    : long && summary.status === "failed"
      ? ` · ${t("posts.summaryFailed")}`
      : long && summary.status === "fallback" ? ` · ${t("posts.summaryFallback")}` : "";
  const meta = `#${post.seq} · ${post.author} · ${post.kind}` + state;
  const more = long
    ? `<a class="more" href="?post=${encodeURIComponent(post.id)}">${esc(t("posts.full"))}</a>`
    : "";
  return `<article class="item"><div class="meta">${esc(meta)}</div><div class="md">${markdown(text)}</div>${more}</article>`;
}

async function loadPost(id) {
  const data = await api(`posts/${encodeURIComponent(id)}`);
  const post = data.post;
  const summary = post.summary || {};
  const files = (post.attachments || []).map((a) => `<div class="attachment">${attachmentHtml(a)}</div>`).join("");
  const summaryLabel = summary.status === "fallback" ? t("posts.summaryFallback") : t("posts.summary");
  const summaryBlock = summary.text
    ? `<details class="summary"><summary>${esc(summaryLabel)}</summary><div class="md">${markdown(summary.text)}</div></details>`
    : "";
  app.innerHTML = `<p><a href="/app/posts">← ${esc(t("posts.back"))}</a></p>
    <article class="item"><div class="meta">#${post.seq} · ${esc(post.author)} · ${esc(post.kind)}</div>
    <div class="md">${markdown(post.body || "")}</div>${files}</article>${summaryBlock}`;
  renderMath(app);
}

function renderPending() {
  const target = document.getElementById("pending-files");
  if (!target) return;
  target.innerHTML = pendingFiles.map((file, index) =>
    `<span class="chip">${esc(file.name)} <button type="button" data-remove="${index}" aria-label="${esc(t("common.remove", {name: file.name}))}">×</button></span>`
  ).join("");
  target.querySelectorAll("button[data-remove]").forEach((button) => {
    button.onclick = () => { pendingFiles.splice(Number(button.dataset.remove), 1); renderPending(); };
  });
}

function clipboardImageFiles(event) {
  const data = event.clipboardData;
  if (!data) return [];
  const files = [...(data.files || [])].filter((file) => file.type.startsWith("image/"));
  if (files.length) return files;
  return [...(data.items || [])]
    .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
    .map((item) => item.getAsFile())
    .filter(Boolean);
}

function normalizeFile(file) {
  if (file.name) return file;
  const ext = (file.type.split("/")[1] || "png").replace("+xml", "");
  return new File([file], `pasted-${Date.now()}.${ext}`, {type: file.type || "image/png"});
}

function addFiles(files) {
  for (const file of files || []) if (file && file.size) pendingFiles.push(normalizeFile(file));
  renderPending();
}

async function siteRequest(method = "GET", body = null) {
  const response = await fetch("/api/site", {
    method,
    headers: body ? {"Content-Type": "application/json"} : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || `HTTP ${response.status}`);
  return data.site;
}

function applySite() {
  const name = document.getElementById("brand-name");
  const logo = document.getElementById("brand-logo");
  const links = document.getElementById("site-links");
  const footer = document.getElementById("site-footer");
  if (name) name.textContent = site.site_name || "loomsci";
  if (logo) {
    if (site.logo_url) {
      logo.hidden = false;
      logo.alt = site.site_name || "loomsci";
      logo.onerror = () => { logo.hidden = true; };
      if (logo.getAttribute("src") !== site.logo_url) logo.src = site.logo_url;
    } else {
      logo.hidden = true;
      logo.removeAttribute("src");
    }
  }
  if (links) links.innerHTML = (site.links || []).map((link) => {
    const href = String(link.href || "");
    const safe = href.startsWith("/") ? href : safeUrl(href);
    return `<a href="${esc(safe)}" target="_blank" rel="noreferrer noopener">${esc(link.label)}</a>`;
  }).join("");
  if (footer) footer.textContent = site.footer || "";
}

async function loadSite() {
  try { site = await siteRequest(); }
  catch { /* keep defaults when the shell starts without a saved site */ }
  applySite();
}

async function loadSiteView() {
  const links = (site.links || []).map((link) => `${link.label} | ${link.href}`).join("\n");
  app.innerHTML = `<form class="compose" id="site-form">
    <h2>${esc(t("site.title"))}</h2>
    <label>${esc(t("site.nameLabel"))}<input name="site_name" value="${esc(site.site_name)}" maxlength="80"></label>
    <label>${esc(t("site.logoLabel"))}<input name="logo_url" value="${esc(site.logo_url)}" maxlength="500"></label>
    <label>${esc(t("site.linksLabel"))}<textarea name="links" rows="4">${esc(links)}</textarea></label>
    <label>${esc(t("site.footerLabel"))}<textarea name="footer" rows="2" maxlength="300">${esc(site.footer)}</textarea></label>
    <p id="site-status" class="muted"></p>
    <button type="submit">${esc(t("site.save"))}</button></form>`;
  document.getElementById("site-form").onsubmit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const parsed = [];
    for (const line of String(form.get("links") || "").split("\n")) {
      const index = line.indexOf("|");
      if (index < 0) continue;
      const label = line.slice(0, index).trim();
      const href = line.slice(index + 1).trim();
      if (label && href) parsed.push({label, href});
    }
    try {
      site = await siteRequest("POST", {
        site_name: form.get("site_name") || "loomsci",
        logo_url: form.get("logo_url") || "",
        links: parsed,
        footer: form.get("footer") || "",
      });
      applySite();
      document.getElementById("site-status").textContent = t("site.saved");
    } catch (err) { showError(err.message); }
  };
  renderMath(app);
}

async function refreshHealth() {
  try {
    const health = await api("health");
    statusEl.textContent = t("status.local", {service: health.service, version: health.version});
    return health;
  } catch (err) {
    statusEl.textContent = t("status.unreachable");
    return null;
  }
}

function humanBytes(value) {
  let n = Number(value || 0);
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i ? 1 : 0)} ${units[i]}`;
}

function projectCard(project) {
  const count = (project.entries ?? 0).toLocaleString();
  const bytes = humanBytes(project.bytes);
  return `<a class="project-card" href="?project=${encodeURIComponent(project.code)}">
    <div class="project-title">${esc(project.name)}</div>
    <div class="meta">${esc(project.code)} · ${esc(project.machine_id || "")}</div>
    <div class="project-meta">${count} ${esc(t("projects.entries"))} · ${bytes}</div>
    <div class="project-meta">${esc(project.type || "unknown")} · ${esc(project.review_status || "candidate")}</div>
  </a>`;
}

function timelineHtml(rows) {
  if (!rows.length) return `<p class="muted">—</p>`;
  const max = Math.max(...rows.map((row) => Number(row.entries || 0)), 1);
  return `<div class="timeline">${rows.map((row) => `
    <div class="timeline-row"><span>${esc(row.month || "")}</span>
      <div class="bar"><i style="width:${Math.max(2, Math.round(Number(row.entries || 0) / max * 100))}%"></i></div>
      <b>${Number(row.entries || 0)}</b></div>`).join("")}</div>`;
}

function project_store_eval_fields(ev) {
  return ["problem_clarity", "evidence", "implementation", "output", "application", "commercial", "maintainability"]
    .map((key) => `<span class="chip">${esc(key.replace(/_/g, " "))} ${ev[key] ?? "—"}/5</span>`).join("") +
    `<span class="chip">${esc(ev.status)}</span>`;
}

async function loadProject(code) {
  const [detail, stats] = await Promise.all([
    api(`projects/${encodeURIComponent(code)}`),
    api(`projects/${encodeURIComponent(code)}/stats`),
  ]);
  const project = detail.project;
  const kinds = (stats.kinds || []).map((row) =>
    `<span class="chip">${esc(row.kind)} ${Number(row.entries || 0)} · ${humanBytes(row.bytes)}</span>`).join("");
  const sources = (project.sources || []).map((source) =>
    `<div class="project-row"><b>${esc(source.role)}</b><span>${esc(source.source_state)}</span>
      <code>${esc(source.root_path)}</code>
      <span class="muted">${esc(t("projects.dataAsOf"))} ${esc(source.data_as_of || "—")}</span></div>`).join("");
  const apps = (project.apps || []).map((app) =>
    `<div class="project-row"><b>${esc(app.name)}</b><span>${esc(app.status)}</span>
      <code>${esc(app.url || "")}</code>
      <span class="muted">${esc(app.checked_at || "")}</span>
      <button type="button" data-check-app="${esc(app.name)}">${esc(t("projects.checkApp"))}</button></div>`).join("") || `<p class="muted">—</p>`;
  const schemas = (project.schemas || []).map((schema) => {
    let tables = [];
    try { tables = JSON.parse(schema.tables_json || "[]"); } catch { tables = []; }
    return `<div class="project-row"><b>${esc(schema.engine)}</b><code>${esc(schema.db_path)}</code>
      <span class="muted">${tables.map((table) => `${esc(table.name || "")} ${Number(table.rows || 0).toLocaleString()}`).join(" · ")}</span></div>`;
  }).join("") || `<p class="muted">—</p>`;
  const recent = (stats.recent || []).map((row) =>
    `<div class="project-row"><span class="chip">${esc(row.kind)}</span><code>${esc(row.path)}</code>
      <span class="muted">${humanBytes(row.bytes)} · ${esc(row.mtime || "")}</span></div>`).join("") || `<p class="muted">—</p>`;
  app.innerHTML = `<p><a href="/app/projects">← ${esc(t("projects.back"))}</a></p>
    <h2>${esc(project.name)}</h2>
    <div class="meta">${esc(project.code)} · ${esc(t("projects.machine"))}: ${esc(project.machine_id || "")} · ${esc(project.type)}</div>
    <div class="project-section"><h3>${esc(t("projects.review"))}</h3>
      <div class="chips"><span class="chip">${esc(project.review_status || "candidate")}</span>
      <span class="chip">${esc(t("projects.completeness"))} ${project.completeness ?? "—"}/5</span>
      <span class="chip">${esc(t("projects.maturity"))} ${project.maturity ?? "—"}/5</span>
      <span class="chip">${esc(t("projects.commercial"))} ${project.commercial_potential ?? "—"}/5</span></div>
      ${project.direction ? `<p>${esc(project.direction)}</p>` : ""}
      ${project.review_notes ? `<p class="meta">${esc(project.review_notes)}</p>` : ""}
    </div>
    <div class="project-section"><h3>${esc(t("projects.evaluation"))}</h3>
      ${(project.evaluations && project.evaluations.length) ? (() => {
        const ev = project.evaluations[0];
        return `<div class="chips">${project_store_eval_fields(ev)}</div>${ev.rationale ? `<p>${esc(ev.rationale)}</p>` : ""}`;
      })() : `<p class="muted">—</p>`}
    </div>
    <div class="project-section"><h3>${esc(t("projects.kinds"))}</h3><div class="chips">${kinds || "—"}</div></div>
    <div class="project-section"><h3>${esc(t("projects.sources"))}</h3>${sources}</div>
    <div class="project-section"><h3>${esc(t("projects.apps"))}</h3>${apps}</div>
    <div class="project-section"><h3>${esc(t("projects.schemas"))}</h3>${schemas}</div>
    <div class="project-section"><h3>${esc(t("projects.timeline"))}</h3>${timelineHtml(stats.timeline || [])}</div>
    <div class="project-section"><h3>${esc(t("projects.recent"))}</h3>${recent}</div>`;
  app.querySelectorAll('button[data-check-app]').forEach((button) => {
    button.onclick = async () => {
      try {
        await api(`projects/${encodeURIComponent(project.code)}/apps/${encodeURIComponent(button.dataset.checkApp)}/check`, {method: "POST", body: {}});
        await loadProject(project.code);
      } catch (err) { showError(err.message); }
    };
  });
  renderMath(app);
}

async function loadProjects() {
  const code = new URLSearchParams(location.search).get("project");
  if (code) return loadProject(code);
  const data = await api("projects");
  const projects = (data.projects || []).map((project) => projectCard(project)).join("");
  app.innerHTML = `<h2>${esc(t("nav.projects"))}</h2>` +
    (projects ? `<div class="project-grid">${projects}</div>` : `<p class="muted">${esc(t("projects.empty"))}</p>`);
}

async function loadPosts() {
  const postId = new URLSearchParams(location.search).get("post");
  if (postId) return loadPost(postId);
  const status = await api("status");
  const since = Math.max(0, Number(status.last_seq || 0) - 100);
  const data = await api(`posts?since=${since}&limit=100&view=feed`);
  pendingFiles = [];
  const form = `<form class="compose" id="post-form">
    <textarea name="body" placeholder="${esc(t("posts.bodyPlaceholder"))}" required></textarea>
    <input type="file" name="file" multiple>
    <button type="button" id="paste-image">${esc(t("posts.pasteImage"))}</button>
    <div id="pending-files" class="pending"></div>
    <button type="submit">${esc(t("posts.post"))}</button></form>
    <form class="compose" id="search-form"><input name="q" placeholder="${esc(t("posts.searchPlaceholder"))}"><button type="submit">${esc(t("posts.search"))}</button></form>`;
  const posts = (data.posts || []).slice().reverse().map(postItem).join("");
  app.innerHTML = form + (posts || `<p class="muted">${esc(t("posts.empty"))}</p>`);
  const fileInput = document.querySelector('#post-form input[type="file"]');
  fileInput.onchange = () => addFiles(fileInput.files);
  document.getElementById("paste-image").onclick = async () => {
    showError("");
    if (!navigator.clipboard?.read) {
      showError(t("posts.clipboardUnsupported"));
      return;
    }
    try {
      const items = await navigator.clipboard.read();
      const files = [];
      for (const item of items) {
        const type = item.types.find((value) => value.startsWith("image/"));
        if (type) files.push(new File([await item.getType(type)], `clipboard-${Date.now()}.${type.split("/")[1] || "png"}`, {type}));
      }
      if (files.length) addFiles(files);
      else showError(t("posts.clipboardEmpty"));
    } catch (err) {
      showError(t("posts.clipboardFailed", {error: err.message}));
    }
  };
  const bodyInput = document.querySelector('#post-form textarea[name="body"]');
  if (!documentPasteBound) {
  documentPasteBound = true;
  document.addEventListener("paste", (event) => {
    if (view !== "posts" || !document.getElementById("post-form")) return;
    const files = clipboardImageFiles(event);
    if (files.length) {
      event.preventDefault();
      addFiles(files);
      return;
    }
    const types = [...(event.clipboardData?.types || [])];
    if (types.includes("Files") || types.some((type) => type.startsWith("image/"))) {
      showError(t("posts.clipboardNoFile"));
    }
  });
  }
  bodyInput.addEventListener("dragover", (event) => {
    if ([...(event.dataTransfer?.items || [])].some((item) => item.kind === "file" && item.type.startsWith("image/"))) {
      event.preventDefault();
    }
  });
  bodyInput.addEventListener("drop", (event) => {
    const files = [...(event.dataTransfer?.files || [])].filter((file) => file.type.startsWith("image/"));
    if (files.length) { event.preventDefault(); addFiles(files); }
  });
  document.getElementById("post-form").onsubmit = async (event) => {
    event.preventDefault(); showError("");
    const formData = new FormData(event.target);
    try {
      const attachments = [];
      for (const file of pendingFiles) {
        const base64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
          reader.onerror = reject;
          reader.readAsDataURL(file);
        });
        const uploaded = await api("attachments", {method: "POST", body: {
          filename: file.name, content_type: file.type || "application/octet-stream", content_base64: base64,
        }});
        attachments.push(uploaded.attachment.id);
      }
      await api("posts", {method: "POST", body: {
        body: String(formData.get("body") || ""), attachments,
      }});
      await loadPosts();
    } catch (err) { showError(err.message); }
  };
  document.getElementById("search-form").onsubmit = async (event) => {
    event.preventDefault();
    const q = new FormData(event.target).get("q") || "";
    if (!q.trim()) return loadPosts();
    try {
      const result = await api(`search?q=${encodeURIComponent(q)}&limit=50`);
      app.innerHTML = `<p class="muted">${esc(t("posts.results", {query: q}))}</p>` + ((result.results || []).map((r) =>
        item(r.title, `${r.type} · ${r.id}`, r.snippet || "")).join("") || `<p class="muted">${esc(t("posts.noResults"))}</p>`);
      renderMath(app);
    } catch (err) { showError(err.message); }
  };
  renderMath(app);
}

async function loadTasks() {
  const data = await api("tasks?limit=100");
  const form = `<form class="compose" id="task-form">
    <input name="title" placeholder="${esc(t("tasks.titlePlaceholder"))}" required maxlength="200">
    <textarea name="acceptance" placeholder="${esc(t("tasks.acceptancePlaceholder"))}"></textarea>
    <button type="submit">${esc(t("tasks.add"))}</button></form>`;
  const tasks = (data.tasks || []).map((task) => {
    const actions = `<div class="actions"><form data-task="${esc(task.id)}" data-action="claim"><button>${esc(t("tasks.claim"))}</button></form>
      <form data-task="${esc(task.id)}" data-action="done"><input name="evidence" placeholder="${esc(t("tasks.evidencePlaceholder"))}" required><button>${esc(t("tasks.done"))}</button></form></div>`;
    const owner = task.assigned_to || t("tasks.unassigned");
    return item(task.title || task.id, `${stateLabel("tasks.status", task.status)} · ${owner}`, task.acceptance || "", actions);
  }).join("");
  app.innerHTML = form + (tasks || `<p class="muted">${esc(t("tasks.empty"))}</p>`);
  document.getElementById("task-form").onsubmit = async (event) => {
    event.preventDefault(); const formData = new FormData(event.target);
    try { await api("tasks", {method: "POST", body: {title: formData.get("title") || "", acceptance: formData.get("acceptance") || ""}}); await loadTasks(); }
    catch (err) { showError(err.message); }
  };
  app.querySelectorAll("form[data-task]").forEach((form) => {
    form.onsubmit = async (event) => {
      event.preventDefault();
      try {
        if (form.dataset.action === "claim") await api(`tasks/${form.dataset.task}/claim`, {method: "POST", body: {}});
        else await api(`tasks/${form.dataset.task}/done`, {method: "POST", body: {evidence: new FormData(form).get("evidence") || ""}});
        await loadTasks();
      } catch (err) { showError(err.message); }
    };
  });
  renderMath(app);
}

async function loadMemory() {
  const data = await api("memory?limit=100");
  const form = `<form class="compose" id="fact-form">
    <input name="claim" placeholder="${esc(t("memory.claimPlaceholder"))}" required maxlength="500">
    <input name="source" placeholder="${esc(t("memory.sourcePlaceholder"))}">
    <textarea name="evidence" placeholder="${esc(t("memory.evidencePlaceholder"))}"></textarea>
    <button type="submit">${esc(t("memory.add"))}</button></form>`;
  const facts = (data.facts || []).map((fact) => {
    const actions = `<div class="actions"><button data-fact="${esc(fact.id)}" data-status="approved">${esc(t("memory.approve"))}</button><button data-fact="${esc(fact.id)}" data-status="rejected">${esc(t("memory.reject"))}</button></div>`;
    return item(fact.claim, `${stateLabel("memory.status", fact.status)} · ${fact.source || t("memory.noSource")}`, fact.evidence || "", actions);
  }).join("");
  app.innerHTML = form + (facts || `<p class="muted">${esc(t("memory.empty"))}</p>`);
  document.getElementById("fact-form").onsubmit = async (event) => {
    event.preventDefault(); const formData = new FormData(event.target);
    try { await api("memory", {method: "POST", body: {claim: formData.get("claim") || "", source: formData.get("source") || "", evidence: formData.get("evidence") || ""}}); await loadMemory(); }
    catch (err) { showError(err.message); }
  };
  app.querySelectorAll("button[data-fact]").forEach((button) => {
    button.onclick = async () => {
      try { await api(`memory/${button.dataset.fact}/review`, {method: "POST", body: {status: button.dataset.status}}); await loadMemory(); }
      catch (err) { showError(err.message); }
    };
  });
  renderMath(app);
}

async function loadInbox() {
  const data = await api("inbox?limit=100");
  const posts = (data.inbox || []).map((post) =>
    item("", `#${post.seq} · ${post.author} · ${post.mention_read_at ? t("inbox.read") : t("inbox.unread")}`, post.body,
      `<div class="actions"><button data-post="${esc(post.id)}">${esc(t("inbox.markRead"))}</button></div>`)
  ).join("");
  app.innerHTML = posts || `<p class="muted">${esc(t("inbox.empty"))}</p>`;
  app.querySelectorAll("button[data-post]").forEach((button) => {
    button.onclick = async () => {
      try { await api("inbox/read", {method: "POST", body: {post_id: button.dataset.post}}); await loadInbox(); }
      catch (err) { showError(err.message); }
    };
  });
  renderMath(app);
}

async function loadAdvancedProvider() {
  const select = document.getElementById("advanced-provider");
  const base = document.getElementById("advanced-base");
  const model = document.getElementById("advanced-model");
  const key = document.getElementById("advanced-key");
  const status = document.getElementById("advanced-status");
  if (!select || !base || !model || !key || !status) return;
  const provider = select.value;
  try {
    const data = await api(`settings/llm/${encodeURIComponent(provider)}`);
    const p = data.provider || {};
    base.value = p.base_url || "";
    model.value = p.model || "";
    key.value = "";
    key.placeholder = p.configured ? t("settings.keepKey") : t("settings.notConfigured");
    status.textContent = p.configured ? t("settings.configured") : t("settings.notConfigured");
  } catch (err) { status.textContent = err.message; }
}

async function loadUpdateStatus() {
  const statusEl = document.getElementById("update-status");
  const actions = document.getElementById("update-actions");
  if (!statusEl || !actions) return;
  try {
    const data = await api("update/status");
    const latest = data.latest || {};
    const downloaded = data.downloaded;
    statusEl.textContent = data.available
      ? t("settings.updateAvailable", {current: data.current, latest: latest.version})
      : t("settings.updateCurrent", {current: data.current});
    actions.innerHTML = `<button type="button" id="check-update">${esc(t("settings.checkUpdate"))}</button>` +
      (data.available ? `<button type="button" id="download-update">${esc(t("settings.downloadUpdate"))}</button>` : "") +
      (downloaded ? `<button type="button" id="install-update">${esc(t("settings.installUpdate"))}</button>` : "");
    document.getElementById("check-update").onclick = async () => {
      statusEl.textContent = t("settings.updateChecking");
      try { await api("update/check", {method: "POST", body: {}}); await loadUpdateStatus(); }
      catch (err) { statusEl.textContent = err.message; }
    };
    const download = document.getElementById("download-update");
    if (download) download.onclick = async () => {
      statusEl.textContent = t("settings.updateDownloading");
      try { await api("update/download", {method: "POST", body: {}}); await loadUpdateStatus(); }
      catch (err) { statusEl.textContent = err.message; }
    };
    const install = document.getElementById("install-update");
    if (install) install.onclick = async () => {
      if (!confirm(t("settings.confirmInstall"))) return;
      statusEl.textContent = t("settings.updateRestarting");
      try { await api("update/apply", {method: "POST", body: {}}); }
      catch (err) { statusEl.textContent = err.message; return; }
      setTimeout(() => location.reload(), 8000);
    };
  } catch (err) { statusEl.textContent = err.message; }
}

async function loadSettings() {
  const data = await api("settings/llm/deepseek");
  const provider = data.provider;
  const configured = Boolean(provider.configured);
  app.innerHTML = `<section class="settings">
    <h2>${esc(t("settings.provider"))}</h2>
    <article class="item">
      <h3>${esc(provider.label)}</h3>
      <div class="meta">${configured ? esc(t("settings.configured")) : esc(t("settings.notConfigured"))}</div>
      <form class="compose" id="key-form">
        <label>${esc(t("settings.keyLabel"))}
          <input type="password" name="api_key" autocomplete="off" spellcheck="false"
            placeholder="${configured ? esc(t("settings.keepKey")) : "sk-..."}">
        </label>
        <button type="submit">${esc(t("settings.save"))}</button>
        ${configured ? `<button type="button" id="clear-key">${esc(t("settings.clear"))}</button>` : ""}
        <button type="button" id="test-key">${esc(t("settings.test"))}</button>
      </form>
      <p class="meta" id="settings-status"></p>
    </article>
    <h2>${esc(t("settings.advancedProviders"))}</h2>
    <article class="item">
      <div class="compose">
        <label>${esc(t("settings.provider"))}
          <select id="advanced-provider">
            <option value="aliyun">Alibaba DashScope</option>
            <option value="volcengine">Volcengine Ark</option>
          </select>
        </label>
        <label>${esc(t("settings.baseUrl"))}<input id="advanced-base" autocomplete="off"></label>
        <label>${esc(t("settings.model"))}<input id="advanced-model" autocomplete="off"></label>
        <label>${esc(t("settings.keyLabel"))}<input id="advanced-key" type="password" autocomplete="off"></label>
        <div class="actions"><button type="button" id="advanced-save">${esc(t("settings.save"))}</button>
          <button type="button" id="advanced-test">${esc(t("settings.test"))}</button></div>
        <p class="meta" id="advanced-status"></p>
      </div>
    </article>
    <h2>${esc(t("settings.updates"))}</h2>
    <article class="item">
      <div class="meta" id="update-status">${esc(t("settings.updateLoading"))}</div>
      <div class="actions" id="update-actions"></div>
    </article>
  </section>`;
  const form = document.getElementById("key-form");
  const status = document.getElementById("settings-status");
  form.onsubmit = async (event) => {
    event.preventDefault();
    const key = String(new FormData(form).get("api_key") || "").trim();
    if (!key) { status.textContent = t("settings.enterKey"); return; }
    try {
      await api("settings/llm/deepseek/key", {method: "PUT", body: {api_key: key}});
      await loadSettings();
    } catch (err) { status.textContent = err.message; }
  };
  document.getElementById("test-key").onclick = async () => {
    status.textContent = t("settings.testing");
    try {
      const result = await api("settings/llm/deepseek/test", {method: "POST", body: {}});
      status.textContent = result.ok
        ? t("settings.testOk", {ms: result.latency_ms})
        : t("settings.testFailed", {error: result.error});
    } catch (err) { status.textContent = err.message; }
  };
  await loadUpdateStatus();
  const advancedSelect = document.getElementById("advanced-provider");
  if (advancedSelect) {
    advancedSelect.onchange = loadAdvancedProvider;
    await loadAdvancedProvider();
    document.getElementById("advanced-save").onclick = async () => {
      const provider = advancedSelect.value;
      const status = document.getElementById("advanced-status");
      try {
        await api(`settings/llm/${encodeURIComponent(provider)}`, {method: "PUT", body: {
          base_url: document.getElementById("advanced-base").value,
          model: document.getElementById("advanced-model").value,
        }});
        const value = document.getElementById("advanced-key").value.trim();
        if (value) await api(`settings/llm/${encodeURIComponent(provider)}/key`, {method: "PUT", body: {api_key: value}});
        await loadAdvancedProvider();
      } catch (err) { status.textContent = err.message; }
    };
    document.getElementById("advanced-test").onclick = async () => {
      const provider = advancedSelect.value;
      const status = document.getElementById("advanced-status");
      status.textContent = t("settings.testing");
      try {
        const result = await api(`settings/llm/${encodeURIComponent(provider)}/test`, {method: "POST", body: {}});
        status.textContent = result.ok ? t("settings.testOk", {ms: result.latency_ms}) : t("settings.testFailed", {error: result.error});
      } catch (err) { status.textContent = err.message; }
    };
  }
  const clear = document.getElementById("clear-key");
  if (clear) clear.onclick = async () => {
    if (!confirm(t("settings.confirmClear"))) return;
    try {
      await api("settings/llm/deepseek/key", {method: "PUT", body: {api_key: ""}});
      await loadSettings();
    } catch (err) { status.textContent = err.message; }
  };
}

const views = {projects: loadProjects, posts: loadPosts, tasks: loadTasks, memory: loadMemory, inbox: loadInbox, site: loadSiteView, settings: loadSettings};

async function render(next = view) {
  view = next; showError("");
  document.querySelectorAll("nav button").forEach((button) => { button.disabled = button.dataset.view === view; });
  try { await views[view](); } catch (err) { app.innerHTML = ""; showError(err.message); }
}

document.querySelectorAll("nav button").forEach((button) => {
  button.onclick = () => {
    history.pushState({view: button.dataset.view}, "", viewPath(button.dataset.view));
    render(button.dataset.view);
  };
});
window.addEventListener("popstate", () => render(viewFromPath(location.pathname)));
const localeSelect = document.getElementById("locale");
if (localeSelect) {
  localeSelect.onchange = () => {
    window.LS_I18N.setLocale(localeSelect.value);
    applySite();
    refreshHealth();
    render();
  };
}
(async () => {
  window.LS_I18N.applyStatic();
  statusEl.textContent = t("status.connecting");
  await loadSite();
  await refreshHealth();
  render(view);
})();
