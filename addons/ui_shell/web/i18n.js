(() => {
  const messages = {
    en: {
      "app.title": "loomsci ui-shell",
      "app.name": "loomsci",
      "nav.posts": "Posts",
      "nav.tasks": "Tasks",
      "nav.memory": "Memory",
      "nav.inbox": "Inbox",
      "nav.site": "Site",
      "status.connecting": "connecting…",
      "status.local": "{service} {version} · local",
      "status.unreachable": "core unreachable",
      "common.remove": "Remove {name}",
      "posts.titlePlaceholder": "Title",
      "posts.bodyPlaceholder": "Markdown + $LaTeX$ body; paste an image here",
      "posts.pasteImage": "Paste image from clipboard",
      "posts.post": "Post",
      "posts.searchPlaceholder": "Search posts, tasks, facts",
      "posts.search": "Search",
      "posts.empty": "No posts yet.",
      "posts.results": "Results for {query}",
      "posts.noResults": "No results.",
      "posts.clipboardUnsupported": "This browser does not expose navigator.clipboard.read; use copy/paste or the file picker.",
      "posts.clipboardEmpty": "Clipboard contains no image.",
      "posts.clipboardFailed": "Clipboard read failed: {error}. Use Cmd/Ctrl+V in the body or the file picker.",
      "posts.clipboardNoFile": "Clipboard did not expose an image file; copy the image itself (not a file path) and paste again.",
      "tasks.titlePlaceholder": "Task title",
      "tasks.acceptancePlaceholder": "Acceptance criteria",
      "tasks.add": "Add task",
      "tasks.empty": "No tasks yet.",
      "tasks.claim": "Claim",
      "tasks.done": "Done",
      "tasks.evidencePlaceholder": "Evidence",
      "tasks.unassigned": "unassigned",
      "tasks.status.open": "open",
      "tasks.status.claimed": "claimed",
      "tasks.status.done": "done",
      "memory.claimPlaceholder": "Fact / claim",
      "memory.sourcePlaceholder": "Source",
      "memory.evidencePlaceholder": "Evidence",
      "memory.add": "Add candidate fact",
      "memory.empty": "No facts yet.",
      "memory.approve": "Approve",
      "memory.reject": "Reject",
      "memory.noSource": "no source",
      "memory.status.candidate": "candidate",
      "memory.status.approved": "approved",
      "memory.status.rejected": "rejected",
      "inbox.empty": "No mentions.",
      "inbox.read": "read",
      "inbox.unread": "unread",
      "inbox.markRead": "Mark read",
      "site.title": "Site settings",
      "site.nameLabel": "Site name",
      "site.logoLabel": "Logo URL",
      "site.linksLabel": "Links (one per line: label | URL)",
      "site.footerLabel": "Footer",
      "site.save": "Save site",
      "site.saved": "Saved.",
      "site.invalidLinks": "Links must use http(s), mailto, or a local path.",
    },
    "zh-CN": {
      "app.title": "loomsci 界面",
      "app.name": "loomsci",
      "nav.posts": "帖子",
      "nav.tasks": "任务",
      "nav.memory": "记忆",
      "nav.inbox": "收件箱",
      "nav.site": "站点",
      "status.connecting": "正在连接…",
      "status.local": "{service} {version} · 本地",
      "status.unreachable": "Core 不可达",
      "common.remove": "移除 {name}",
      "posts.titlePlaceholder": "标题",
      "posts.bodyPlaceholder": "Markdown + $LaTeX$ 正文；可直接粘贴图片",
      "posts.pasteImage": "从剪贴板粘贴图片",
      "posts.post": "发布",
      "posts.searchPlaceholder": "搜索帖子、任务、事实",
      "posts.search": "搜索",
      "posts.empty": "还没有帖子。",
      "posts.results": "“{query}”的搜索结果",
      "posts.noResults": "没有结果。",
      "posts.clipboardUnsupported": "当前浏览器不支持 navigator.clipboard.read；请使用复制/粘贴或文件选择器。",
      "posts.clipboardEmpty": "剪贴板中没有图片。",
      "posts.clipboardFailed": "读取剪贴板失败：{error}。请在正文中按 Cmd/Ctrl+V，或使用文件选择器。",
      "posts.clipboardNoFile": "剪贴板没有提供图片文件；请复制图片本身（不是文件路径）后重试。",
      "tasks.titlePlaceholder": "任务标题",
      "tasks.acceptancePlaceholder": "验收标准",
      "tasks.add": "添加任务",
      "tasks.empty": "还没有任务。",
      "tasks.claim": "领取",
      "tasks.done": "完成",
      "tasks.evidencePlaceholder": "证据",
      "tasks.unassigned": "未分配",
      "tasks.status.open": "待处理",
      "tasks.status.claimed": "已领取",
      "tasks.status.done": "已完成",
      "memory.claimPlaceholder": "事实 / 主张",
      "memory.sourcePlaceholder": "来源",
      "memory.evidencePlaceholder": "证据",
      "memory.add": "添加候选事实",
      "memory.empty": "还没有事实。",
      "memory.approve": "批准",
      "memory.reject": "拒绝",
      "memory.noSource": "无来源",
      "memory.status.candidate": "候选",
      "memory.status.approved": "已批准",
      "memory.status.rejected": "已拒绝",
      "inbox.empty": "没有提及。",
      "inbox.read": "已读",
      "inbox.unread": "未读",
      "inbox.markRead": "标记已读",
      "site.title": "站点设置",
      "site.nameLabel": "站点名称",
      "site.logoLabel": "Logo 地址",
      "site.linksLabel": "链接（每行：名称 | URL）",
      "site.footerLabel": "页脚",
      "site.save": "保存站点",
      "site.saved": "已保存。",
      "site.invalidLinks": "链接必须是 http(s)、mailto 或本地路径。",
    },
  };
  const fallback = "en";
  function normalize(value) {
    const raw = String(value || "").toLowerCase();
    if (raw.startsWith("zh")) return "zh-CN";
    return "en";
  }
  function stored() {
    try { return localStorage.getItem("loomsci.locale"); } catch { return ""; }
  }
  let locale = normalize(stored() || navigator.language || fallback);
  function t(key, vars = {}) {
    const table = messages[locale] || messages[fallback];
    let text = table[key] ?? messages[fallback][key] ?? key;
    for (const [name, value] of Object.entries(vars)) text = text.replaceAll(`{${name}}`, String(value));
    return text;
  }
  function applyStatic(root = document) {
    document.documentElement.lang = locale;
    document.title = t("app.title");
    root.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.setAttribute("placeholder", t(el.dataset.i18nPlaceholder)); });
    const select = document.getElementById("locale");
    if (select) select.value = locale;
  }
  function setLocale(value) {
    locale = normalize(value);
    try { localStorage.setItem("loomsci.locale", locale); } catch { /* ignore */ }
    applyStatic();
    return locale;
  }
  window.LS_I18N = { t, applyStatic, setLocale, get locale() { return locale; } };
})();
