const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const PAGE_SIZE = 20;

const I18N = {
  zh: {
    settings: "设置", newContent: "新建内容", bodyPlaceholder: "Markdown 正文；可直接粘贴图片",
    tagsPlaceholder: "标签，逗号分隔", pasteImage: "从剪贴板粘贴图片", publish: "发布",
    backup: "创建备份", searchPlaceholder: "搜索", search: "搜索", clear: "清除",
    empty: "暂无内容。先写一段 Markdown。", loadMore: "加载更多", back: "返回列表",
    navContent: "内容", navSite: "站点", navSettings: "设置", backHome: "返回主页",
    siteTitle: "站点", siteName: "站点名称", siteLogo: "Logo 地址",
    siteLogoHint: "不填则不显示 Logo。", backupTitle: "数据备份", backupHint: "备份包含 items、附件和 App 数据，不包含 token、代码、venv。恢复必须填入一个不存在的新目录。", refresh: "刷新", createBackup: "创建备份", restoreTarget: "恢复到空目录", verify: "验证", restore: "恢复", backupVerified: "备份验证通过", backupCreated: "备份已创建", backupRestored: "已恢复", selectItem: "选择一条内容",
    username: "用户名", deepseekKey: "DeepSeek API Key", fingerprint: "本机软指纹",
    save: "保存", rotate: "轮换软指纹", noMore: "没有更多了", deleted: "已删除",
    updated: "已更新", created: "已创建", saved: "已保存", tags: "标签", attachments: "附件",
    previous: "上一张", next: "下一张", close: "关闭", loading: "加载中",
    notFound: "内容不存在", error: "操作失败",
  },
  en: {
    settings: "Settings", newContent: "New content", bodyPlaceholder: "Markdown body; paste images directly",
    tagsPlaceholder: "Tags, comma separated", pasteImage: "Paste image", publish: "Publish",
    backup: "Create backup", searchPlaceholder: "Search", search: "Search", clear: "Clear",
    empty: "No content yet. Write some Markdown.", loadMore: "Load more", back: "Back to list",
    navContent: "Content", navSite: "Site", navSettings: "Settings", backHome: "Home",
    siteTitle: "Site", siteName: "Site name", siteLogo: "Logo URL",
    siteLogoHint: "Leave blank to hide the logo.", backupTitle: "Backups", backupHint: "Backups contain items, attachments, and app data. They exclude tokens, code, and venvs. Restore requires a new, non-existing directory.", refresh: "Refresh", createBackup: "Create backup", restoreTarget: "Restore to empty directory", verify: "Verify", restore: "Restore", backupVerified: "Backup verified", backupCreated: "Backup created", backupRestored: "Restored", selectItem: "Select an item",
    username: "Username", deepseekKey: "DeepSeek API Key", fingerprint: "Local fingerprint",
    save: "Save", rotate: "Rotate fingerprint", noMore: "No more items", deleted: "Deleted",
    updated: "Updated", created: "Created", saved: "Saved", tags: "Tags", attachments: "Attachments",
    previous: "Previous", next: "Next", close: "Close", loading: "Loading",
    notFound: "Item not found", error: "Operation failed",
  },
};
let lang = localStorage.getItem("loomsci.lang") || "zh";
const t = (key) => (I18N[lang] || I18N.zh)[key] || key;

const state = { items: [], offset: 0, tag: "", query: "", hasMore: false };
const pendingFiles = [];
const blobCache = new Map();
let galleryImages = [];
let galleryIndex = 0;

function showMessage(text, error = false) {
  const el = $("#message");
  el.textContent = text;
  el.classList.toggle("error", error);
}

function applyI18n() {
  $$("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $$("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
  $("#lang-toggle").textContent = lang === "zh" ? "EN" : "CN";
}

async function api(path, options = {}) {
  const headers = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers, credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || ("HTTP " + response.status));
  return data;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function safeUrl(url) {
  return /^(https?:\/\/|mailto:)/i.test(url) ? url : "#";
}

function inline(text) {
  return text.replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) =>
      `<a href="${escapeHTML(safeUrl(url))}" rel="noreferrer noopener">${label}</a>`);
}

function markdown(source) {
  const lines = escapeHTML(source).split("\n");
  const out = [];
  let code = false, list = null, para = [], i = 0;
  const flush = () => { if (para.length) { out.push(`<p>${inline(para.join(" "))}</p>`); para = []; } };
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };

  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("```")) {
      flush(); closeList();
      out.push(code ? "</code></pre>" : "<pre><code>");
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
      i++; continue;
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
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
        ],
        throwOnError: false,
      });
    } catch { /* keep source */ }
  }
}

function tagList(tags, clickable = true) {
  const wrap = document.createElement("div");
  wrap.className = "meta";
  for (const tag of tags || []) {
    const button = document.createElement("button");
    button.className = "tag";
    button.textContent = tag.tag;
    if (clickable) {
      button.onclick = (event) => {
        event.stopPropagation();
        setTag(tag.tag);
      };
    }
    wrap.appendChild(button);
  }
  return wrap;
}

function hashName(blob) {
  return blob.hash_name || blob.filename || blob.id;
}

function isImage(blob) {
  return String(blob.content_type || "").startsWith("image/");
}

function isMarkdown(blob) {
  const name = String(blob.filename || "").toLowerCase();
  return name.endsWith(".md") || name.endsWith(".markdown") || /markdown/.test(String(blob.content_type || ""));
}

async function blobURL(blob) {
  if (blobCache.has(blob.id)) return blobCache.get(blob.id);
  const response = await fetch("/v1/blobs/" + encodeURIComponent(blob.id), {
    credentials: "same-origin",
  });
  if (!response.ok) throw new Error("attachment failed");
  const url = URL.createObjectURL(await response.blob());
  blobCache.set(blob.id, url);
  return url;
}

async function thumb(blob, onClick) {
  const image = document.createElement("img");
  image.className = "thumb";
  image.alt = hashName(blob);
  image.onclick = onClick;
  try { image.src = await blobURL(blob); } catch { /* keep placeholder */ }
  return image;
}

function setTag(tag) {
  state.tag = state.tag === tag ? "" : tag;
  state.query = "";
  $("#search").value = "";
  loadItems(true);
  loadTags();
}

async function loadTags() {
  try {
    const data = await api("/v1/tags?limit=1000");
    const cloud = $("#tag-cloud");
    cloud.replaceChildren();
    for (const row of data.tags || []) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = row.tag === state.tag ? "active" : "";
      button.textContent = row.tag;
      const count = document.createElement("span");
      count.className = "tag-count";
      count.textContent = row.count;
      button.appendChild(count);
      button.onclick = () => setTag(row.tag);
      cloud.appendChild(button);
    }
  } catch (error) {
    showMessage(error.message, true);
  }
}

function itemCard(item) {
  const card = document.createElement("article");
  card.className = "item";
  card.onclick = () => { location.hash = "#/item/" + encodeURIComponent(item.id); };

  const summary = document.createElement("div");
  summary.className = "summary md";
  summary.innerHTML = markdown((item.body || "").slice(0, 420));
  card.appendChild(summary);
  renderMath(summary);
  card.appendChild(tagList(item.tags));

  const images = (item.blobs || []).filter(isImage);
  if (images.length) {
    const row = document.createElement("div");
    row.className = "thumb-row";
    images.forEach((blob, index) => {
      thumb(blob, async (event) => {
        event.stopPropagation();
        await openGallery(images, index);
      }).then((img) => row.appendChild(img));
    });
    card.appendChild(row);
  }
  return card;
}

function renderItems() {
  const list = $("#items");
  list.replaceChildren();
  $("#empty").hidden = state.items.length > 0;
  for (const item of state.items) list.appendChild(itemCard(item));
  $("#load-more").hidden = !state.hasMore;
}

async function loadItems(reset = true) {
  if (reset) { state.items = []; state.offset = 0; }
  let path;
  if (state.query) {
    path = "/v1/search?q=" + encodeURIComponent(state.query) + "&limit=" + PAGE_SIZE;
  } else {
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(state.offset) });
    if (state.tag) params.set("tag", state.tag);
    path = "/v1/items?" + params.toString();
  }
  const data = await api(path);
  const rows = data.items || [];
  state.items = reset ? rows : state.items.concat(rows);
  state.offset += rows.length;
  state.hasMore = !state.query && rows.length === PAGE_SIZE;
  renderItems();
  $("#status").textContent = "Core 已连接";
}

async function openGallery(blobs, index) {
  galleryImages = blobs;
  galleryIndex = index;
  await showGalleryImage();
  $("#gallery").hidden = false;
}

async function showGalleryImage() {
  const blob = galleryImages[galleryIndex];
  if (!blob) return;
  const image = $("#gallery-image");
  try { image.src = await blobURL(blob); } catch { image.src = ""; }
  image.alt = hashName(blob);
  $("#gallery-count").textContent = (galleryIndex + 1) + " / " + galleryImages.length;
}

function closeGallery() {
  $("#gallery").hidden = true;
  $("#gallery-image").src = "";
}

async function renderDetail(item) {
  const detail = $("#detail");
  detail.replaceChildren();
  const head = document.createElement("div");
  head.className = "detail-head";
  const back = document.createElement("button");
  back.textContent = t("back");
  back.onclick = () => { location.hash = "#/"; };
  head.appendChild(back);
  detail.appendChild(head);

  const body = document.createElement("div");
  body.className = "md detail-body";
  body.innerHTML = markdown(item.body || "");
  detail.appendChild(body);
  renderMath(body);
  detail.appendChild(tagList(item.tags));

  const attachments = item.blobs || [];
  if (attachments.length) {
    const section = document.createElement("section");
    section.className = "attachment-block";
    const heading = document.createElement("h2");
    heading.textContent = t("attachments");
    section.appendChild(heading);

    const images = attachments.filter(isImage);
    if (images.length) {
      const row = document.createElement("div");
      row.className = "thumb-row";
      for (let i = 0; i < images.length; i += 1) {
        const img = await thumb(images[i], () => openGallery(images, i));
        row.appendChild(img);
      }
      section.appendChild(row);
    }

    for (const blob of attachments.filter((x) => !isImage(x))) {
      if (isMarkdown(blob)) {
        const details = document.createElement("details");
        details.className = "md-attachment";
        details.open = true;
        const summary = document.createElement("summary");
        summary.textContent = hashName(blob);
        details.appendChild(summary);
        try {
          const response = await fetch("/v1/blobs/" + encodeURIComponent(blob.id) + "?inline=1", {
            credentials: "same-origin",
          });
          const data = await response.json();
          const md = document.createElement("div");
          md.className = "md";
          md.innerHTML = markdown(data.text || "");
          details.appendChild(md);
          renderMath(md);
        } catch {
          const fail = document.createElement("p");
          fail.className = "muted";
          fail.textContent = t("error");
          details.appendChild(fail);
        }
        section.appendChild(details);
      } else {
        const button = document.createElement("button");
        button.textContent = "📎 " + hashName(blob);
        button.onclick = async () => {
          try { window.open(await blobURL(blob), "_blank"); } catch { showMessage(t("error"), true); }
        };
        section.appendChild(button);
      }
    }
    detail.appendChild(section);
  }
}

async function route() {
  if (!$("#gallery").hidden) closeGallery();
  const hash = location.hash || "#/";
  const match = hash.match(/^#\/item\/(.+)$/);
  const isSettings = hash === "#/settings";
  const isSite = hash === "#/site";
  const isContent = !isSettings && !isSite;

  $("#compose-panel").hidden = !isContent;
  $("#list-view").hidden = !isContent;
  $("#settings-view").hidden = !isSettings;
  $("#site-view").hidden = !isSite;
  $("#detail-view").hidden = isSettings || isSite;

  $$(".rail nav button").forEach((button) => {
    button.classList.toggle("active",
      (button.dataset.view === "content" && isContent) ||
      (button.dataset.view === "settings" && isSettings) ||
      (button.dataset.view === "site" && isSite));
  });

  if (match) {
    $("#detail-empty").hidden = true;
    try {
      const data = await api("/v1/items/" + encodeURIComponent(decodeURIComponent(match[1])));
      await renderDetail(data.item);
    } catch (error) {
      $("#detail").textContent = error.message;
    }
  } else if (isSettings) {
    $("#detail").replaceChildren();
    showSettings();
  } else if (isSite) {
    $("#detail").replaceChildren();
    showSite();
  } else {
    $("#detail").replaceChildren();
    $("#detail-empty").hidden = false;
    if (!state.items.length) await loadItems(true);
    await loadTags();
  }
}

function generateFingerprint() {
  const id = crypto.randomUUID ? crypto.randomUUID() : (Date.now().toString(16) + Math.random().toString(16).slice(2));
  localStorage.setItem("loomsci.fingerprint", id);
  localStorage.setItem("loomsci.fingerprintAt", new Date().toISOString());
  return id;
}

function currentFingerprint() {
  const updated = Date.parse(localStorage.getItem("loomsci.fingerprintAt") || "");
  const stale = !updated || Date.now() - updated > 30 * 24 * 3600 * 1000;
  if (stale || !localStorage.getItem("loomsci.fingerprint")) return generateFingerprint();
  return localStorage.getItem("loomsci.fingerprint");
}

function showSettings() {
  $("#setting-username").value = localStorage.getItem("loomsci.username") || "";
  $("#setting-api-key").value = localStorage.getItem("loomsci.apiKey") || "";
  $("#setting-fingerprint").value = currentFingerprint();
  $("#settings-message").textContent = "";
  loadBackups();
}

async function loadBackups() {
  const list = $("#backup-list");
  list.replaceChildren();
  try {
    const data = await api("/v1/backups");
    for (const backup of data.backups || []) {
      const row = document.createElement("div");
      row.className = "backup-row";
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = backup.name;
      const verify = document.createElement("button");
      verify.type = "button";
      verify.textContent = t("verify");
      verify.onclick = async () => {
        try {
          await api("/v1/backups/verify", { method: "POST", body: JSON.stringify({ backup: backup.path }) });
          $("#backup-message").textContent = t("backupVerified");
        } catch (error) { $("#backup-message").textContent = error.message; }
      };
      const restore = document.createElement("button");
      restore.type = "button";
      restore.textContent = t("restore");
      restore.onclick = async () => {
        const target = $("#backup-target").value.trim();
        if (!target) { $("#backup-message").textContent = t("restoreTarget"); return; }
        try {
          await api("/v1/backups/restore", {
            method: "POST",
            body: JSON.stringify({ backup: backup.path, target }),
          });
          $("#backup-message").textContent = t("backupRestored") + ": " + target;
        } catch (error) { $("#backup-message").textContent = error.message; }
      };
      row.append(name, verify, restore);
      list.appendChild(row);
    }
  } catch (error) {
    $("#backup-message").textContent = error.message;
  }
}

async function createBackupFromSettings() {
  try {
    const data = await api("/v1/backups", { method: "POST" });
    $("#backup-message").textContent = t("backupCreated") + ": " + data.backup.name;
    await loadBackups();
  } catch (error) {
    $("#backup-message").textContent = error.message;
  }
}

function saveSettings(event) {
  event.preventDefault();
  localStorage.setItem("loomsci.username", $("#setting-username").value.trim());
  localStorage.setItem("loomsci.apiKey", $("#setting-api-key").value);
  applyI18n();
  $("#settings-message").textContent = t("saved");
}

function applySite() {
  let site = {};
  try { site = JSON.parse(localStorage.getItem("loomsci.site") || "{}"); } catch { site = {}; }
  const name = String(site.name || "").trim() || "LoomSci Core";
  $("#brand-name").textContent = name;
  document.title = name;
  const logo = String(site.logo || "").trim();
  const image = $("#brand-logo");
  if (logo && /^(https?:\/\/|\/)/i.test(logo)) {
    image.src = logo;
    image.hidden = false;
  } else {
    image.removeAttribute("src");
    image.hidden = true;
  }
}

function showSite() {
  let site = {};
  try { site = JSON.parse(localStorage.getItem("loomsci.site") || "{}"); } catch { site = {}; }
  $("#site-name").value = site.name || "";
  $("#site-logo").value = site.logo || "";
  $("#site-message").textContent = "";
}

function saveSite(event) {
  event.preventDefault();
  const site = {
    name: $("#site-name").value.trim(),
    logo: $("#site-logo").value.trim(),
  };
  localStorage.setItem("loomsci.site", JSON.stringify(site));
  applySite();
  $("#site-message").textContent = t("saved");
}

function renderPending() {
  const target = $("#pending-files");
  target.replaceChildren();
  pendingFiles.forEach((entry, index) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    if (entry.preview) {
      const image = document.createElement("img");
      image.className = "pending-preview";
      image.src = entry.preview;
      image.alt = entry.file.name;
      image.onclick = () => window.open(entry.preview, "_blank");
      chip.appendChild(image);
    }
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.onclick = () => {
      if (entry.preview) URL.revokeObjectURL(entry.preview);
      pendingFiles.splice(index, 1);
      renderPending();
    };
    chip.appendChild(remove);
    target.appendChild(chip);
  });
}

function normalizeFile(file) {
  if (file.name) return file;
  const ext = (file.type.split("/")[1] || "png").replace("+xml", "");
  return new File([file], `pasted-${Date.now()}.${ext}`, { type: file.type || "image/png" });
}

function addFiles(files) {
  for (const item of files || []) {
    if (!item || !item.size) continue;
    const file = normalizeFile(item);
    pendingFiles.push({
      file,
      preview: file.type.startsWith("image/") ? URL.createObjectURL(file) : "",
    });
  }
  renderPending();
}

function clipboardImages(event) {
  const data = event.clipboardData;
  if (!data) return [];
  const files = [...(data.files || [])].filter((file) => file.type.startsWith("image/"));
  if (files.length) return files;
  return [...(data.items || [])]
    .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
    .map((item) => item.getAsFile())
    .filter(Boolean);
}

async function fileToBase64(file) {
  const buffer = await file.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

$("#file").addEventListener("change", (event) => addFiles(event.target.files));

$("#paste-image").addEventListener("click", async () => {
  showMessage("");
  if (!navigator.clipboard?.read) {
    showMessage(t("pasteImage") + ": unsupported", true);
    return;
  }
  try {
    const items = await navigator.clipboard.read();
    const files = [];
    for (const item of items) {
      const type = item.types.find((value) => value.startsWith("image/"));
      if (type) {
        files.push(new File([await item.getType(type)], `clipboard-${Date.now()}.${type.split("/")[1] || "png"}`, { type }));
      }
    }
    if (files.length) addFiles(files);
    else showMessage(t("empty"), true);
  } catch (error) {
    showMessage(error.message, true);
  }
});

document.addEventListener("paste", (event) => {
  if (!document.getElementById("create-form")) return;
  const files = clipboardImages(event);
  if (!files.length) return;
  event.preventDefault();
  addFiles(files);
});

$("#create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = $("#body").value;
  const tags = $("#tags").value.split(",").map((x) => x.trim()).filter(Boolean);
  if (!body.trim()) return;
  try {
    const created = await api("/v1/items", {
      method: "POST",
      body: JSON.stringify({ app: "core", type: "core.note", title: "", body, tags }),
    });
    const item = created.item;
    for (const entry of pendingFiles) {
      await api("/v1/blobs", {
        method: "POST",
        body: JSON.stringify({
          filename: entry.file.name,
          content_type: entry.file.type || "application/octet-stream",
          content_base64: await fileToBase64(entry.file),
          item_id: item.id,
        }),
      });
    }
    const count = pendingFiles.length;
    for (const entry of pendingFiles) if (entry.preview) URL.revokeObjectURL(entry.preview);
    pendingFiles.length = 0;
    renderPending();
    event.target.reset();
    state.items = [];
    await loadItems(true);
    await loadTags();
    showMessage(t("created") + (count ? " · " + count : ""));
  } catch (error) {
    showMessage(error.message, true);
  }
});

$("#search-button").addEventListener("click", async () => {
  state.query = $("#search").value.trim();
  state.tag = "";
  try { await loadItems(true); await loadTags(); } catch (error) { showMessage(error.message, true); }
});

$("#search").addEventListener("keydown", (event) => {
  if (event.key === "Enter") $("#search-button").click();
});

$("#clear-search").addEventListener("click", async () => {
  state.query = "";
  state.tag = "";
  $("#search").value = "";
  try { await loadItems(true); await loadTags(); } catch (error) { showMessage(error.message, true); }
});

$("#load-more").addEventListener("click", async () => {
  try { await loadItems(false); } catch (error) { showMessage(error.message, true); }
});

$("#backup").addEventListener("click", async () => {
  try {
    const data = await api("/v1/backups", { method: "POST" });
    showMessage(t("backup") + ": " + data.backup.name);
  } catch (error) {
    showMessage(error.message, true);
  }
});

$$(".rail nav button").forEach((button) => {
  button.addEventListener("click", () => {
    location.hash = button.dataset.view === "content" ? "#/" : "#/" + button.dataset.view;
  });
});
$("#lang-toggle").addEventListener("click", async () => {
  lang = lang === "zh" ? "en" : "zh";
  localStorage.setItem("loomsci.lang", lang);
  applyI18n();
  await route();
});
$$("[data-home]").forEach((button) => {
  button.addEventListener("click", () => { location.hash = "#/"; });
});
$("#settings-form").addEventListener("submit", saveSettings);
$("#site-form").addEventListener("submit", saveSite);
$("#backup-refresh").addEventListener("click", loadBackups);
$("#backup-create-settings").addEventListener("click", createBackupFromSettings);
$("#rotate-fingerprint").addEventListener("click", () => {
  $("#setting-fingerprint").value = generateFingerprint();
  $("#settings-message").textContent = t("saved");
});

$("#gallery-close").addEventListener("click", closeGallery);
$("#gallery-prev").addEventListener("click", async () => {
  galleryIndex = (galleryIndex - 1 + galleryImages.length) % galleryImages.length;
  await showGalleryImage();
});
$("#gallery-next").addEventListener("click", async () => {
  galleryIndex = (galleryIndex + 1) % galleryImages.length;
  await showGalleryImage();
});
$("#gallery").addEventListener("click", (event) => { if (event.target.id === "gallery") closeGallery(); });
document.addEventListener("keydown", (event) => {
  if ($("#gallery").hidden) return;
  if (event.key === "Escape") closeGallery();
  if (event.key === "ArrowLeft") $("#gallery-prev").click();
  if (event.key === "ArrowRight") $("#gallery-next").click();
});

window.addEventListener("hashchange", () => route().catch((error) => showMessage(error.message, true)));

applyI18n();
applySite();
currentFingerprint();
route().catch((error) => {
  showMessage(error.message, true);
  $("#status").textContent = "Core 未连接";
});
