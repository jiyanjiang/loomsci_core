const $ = (id) => document.getElementById(id);
let current = null;
function showError(message) { $("error").hidden = !message; $("error").textContent = message || ""; }
function esc(value) { return String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
async function api(path, options = {}) {
  const opts = {...options, headers: {...(options.headers || {})}};
  if (opts.body && typeof opts.body !== "string") { opts.body = JSON.stringify(opts.body); opts.headers["Content-Type"] = "application/json"; }
  const res = await fetch("/api/" + path, opts);
  const text = await res.text(); let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = {error:text}; }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}
async function loadList() {
  const data = await api("workspaces");
  $("list").innerHTML = (data.workspaces || []).map((w) =>
    `<div class="item" data-ref="${esc(w.code + '@' + w.version)}"><b>${esc(w.title)}</b><span class="muted">${esc(w.code)}/${esc(w.version)} · sources ${w.sources} · facts ${w.facts}</span></div>`
  ).join("") || '<p class="muted">No workspaces yet.</p>';
  $("list").querySelectorAll(".item").forEach((el) => { el.onclick = () => select(el.dataset.ref); });
}
async function select(ref) {
  current = ref; showError("");
  const data = await api(`workspaces/${encodeURIComponent(ref)}`);
  $("title").textContent = data.title || ref;
  $("meta").textContent = `${data.code}/${data.version} · ${data.prompt}`;
  $("detail").hidden = false;
  $("draft").value = data.draft || "";
  $("sources").innerHTML = (data.sources || []).map((s) =>
    `<div class="item"><b>${esc(s.id)} · ${esc(s.title)}</b><span class="muted">${esc(s.grade)} · ${esc(s.url)}</span></div>`).join("") || '<p class="muted">No sources.</p>';
  $("facts").innerHTML = (data.facts || []).map((f) =>
    `<div class="item"><b>${esc(f.id)} · ${esc(f.claim)}</b><span class="muted">${esc(f.grade)} · ${esc(f.url)}</span></div>`).join("") || '<p class="muted">No facts.</p>';
  $("gate").textContent = data.check ? JSON.stringify(data.check, null, 2) : "";
  await loadList();
}
$("new-form").onsubmit = async (e) => {
  e.preventDefault(); const f = new FormData(e.target);
  try { const data = await api("workspaces", {method:"POST", body:{prompt:f.get("prompt"), title:f.get("title")}}); e.target.reset(); await loadList(); await select(data.code + "@" + data.version); }
  catch (err) { showError(err.message); }
};
$("source-form").onsubmit = async (e) => {
  e.preventDefault(); const f = new FormData(e.target);
  try { await api(`workspaces/${encodeURIComponent(current)}/sources`, {method:"POST", body:{url:f.get("url"), title:f.get("title"), text:f.get("text")}}); e.target.reset(); await select(current); }
  catch (err) { showError(err.message); }
};
$("fact-form").onsubmit = async (e) => {
  e.preventDefault(); const f = new FormData(e.target);
  try { await api(`workspaces/${encodeURIComponent(current)}/facts`, {method:"POST", body:{claim:f.get("claim"), url:f.get("url"), quote:f.get("quote")}}); e.target.reset(); await select(current); }
  catch (err) { showError(err.message); }
};
$("save").onclick = async () => {
  try { await api(`workspaces/${encodeURIComponent(current)}/draft`, {method:"POST", body:{draft:$("draft").value}}); await select(current); }
  catch (err) { showError(err.message); }
};
$("check").onclick = async () => {
  try { await api(`workspaces/${encodeURIComponent(current)}/draft`, {method:"POST", body:{draft:$("draft").value}}); const data = await api(`workspaces/${encodeURIComponent(current)}/check`, {method:"POST", body:{}}); $("gate").textContent = JSON.stringify(data.gate, null, 2); await loadList(); }
  catch (err) { showError(err.message); }
};
$("publish").onclick = async () => {
  try { const data = await api(`workspaces/${encodeURIComponent(current)}/publish`, {method:"POST", body:{}}); showError(""); alert("Published: " + (data.post?.id || "ok")); }
  catch (err) { showError(err.message); }
};
loadList().catch((err) => showError(err.message));
