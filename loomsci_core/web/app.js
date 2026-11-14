const TOKEN = window.__LOOMSCI_TOKEN__;
const $ = (selector) => document.querySelector(selector);
const itemsEl = $("#items");
const emptyEl = $("#empty");
const messageEl = $("#message");

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

function render(items) {
  itemsEl.replaceChildren();
  emptyEl.hidden = items.length > 0;
  for (const item of items) {
    const row = document.createElement("article");
    row.className = "item";

    const title = document.createElement("h3");
    title.textContent = item.title || "(无标题)";
    row.appendChild(title);

    const body = document.createElement("div");
    body.className = "body";
    body.textContent = item.body || "";
    row.appendChild(body);

    row.appendChild(tagList(item.tags));

    if (item.blobs && item.blobs.length) {
      const files = document.createElement("div");
      files.className = "meta";
      for (const blob of item.blobs) {
        const link = document.createElement("button");
        link.textContent = "📎 " + blob.filename;
        link.onclick = async () => {
          try {
            const response = await fetch("/v1/blobs/" + encodeURIComponent(blob.id), {
              headers: { Authorization: "Bearer " + TOKEN },
            });
            if (!response.ok) throw new Error("附件读取失败");
            const url = URL.createObjectURL(await response.blob());
            window.open(url, "_blank");
          } catch (error) {
            showMessage(error.message, true);
          }
        };
        files.appendChild(link);
      }
      row.appendChild(files);
    }

    const actions = document.createElement("div");
    actions.className = "row-actions";

    const edit = document.createElement("button");
    edit.textContent = "编辑";
    edit.onclick = () => {
      const editor = document.createElement("div");
      editor.className = "editor";

      const titleInput = document.createElement("input");
      titleInput.value = item.title || "";
      titleInput.placeholder = "标题";
      const bodyInput = document.createElement("textarea");
      bodyInput.value = item.body || "";
      bodyInput.rows = 5;
      bodyInput.placeholder = "正文";

      const editorActions = document.createElement("div");
      editorActions.className = "row-actions";
      const save = document.createElement("button");
      save.textContent = "保存";
      save.className = "primary";
      const cancel = document.createElement("button");
      cancel.textContent = "取消";
      cancel.onclick = () => load();
      save.onclick = async () => {
        if (!titleInput.value.trim() || !bodyInput.value) {
          showMessage("标题和正文不能为空", true);
          return;
        }
        try {
          await api("/v1/items/" + encodeURIComponent(item.id), {
            method: "PATCH",
            body: JSON.stringify({ title: titleInput.value, body: bodyInput.value }),
          });
          await load();
          showMessage("已更新");
        } catch (error) {
          showMessage(error.message, true);
        }
      };
      editorActions.append(save, cancel);
      editor.append(titleInput, bodyInput, editorActions);
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

$("#create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = $("#title").value.trim();
  const body = $("#body").value;
  const tags = $("#tags").value.split(",").map((x) => x.trim()).filter(Boolean);
  if (!title || !body) return;
  try {
    const created = await api("/v1/items", {
      method: "POST",
      body: JSON.stringify({ app: "core", type: "core.note", title, body, tags }),
    });
    const item = created.item;
    const files = Array.from($("#file").files || []);
    for (const file of files) {
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
    event.target.reset();
    await load();
    showMessage("已创建" + (files.length ? "，附件 " + files.length + " 个" : ""));
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
