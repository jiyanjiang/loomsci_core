const app = document.getElementById("app");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
let view = "posts";

function showError(message) {
  errorEl.hidden = !message;
  errorEl.textContent = message || "";
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function safeUrl(url) {
  return /^https?:\/\//i.test(url) ? url : "#";
}

function inline(text) {
  return text
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) =>
      `<a href="${esc(safeUrl(url))}" rel="noreferrer noopener">${label}</a>`);
}

function markdown(source) {
  const lines = esc(source).split("\n");
  const html = [];
  let code = false;
  let list = false;
  let para = [];
  const flush = () => {
    if (para.length) { html.push(`<p>${inline(para.join(" "))}</p>`); para = []; }
  };
  for (const line of lines) {
    if (line.startsWith("```")) {
      flush();
      if (list) { html.push("</ul>"); list = false; }
      html.push(code ? "</code></pre>" : "<pre><code>");
      code = !code;
      continue;
    }
    if (code) { html.push(line + "\n"); continue; }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flush();
      if (list) { html.push("</ul>"); list = false; }
      const level = heading[1].length + 1;
      html.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      flush();
      if (!list) { html.push("<ul>"); list = true; }
      html.push(`<li>${inline(line.replace(/^\s*[-*]\s+/, ""))}</li>`);
      continue;
    }
    if (!line.trim()) {
      flush();
      if (list) { html.push("</ul>"); list = false; }
      continue;
    }
    para.push(line.trim());
  }
  flush();
  if (list) html.push("</ul>");
  if (code) html.push("</code></pre>");
  return html.join("");
}

async function api(path, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  if (opts.body && typeof opts.body !== "string") {
    opts.body = JSON.stringify(opts.body);
    opts.headers["Content-Type"] = "application/json";
  }
  const response = await fetch("/api/v1/" + path, opts);
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { error: text }; }
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function item(title, meta, body, actions = "") {
  return `<article class="item"><h3>${esc(title)}</h3><div class="meta">${esc(meta)}</div><div class="md">${markdown(body || "")}</div>${actions}</article>`;
}

async function loadPosts() {
  const data = await api("posts?limit=100");
  const form = `<form class="compose" id="post-form">
    <input name="title" placeholder="Title" maxlength="200">
    <textarea name="body" placeholder="Markdown body" required></textarea>
    <button type="submit">Post</button></form>`;
  const posts = (data.posts || []).slice().reverse().map((post) => {
    const files = (post.attachments || []).map((a) =>
      `<a href="/api/v1/attachments/${esc(a.id)}">${esc(a.filename)}</a>`).join(" · ");
    return item(post.title || post.id, `#${post.seq} · ${post.author} · ${post.kind}`, post.body)
      + (files ? `<div class="meta">${files}</div>` : "");
  }).join("");
  app.innerHTML = form + (posts || '<p class="muted">No posts yet.</p>');
  document.getElementById("post-form").onsubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    try { await api("posts", { method: "POST", body: { title: formData.get("title") || "", body: formData.get("body") || "" } }); await loadPosts(); }
    catch (err) { showError(err.message); }
  };
}

async function loadTasks() {
  const data = await api("tasks?limit=100");
  const form = `<form class="compose" id="task-form">
    <input name="title" placeholder="Task title" required maxlength="200">
    <textarea name="acceptance" placeholder="Acceptance criteria"></textarea>
    <button type="submit">Add task</button></form>`;
  const tasks = (data.tasks || []).map((task) => {
    let actions = `<div class="actions"><form data-task="${esc(task.id)}" data-action="claim"><button>Claim</button></form>`;
    actions += `<form data-task="${esc(task.id)}" data-action="done"><input name="evidence" placeholder="Evidence" required><button>Done</button></form></div>`;
    return item(task.title || task.id, `${task.status} · ${task.assigned_to || "unassigned"}`, task.acceptance || "", actions);
  }).join("");
  app.innerHTML = form + (tasks || '<p class="muted">No tasks yet.</p>');
  document.getElementById("task-form").onsubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    try { await api("tasks", { method: "POST", body: { title: formData.get("title") || "", acceptance: formData.get("acceptance") || "" } }); await loadTasks(); }
    catch (err) { showError(err.message); }
  };
  app.querySelectorAll("form[data-task]").forEach((form) => {
    form.onsubmit = async (event) => {
      event.preventDefault();
      const id = form.dataset.task;
      const action = form.dataset.action;
      try {
        if (action === "claim") await api(`tasks/${id}/claim`, { method: "POST", body: {} });
        else await api(`tasks/${id}/done`, { method: "POST", body: { evidence: new FormData(form).get("evidence") || "" } });
        await loadTasks();
      } catch (err) { showError(err.message); }
    };
  });
}

async function loadMemory() {
  const data = await api("memory?limit=100");
  const form = `<form class="compose" id="fact-form">
    <input name="claim" placeholder="Fact / claim" required maxlength="500">
    <input name="source" placeholder="Source">
    <textarea name="evidence" placeholder="Evidence"></textarea>
    <button type="submit">Add candidate fact</button></form>`;
  const facts = (data.facts || []).map((fact) => {
    const actions = `<div class="actions">
      <button data-fact="${esc(fact.id)}" data-status="approved">Approve</button>
      <button data-fact="${esc(fact.id)}" data-status="rejected">Reject</button></div>`;
    return item(fact.claim, `${fact.status} · ${fact.source || "no source"}`, fact.evidence || "", actions);
  }).join("");
  app.innerHTML = form + (facts || '<p class="muted">No facts yet.</p>');
  document.getElementById("fact-form").onsubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    try { await api("memory", { method: "POST", body: { claim: formData.get("claim") || "", source: formData.get("source") || "", evidence: formData.get("evidence") || "" } }); await loadMemory(); }
    catch (err) { showError(err.message); }
  };
  app.querySelectorAll("button[data-fact]").forEach((button) => {
    button.onclick = async () => {
      try { await api(`memory/${button.dataset.fact}/review`, { method: "POST", body: { status: button.dataset.status } }); await loadMemory(); }
      catch (err) { showError(err.message); }
    };
  });
}

async function loadInbox() {
  const data = await api("inbox?limit=100");
  const posts = (data.inbox || []).map((post) => {
    const actions = `<div class="actions"><button data-post="${esc(post.id)}">Mark read</button></div>`;
    return item(post.title || post.id, `#${post.seq} · ${post.author} · ${post.mention_read_at ? "read" : "unread"}`, post.body, actions);
  }).join("");
  app.innerHTML = posts || '<p class="muted">No mentions.</p>';
  app.querySelectorAll("button[data-post]").forEach((button) => {
    button.onclick = async () => {
      try { await api("inbox/read", { method: "POST", body: { post_id: button.dataset.post } }); await loadInbox(); }
      catch (err) { showError(err.message); }
    };
  });
}

const views = { posts: loadPosts, tasks: loadTasks, memory: loadMemory, inbox: loadInbox };

async function render(next = view) {
  view = next;
  showError("");
  document.querySelectorAll("nav button").forEach((button) => {
    button.disabled = button.dataset.view === view;
  });
  try { await views[view](); }
  catch (err) { app.innerHTML = ""; showError(err.message); }
}

document.querySelectorAll("nav button").forEach((button) => {
  button.onclick = () => render(button.dataset.view);
});

(async () => {
  try {
    const health = await api("health");
    statusEl.textContent = `${health.service} ${health.version} · local`;
  } catch (err) {
    statusEl.textContent = "core unreachable";
    showError(err.message);
  }
  render();
})();
