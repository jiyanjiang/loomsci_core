"""Deterministic source/fact gate for research.ask.

This module does not decide whether a prose claim is true. It enforces the
minimum evidence contract:

  * at least two independent source domains;
  * at least one official/primary/academic source (not all weak media);
  * the answer cites at least two source ids/URLs from the supplied set;
  * an explicit abstention ("来源不足/无法核验") is never marked verified.

The gate is intentionally conservative: a false negative is preferable to a
false "verified" badge.
"""
from __future__ import annotations

import re
import urllib.parse

_STRONG = {"official", "primary"}
_OFFICIAL = (".gov.cn", "gov.cn", ".edu.cn", "edu.cn", "archives.", "loc.gov", "europa.eu")
_PRIMARY = ("doi.org", "nature.com", "science.org", "aps.org", "arxiv.org", "jstor.org", "springer.com", "ac.cn")
_SECONDARY = ("wikipedia.org", "baike.baidu.com", "britannica.com", "openalex.org", "crossref.org")
_WEAK = ("sohu.com", "163.com", "sina.com.cn", "qq.com", "toutiao.com", "baijiahao.baidu.com", "weixin.qq.com", "douban.com")


def grade_for(url: str) -> str:
    host = (urllib.parse.urlparse(url or "").hostname or "").lower()
    if any(host == h or host.endswith("." + h.lstrip(".")) or h in host for h in _OFFICIAL):
        return "official"
    if any(h in host for h in _PRIMARY):
        return "primary"
    if any(h in host for h in _SECONDARY):
        return "secondary"
    if any(h in host for h in _WEAK):
        return "weak"
    return "weak"


def _host(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def evaluate(answer: str, sources: list[dict], *,
             query_terms: list[str] | None = None) -> dict:
    """答案 + 来源 → 门禁判定。

    query_terms：检索词（中文原式/英文译式）。给了就多查一条**切题性**——
    被引用的来源里至少得有一条标题/摘要与检索词有词面交集。
    背景（2026-11-02 实测）：单看“域名数/强来源数”挡不住跑题论文，
    一篇 grade=primary 但与问题无关的论文照样能帮答案过关。
    这条只在**全部**被引来源都与检索词零交集时才判失败，属保守兜底，不做逐条筛选。
    """
    text = answer or ""
    srcs = [s for s in (sources or []) if isinstance(s, dict) and s.get("url")]
    domains = {_host(s["url"]) for s in srcs if _host(s["url"])}
    strong = {s.get("id") or s.get("url") for s in srcs
              if str(s.get("grade") or "").lower() in _STRONG}
    ids = {str(s.get("id") or "").upper() for s in srcs if s.get("id")}
    urls = {str(s.get("url") or "") for s in srcs if s.get("url")}

    cited_ids = {x.upper() for x in re.findall(r"\[(S\d+)\]", text, re.I)}
    cited_urls = {u.rstrip(".,);]") for u in re.findall(r"https?://[^\s)>\]]+", text)}
    cited = (cited_ids & ids) | (cited_urls & urls)
    abstain = bool(re.search(r"来源不足|无法核验|未能核验|缺证据|无来源|未核验", text))

    reasons: list[str] = []
    if len(domains) < 2:
        reasons.append(f"独立来源域名不足({len(domains)})")
    if not strong:
        reasons.append("缺少官方/一手/学术来源")
    if len(cited) < 2:
        reasons.append(f"答案引用来源不足({len(cited)})")
    if abstain:
        reasons.append("答案显式声明来源不足/未核验")

    # 切题性：只在被引来源**全部**跟检索词零交集时才判失败
    topical: int | None = None
    terms = [str(t).lower() for t in (query_terms or []) if t and len(str(t)) >= 2]
    if terms:
        used = [s for s in srcs
                if str(s.get("id") or "").upper() in cited_ids
                or str(s.get("url") or "") in cited_urls]
        topical = 0
        for s in used:
            blob = f"{s.get('title') or ''} {s.get('snippet') or ''}".lower()
            if any(t in blob for t in terms):
                topical += 1
        if used and topical == 0:
            reasons.append(f"被引用来源({len(used)})与检索词无任何交集（疑似跑题）")

    ok = not reasons
    return {
        "ok": ok,
        "status": "verified" if ok else "unverified",
        "reasons": reasons,
        "source_count": len(srcs),
        "domain_count": len(domains),
        "strong_count": len(strong),
        "cited_count": len(cited),
        "cited": sorted(str(x) for x in cited)[:8],
        "topical_count": topical,
        "abstained": abstain,
    }
