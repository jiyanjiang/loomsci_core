# Report App 产品规格 v0

- 状态：草案，2026-11-14
- 产品线：LoomSci Core + LoomSci Report
- 免费版：只用公开资源
- 最终交付物：Markdown + PDF + EPUB
- 参考：`research.ask` 流程、LoomReport、TAA `p-64b4f07f`、`p-1a4bff83`

## 1. 定位

Report 是 LoomSci 的第一个免费 App。它把研究问题变成可复现、可回源的研究简报，并导出 MD、PDF、EPUB。

```text
问题
→ 查询规划
→ 公开源检索
→ 来源登记
→ 证据抽取
→ 综合写作
→ 确定性校验
→ MD / PDF / EPUB
```

不是聊天 UI，不是通用搜索引擎，不是付费数据库阅读器。

## 2. 免费资源边界

免费 Report 只用公开/开放资源：

- PubMed / PMC
- arXiv（允许使用本地库）
- Nature Physics 开放获取文章
- DeepSeek Search API / 联网搜索 / 深度思考搜索 / 文件输入 / 链接阅读
- 必要时用 Crossref / OpenAlex / Unpaywall 元数据

规则：

- 不抓取付费墙全文
- 只存元数据、摘要、OA 全文、来源 URL
- 保存内容 hash 与访问日期
- 无法核验的来源不能进入引用
- 付费 lexicon/PMC 全库是后续付费 App，不属于免费 Report

## 3. 黄金任务

### G1 · PISA 科学传播

来源：TAA `p-64b4f07f`。

真实需求：一份多部分、图文并茂的 PISA / 科学传播研究报告。  
这是第一个端到端验收任务。

### G2 · 95 页手册

来源：TAA `p-1a4bff83`。

质量/排版参考：长文 PDF、章节、引用、表格、图、页码检查。  
Report 默认不需要 95 页，但导出管线必须支持这个量级。

## 4. 数据模型

```text
articles
  id, doi, pmid, pmcid, arxiv_id
  title, abstract, authors_json
  journal, year, article_type
  oa_status, license
  url, full_text_url
  source, fetched_at, content_hash

article_matches
  left_id, right_id, method, confidence

report_sources
  report_id, article_id, role, claim_ids_json
```

优先级：

```text
PMC / arXiv 全文
→ Nature Physics OA
→ PubMed 摘要
→ 仅元数据
```

## 5. 建库步骤

1. 收集 Nature Physics `perspective` 文章
2. 解析 DOI、年份、作者、license、OA 状态
3. 在 PMC 与本地 arXiv 库中匹配
4. 只存元数据/摘要/OA 全文，不复制付费全文
5. 建立 50–100 篇匹配样本库
6. 先用样本库做检索与导出测试，再接实时网络

样本库只作测试夹具，不重新分发全文。

## 6. 报告流水线

```text
1. 输入
   问题、受众、语言、长度、图表、截止时间
2. 查询规划
   3–6 个 query；背景词 + 主词；中英按需
3. 检索
   DeepSeek Search + PMC + arXiv + Nature OA；按 DOI/PMID/arXiv 去重
4. 来源登记
   标题、作者、年份、venue、URL、license、访问日期、hash
5. 证据
   claim、excerpt、source、evidence level、section
6. 综合
   只使用已登记来源；每个事实句带引用
7. 校验
   URL/ID 可解析；摘录可匹配；引用覆盖；冲突标注
8. 导出
   规范 MD → PDF + EPUB
```

## 7. 证据等级

```text
L0  模型推断，无来源
L1  仅主题相关
L2  摘要支持该论断
L3  全文支持该论断
L4  全文 + 图表支持
L5  多篇独立来源支持
```

关键论断必须显示等级。低于 L2 不能写成确定事实。

## 8. 交付物

### Markdown

- 唯一真相源
- YAML front matter
- `[F###]` 引用
- 图表引用
- 来源附录

### PDF

- 封面、目录、章节、图表、参考文献
- 页码与页眉
- 表格不截断，无近空白页
- 页数与排版自检

### EPUB

- 可重排
- 目录/导航
- 图片 alt
- 脚注/尾注
- `epubcheck` 通过

### 复现清单

```json
{
  "report_id": "...",
  "question": "...",
  "sources": ["..."],
  "prompt_version": "...",
  "model": "...",
  "created_at": "...",
  "outputs": {"md": "...", "pdf": "...", "epub": "..."}
}
```

## 9. 质量门禁

- 100% 引用 URL/ID 可解析，或显式标注不可用
- 100% 引用能映射到登记来源
- 正文无未引用事实句
- 研究简报至少 3 个来源、2 个独立域名
- 抽检 20 条 claim，人工支持率 ≥95%
- 不伪造 DOI/PMID/arXiv ID
- PDF 无溢出、无缺图、目录页码一致
- EPUB `epubcheck` 通过
- 同一来源集与 prompt 版本可复现

## 10. App 边界

Report 拥有：

```text
reports、sources、evidence、render jobs、templates、daily content
```

Report 使用 Core：

```text
items、blobs、tags、search、app host、backup
```

Report 不做：

- 执行 agent
- 项目管理
- 付费数据库
- 账号/计费
- 抓取付费墙全文

## 11. 阶段

| 阶段 | 目标 | 验收 |
|---|---|---|
| R0 | 来源 schema + 50–100 篇样本 | 元数据/OA/匹配核验 |
| R1 | 建库 + 查询/检索 | 3 个 query 产生去重、可解析来源 |
| R2 | 综合 + 证据等级 | 引用可回源；无未引用事实 |
| R3 | MD → PDF + EPUB | PDF 排版检查；`epubcheck` 通过 |
| R4 | 黄金任务 | PISA 报告 + 95 页量级手册通过 |
| R5 | 免费 Beta | 5 名技术用户；导出与来源审计通过 |

## 12. v0 非目标

- 付费全文数据库
- 自动下载所有付费 PDF
- 多人协作
- 实时新闻流
- 任意网页抓取
- 模型生成引用
