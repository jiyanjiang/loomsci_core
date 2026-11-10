const $ = (id) => document.getElementById(id);
function showError(message) { $("error").hidden = !message; $("error").textContent = message || ""; }
function esc(value) { return String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function inline(text) {
  return text.replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}
function markdown(source) {
  const out = []; let list = false, para = [];
  const flush = () => { if (para.length) { out.push(`<p>${inline(para.join(" "))}</p>`); para = []; } };
  for (const line of esc(source).split("\n")) {
    const h = line.match(/^(#{1,3})\s+(.+)$/);
    if (h) { flush(); if (list) { out.push("</ul>"); list = false; } const n = h[1].length + 1; out.push(`<h${n}>${inline(h[2])}</h${n}>`); continue; }
    if (/^\s*-\s+/.test(line)) { flush(); if (!list) { out.push("<ul>"); list = true; } out.push(`<li>${inline(line.replace(/^\s*-\s+/, ""))}</li>`); continue; }
    if (!line.trim()) { flush(); if (list) { out.push("</ul>"); list = false; } continue; }
    para.push(line.trim());
  }
  flush(); if (list) out.push("</ul>");
  return out.join("");
}
async function get(path) {
  const res = await fetch("/api/" + path);
  const data = await res.json();
  if (!res.ok || data.ok === false) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}
async function refresh() {
  showError("");
  try {
    const summary = await get("summary");
    $("unread").textContent = summary.unread;
    $("open-tasks").textContent = summary.open_tasks;
    $("posts").textContent = summary.posts;
    $("status").textContent = summary.agent;
    const digest = await get("digest");
    $("digest").innerHTML = markdown(digest.markdown || "");
  } catch (err) { showError(err.message); }
}
$("refresh").onclick = refresh;
$("read-all").onclick = async () => {
  try { const res = await fetch("/api/read-all", {method: "POST"}); const data = await res.json(); if (!res.ok || data.ok === false) throw new Error(data.error || "failed"); await refresh(); }
  catch (err) { showError(err.message); }
};
refresh();
