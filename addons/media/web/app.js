const grid = document.getElementById("grid");
const countsEl = document.getElementById("counts");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
let items = [], filter = "all";

function esc(value) { return String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function showError(message) { errorEl.hidden = !message; errorEl.textContent = message || ""; }
function render() {
  const visible = filter === "all" ? items : items.filter((item) => item.kind === filter);
  grid.innerHTML = visible.map((item) => {
    const src = `/api/attachment/${encodeURIComponent(item.id)}`;
    let media = `<a href="${src}">${esc(item.filename)}</a>`;
    const thumb = item.thumbnail || src;
    if (item.kind === "image") media = `<a href="${src}" target="_blank" rel="noreferrer"><img class="media" src="${thumb}" onerror="this.src='${src}'" alt="${esc(item.filename)}" loading="lazy"></a>`;
    if (item.kind === "audio") media = `<audio controls preload="metadata" src="${src}"></audio>`;
    if (item.kind === "video") media = `<video class="media" controls preload="metadata" poster="${thumb}" src="${src}"></video>`;
    return `<article class="card">${media}<div class="name">${esc(item.filename)}</div><div class="muted">${esc(item.kind)} · ${Math.ceil((item.bytes || 0)/1024)} KB · ${esc(item.author || "")}</div></article>`;
  }).join("") || '<p class="empty">No media yet.</p>';
}
async function load() {
  showError("");
  try {
    const res = await fetch("/api/library");
    const data = await res.json();
    if (!res.ok || data.ok === false) throw new Error(data.error || `HTTP ${res.status}`);
    items = data.items || [];
    countsEl.textContent = `images ${data.counts.image} · audio ${data.counts.audio} · video ${data.counts.video} · files ${data.counts.file}`;
    render();
  } catch (err) { showError(err.message); }
}
document.querySelectorAll(".filters button").forEach((button) => {
  button.onclick = () => {
    filter = button.dataset.kind;
    document.querySelectorAll(".filters button").forEach((b) => b.classList.toggle("active", b === button));
    render();
  };
});
fetch("/api/library").then((r) => r.json()).then((d) => { statusEl.textContent = d.ok ? "core library" : "core unreachable"; }).catch(() => { statusEl.textContent = "core unreachable"; });
load();
