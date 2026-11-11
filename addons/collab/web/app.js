const roomsEl = document.getElementById("rooms");
const postsEl = document.getElementById("posts");
const titleEl = document.getElementById("room-title");
const membersEl = document.getElementById("members");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
const postForm = document.getElementById("post-form");
let current = null;

function showError(message) { errorEl.hidden = !message; errorEl.textContent = message || ""; }
function esc(value) { return String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function safeUrl(url) { return /^https?:\/\//i.test(url) ? url : "#"; }
function inline(text) {
  return text.replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, l, u) => `<a href="${esc(safeUrl(u))}" rel="noreferrer noopener">${l}</a>`);
}
function markdown(source) {
  const lines = esc(source).split("\n"); const out = []; let code = false, list = null, para = [];
  const flush = () => { if (para.length) { out.push(`<p>${inline(para.join(" "))}</p>`); para = []; } };
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const line of lines) {
    if (line.startsWith("```")) { flush(); closeList(); out.push(code ? "</code></pre>" : "<pre><code>"); code = !code; continue; }
    if (code) { out.push(line + "\n"); continue; }
    const h = line.match(/^(#{1,3})\s+(.+)$/);
    if (h) { flush(); closeList(); const n = h[1].length + 1; out.push(`<h${n}>${inline(h[2])}</h${n}>`); continue; }
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const ul = line.match(/^\s*[-*+]\s+(.*)$/);
    if (ol || ul) {
      flush();
      const kind = ol ? "ol" : "ul";
      if (list !== kind) { closeList(); out.push(`<${kind}>`); list = kind; }
      out.push(`<li>${inline((ol || ul)[1])}</li>`);
      continue;
    }
    if (!line.trim()) { flush(); closeList(); continue; }
    para.push(line.trim());
  }
  flush(); closeList(); if (code) out.push("</code></pre>");
  return out.join("");
}
async function api(path, options = {}) {
  const opts = {...options, headers: {...(options.headers || {})}};
  if (opts.body && typeof opts.body !== "string") { opts.body = JSON.stringify(opts.body); opts.headers["Content-Type"] = "application/json"; }
  const res = await fetch("/api/" + path, opts);
  const text = await res.text(); let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = {error: text}; }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}
async function loadRooms() {
  const data = await api("rooms");
  roomsEl.innerHTML = "";
  for (const room of data.rooms || []) {
    const el = document.createElement("div");
    el.className = "room" + (current === room.id ? " active" : "");
    el.innerHTML = `<b>${esc(room.name)}</b><span class="muted">${room.members || 0} members</span>`;
    el.onclick = () => selectRoom(room.id);
    roomsEl.appendChild(el);
  }
  if (!current && data.rooms?.length) selectRoom(data.rooms[0].id);
}
async function selectRoom(id) {
  current = id; showError(""); postForm.hidden = false;
  const info = await api(`rooms/${id}`);
  titleEl.textContent = info.room.name;
  membersEl.textContent = (info.members || []).map((m) => `${m.agent} (${m.role})`).join(" · ");
  const data = await api(`rooms/${id}/posts`);
  postsEl.innerHTML = (data.posts || []).map((post) =>
    `<article class="item"><div class="muted">#${post.seq} · ${esc(post.author)} · ${esc(post.kind)}</div><div class="md">${markdown(post.body || "")}</div></article>`
  ).join("") || '<p class="muted">No messages yet.</p>';
  document.querySelectorAll(".room").forEach((el) => el.classList.remove("active"));
  loadRooms();
}
document.getElementById("room-form").onsubmit = async (e) => {
  e.preventDefault(); const f = new FormData(e.target);
  try { const result = await api("rooms", {method: "POST", body: {name: f.get("name")}}); e.target.reset(); current = result.room.id; await loadRooms(); await selectRoom(result.room.id); }
  catch (err) { showError(err.message); }
};
postForm.onsubmit = async (e) => {
  e.preventDefault(); if (!current) return; const f = new FormData(e.target);
  try { await api(`rooms/${current}/posts`, {method: "POST", body: {body: f.get("body")}}); e.target.reset(); await selectRoom(current); }
  catch (err) { showError(err.message); }
};
(async () => {
  try { const h = await api("health"); statusEl.textContent = "core " + h.version; } catch {}
  try { await loadRooms(); } catch (err) { showError(err.message); }
})();
