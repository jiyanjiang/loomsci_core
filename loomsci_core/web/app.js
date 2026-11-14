const TOKEN = window.__LOOMSCI_TOKEN__;
const $ = (selector) => document.querySelector(selector);
const itemsEl = $("#items");
const emptyEl = $("#empty");
const messageEl = $("#message");
const pendingFiles = [];

function showMessage(text, error = false) {
  messageEl.textContent = text;
  messageEl.classList.toggle("error", error);
}

async function api(path, options = {}) {
  const headers = { Authorization: "Bearer " + TOKEN };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
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
  let code = false;
  let list = null;
  let para = [];
  let i = 0;
  const flush = () => {
    if (para.length) { out.push(`<p>${inline(para.join(" "))}</p>`); para = []; }
  };
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
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
        ],
        throwOnError: false,
      });
    } catch { /* keep source */ }
  }
}

function tagList(tags) {
  const wrap = document.createElement("div");
  wrap.className = "meta";
  for (const tag of tags || []) {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = tag.tag;
    wrap.appendChild(span);
  }
  return wrap;
}

async function showBlob(container, blob) {
  if (String(blob.content_type || "").startsWith("image/")) {
    try {
      const response = await fetch("/v1/blobs/" + encodeURIComponent(blob.id), {
        headers: { Authorization: "Bearer " + TOKEN },
      });
      if (!response.ok) throw new Error("附件读取失败");
      const image = document.createElement("img");
      image.className = "attachment-image";
      image.alt = blob.filename;
      image.src = URL.createObjectURL(await response.blob());
      container.appendChild(image);
      return;
    } catch { /* fall through to filename */ }
  }
  const button = document.createElement("button");
  button.textContent = "📎 " + blob.filename;
  button.onclick = async () => {
    try {
      const response = await fetch("/v1/blobs/" + encodeURIComponent(blob.id), {
        headers: { Authorization: "Bearer " + TOKEN },
      });
      if (!response.ok) throw new Error("附件读取失败");
      window.open(URL.createObjectURL(await response.blob()), "_blank");
    } catch (error) {
      showMessage(error.message, true);
    }
  };
  container.appendChild(button);
}

function render(items) {
  itemsEl.replaceChildren();
  emptyEl.hidden = items.length > 0;
  for (const item of items) {
    const row = document.createElement("article");
    row.className = "item";

    const body = document.createElement("div");
    body.className = "md";
    body.innerHTML = markdown(item.body || "");
    row.appendChild(body);
    renderMath(body);

    row.appendChild(tagList(item.tags));

    if (item.blobs && item.blobs.length) {
      const files = document.createElement("div");
      files.className = "meta attachments";
      for (const blob of item.blobs) showBlob(files, blob);
      row.appendChild(files);
    }

    const actions = document.createElement("div");
    actions.className = "row-actions";

    const edit = document.createElement("button");
    edit.textContent = "编辑";
    edit.onclick = () => {
      const editor = document.createElement("div");
      editor.className = "editor";
      const bodyInput = document.createElement("textarea");
      bodyInput.value = item.body || "";
      bodyInput.rows = 8;
      const editorActions = document.createElement("div");
      editorActions.className = "row-actions";
      const save = document.createElement("button");
      save.textContent = "保存";
      save.className = "primary";
      const cancel = document.createElement("button");
      cancel.textContent = "取消";
      cancel.onclick = () => load();
      save.onclick = async () => {
        if (!bodyInput.value.trim()) {
          showMessage("正文不能为空", true);
          return;
        }
        try {
          await api("/v1/items/" + encodeURIComponent(item.id), {
            method: "PATCH",
            body: JSON.stringify({ body: bodyInput.value }),
          });
          await load();
          showMessage("已更新");
        } catch (error) {
          showMessage(error.message, true);
        }
      };
      editorActions.append(save, cancel);
      editor.append(bodyInput, editorActions);
      row.replaceChildren(editor);
    };
    actions.appendChild(edit);

    const remove = document.createElement("button");
    remove.textContent = "删除";
    remove.onclick = async () => {
      if (!confirm("删除这条内容？")) return;
      try {
        await api("/v1/items/" + encodeURIComponent(item.id), { method: "DELETE" });
        await load();
        showMessage("已删除");
      } catch (error) {
        showMessage(error.message, true);
      }
    };
    actions.appendChild(remove);

    row.appendChild(actions);
    itemsEl.appendChild(row);
  }
}

async function load(query = "") {
  const path = query
    ? "/v1/search?q=" + encodeURIComponent(query)
    : "/v1/items?limit=100";
  const data = await api(path);
  render(data.items || []);
  $("#status").textContent = "Core 已连接";
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
    const preview = file.type.startsWith("image/") ? URL.createObjectURL(file) : "";
    pendingFiles.push({ file, preview });
  }
  renderPending();
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
    const name = document.createElement("span");
    name.textContent = entry.file.name;
    chip.appendChild(name);
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
    showMessage("当前浏览器不支持读取剪贴板，请直接 Ctrl+V", true);
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
    else showMessage("剪贴板里没有图片", true);
  } catch (error) {
    showMessage("读取剪贴板失败：" + error.message, true);
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
      const file = entry.file;
      await api("/v1/blobs", {
        method: "POST",
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type || "application/octet-stream",
          content_base64: await fileToBase64(file),
          item_id: item.id,
        }),
      });
    }
    const count = pendingFiles.length;
    for (const entry of pendingFiles) {
      if (entry.preview) URL.revokeObjectURL(entry.preview);
    }
    pendingFiles.length = 0;
    renderPending();
    event.target.reset();
    await load();
    showMessage("已创建" + (count ? "，附件 " + count + " 个" : ""));
  } catch (error) {
    showMessage(error.message, true);
  }
});

$("#search-button").addEventListener("click", async () => {
  try {
    await load($("#search").value.trim());
  } catch (error) {
    showMessage(error.message, true);
  }
});

$("#search").addEventListener("keydown", (event) => {
  if (event.key === "Enter") $("#search-button").click();
});

$("#clear-search").addEventListener("click", async () => {
  $("#search").value = "";
  try {
    await load();
  } catch (error) {
    showMessage(error.message, true);
  }
});

$("#backup").addEventListener("click", async () => {
  try {
    const data = await api("/v1/backups", { method: "POST" });
    showMessage("备份已创建：" + data.backup.name);
  } catch (error) {
    showMessage(error.message, true);
  }
});

load().catch((error) => {
  showMessage(error.message, true);
  $("#status").textContent = "Core 未连接";
});
