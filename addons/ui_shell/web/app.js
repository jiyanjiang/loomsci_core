const app = document.getElementById("app");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
let view = "posts";

function showError(message) { errorEl.hidden = !message; errorEl.textContent = message || ""; }
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

    if (!line.trim()) { flush(); closeList(); i++; continue; }
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
  return `<article class="item"><h3>${esc(title)}</h3><div class="meta">${esc(meta)}</div><div class="md">${markdown(body || "")}</div>${files}${actions}</article>`;
}

async function loadPosts() {
  const status = await api("status");
  const since = Math.max(0, Number(status.last_seq || 0) - 100);
  const data = await api(`posts?since=${since}&limit=100`);
  const form = `<form class="compose" id="post-form">
    <input name="title" placeholder="Title" maxlength="200">
    <textarea name="body" placeholder="Markdown + $LaTeX$ body" required></textarea>
    <input type="file" name="file">
    <button type="submit">Post</button></form>
    <form class="compose" id="search-form"><input name="q" placeholder="Search posts, tasks, facts"><button type="submit">Search</button></form>`;
  const posts = (data.posts || []).slice().reverse().map((post) =>
    item(post.title || post.id, `#${post.seq} · ${post.author} · ${post.kind}`, post.body, "", post.attachments)
  ).join("");
  app.innerHTML = form + (posts || '<p class="muted">No posts yet.</p>');
  document.getElementById("post-form").onsubmit = async (event) => {
    event.preventDefault(); showError("");
    const formData = new FormData(event.target);
    try {
      let attachments = [];
      const file = formData.get("file");
      if (file && file.size) {
        const base64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
          reader.onerror = reject;
          reader.readAsDataURL(file);
        });
        const uploaded = await api("attachments", {method: "POST", body: {
          filename: file.name, content_type: file.type || "application/octet-stream", content_base64: base64,
        }});
        attachments = [uploaded.attachment.id];
      }
      await api("posts", {method: "POST", body: {
        title: formData.get("title") || "", body: formData.get("body") || "", attachments,
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
      app.innerHTML = `<p class="muted">Results for ${esc(q)}</p>` + ((result.results || []).map((r) =>
        item(r.title, `${r.type} · ${r.id}`, r.snippet || "")).join("") || '<p class="muted">No results.</p>');
      renderMath(app);
    } catch (err) { showError(err.message); }
  };
  renderMath(app);
}

async function loadTasks() {
  const data = await api("tasks?limit=100");
  const form = `<form class="compose" id="task-form">
    <input name="title" placeholder="Task title" required maxlength="200">
    <textarea name="acceptance" placeholder="Acceptance criteria"></textarea>
    <button type="submit">Add task</button></form>`;
  const tasks = (data.tasks || []).map((task) => {
    const actions = `<div class="actions"><form data-task="${esc(task.id)}" data-action="claim"><button>Claim</button></form>
      <form data-task="${esc(task.id)}" data-action="done"><input name="evidence" placeholder="Evidence" required><button>Done</button></form></div>`;
    return item(task.title || task.id, `${task.status} · ${task.assigned_to || "unassigned"}`, task.acceptance || "", actions);
  }).join("");
  app.innerHTML = form + (tasks || '<p class="muted">No tasks yet.</p>');
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
    <input name="claim" placeholder="Fact / claim" required maxlength="500">
    <input name="source" placeholder="Source">
    <textarea name="evidence" placeholder="Evidence"></textarea>
    <button type="submit">Add candidate fact</button></form>`;
  const facts = (data.facts || []).map((fact) => {
    const actions = `<div class="actions"><button data-fact="${esc(fact.id)}" data-status="approved">Approve</button><button data-fact="${esc(fact.id)}" data-status="rejected">Reject</button></div>`;
    return item(fact.claim, `${fact.status} · ${fact.source || "no source"}`, fact.evidence || "", actions);
  }).join("");
  app.innerHTML = form + (facts || '<p class="muted">No facts yet.</p>');
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
    item(post.title || post.id, `#${post.seq} · ${post.author} · ${post.mention_read_at ? "read" : "unread"}`, post.body,
      `<div class="actions"><button data-post="${esc(post.id)}">Mark read</button></div>`)
  ).join("");
  app.innerHTML = posts || '<p class="muted">No mentions.</p>';
  app.querySelectorAll("button[data-post]").forEach((button) => {
    button.onclick = async () => {
      try { await api("inbox/read", {method: "POST", body: {post_id: button.dataset.post}}); await loadInbox(); }
      catch (err) { showError(err.message); }
    };
  });
  renderMath(app);
}

const views = {posts: loadPosts, tasks: loadTasks, memory: loadMemory, inbox: loadInbox};

async function render(next = view) {
  view = next; showError("");
  document.querySelectorAll("nav button").forEach((button) => { button.disabled = button.dataset.view === view; });
  try { await views[view](); } catch (err) { app.innerHTML = ""; showError(err.message); }
}

document.querySelectorAll("nav button").forEach((button) => { button.onclick = () => render(button.dataset.view); });
(async () => {
  try { const health = await api("health"); statusEl.textContent = `${health.service} ${health.version} · local`; }
  catch (err) { statusEl.textContent = "core unreachable"; showError(err.message); }
  render();
})();
