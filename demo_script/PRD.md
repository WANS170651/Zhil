# URL信息采集与入库系统技术实现文档

## 1. 项目背景

场景案例：在求职过程中，用户需要收集和整理大量招聘信息。传统方式依赖人工复制粘贴，效率低且容易出错。
本系统旨在通过 **自动化爬虫、智能解析（LLM）、动态适配 Notion 数据库 Schema、自动写入数据库** 的方式，构建一个高效、稳定、可扩展的 **“招聘信息采集 → 结构化解析 → 数据库存储”** 工作流。

---

## 2. 项目目标

* **自动化采集**：用户输入职位 URL，系统自动爬取网页内容。
* **动态 Schema 适配**：系统实时解析 Notion Database 字段定义，动态生成 LLM 输出规范。
* **结构化解析**：LLM 将原始网页内容抽取为符合 Notion Database 字段定义的 JSON。
* **幂等存储**：系统调用 Notion API 写入数据库，避免重复记录。
* **可扩展性**：支持未来扩展到多个数据库、多站点、多格式。

---

## 3. 系统范围

### 3.1 范围内

* 用户输入职位 URL
* 爬虫模块（Playwright）抓取并输出 Markdown/纯文本
* Schema 模块获取 Notion Database 字段定义
* LLM 模块抽取并生成符合 Schema 的 JSON
* Normalizer 校验和归一化 LLM 输出
* 调用 Notion API 写入数据
* 日志、错误处理与重试

### 3.2 范围外

* 批量全站爬取
* 招聘信息实时订阅/推送
* 前端管理界面

---

## 4. 系统架构

```
┌──────────────┐
│   User Input │  （职位URL）
└───────┬──────┘
        │
        ▼
┌──────────────┐
│   WebScraper │  （Playwright → Markdown/纯文本）
└───────┬──────┘
        │
        ▼
┌──────────────┐
│ NotionSchema │  （API 拉取 Database 字段定义）
└───────┬──────┘
        │
        ▼
┌──────────────┐
│     LLM      │  （Qwen via OpenAI SDK → 动态 JSON Schema）
└───────┬──────┘
        │
        ▼
┌──────────────┐
│ Normalizer   │  （校验 + 枚举映射 + 格式归一化）
└───────┬──────┘
        │
        ▼
┌──────────────┐
│ NotionWriter │  （Notion API → Database Upsert）
└──────────────┘
```

---

## 5. 功能模块

### 5.1 爬虫模块（`WebScraper`）

* **技术栈**：Playwright + html2text
* **功能**：

  * 加载网页（支持 JS 渲染）
  * 导出 HTML → Markdown/纯文本
  * 输出文本作为 LLM 输入

---

### 5.2 Notion Schema 模块（`NotionSchema`）

* **API**：`GET /v1/databases/{database_id}`
* **功能**：

  * 获取字段定义（name、type、options）
  * 识别支持的类型：`title`、`rich_text`、`select`、`multi_select`、`status`、`url`、`date`、`number`、`email`、`phone_number`、`checkbox`、`files`
* **缓存**：Schema 结果缓存 10\~60 分钟

---

### 5.3 LLM 抽取模块（`Extractor`）

* **技术栈**：OpenAI SDK（Qwen 模型，DashScope 兼容模式）
* **输入**：Markdown 文本 + URL + Notion Schema
* **输出**：符合 Notion Schema 的 JSON 对象
* **输出控制**：

  * 使用 `response_format={"type":"json_object"}` 或 **函数调用（function calling）**
  * 枚举字段（select/status/multi\_select）由 Schema 动态注入
  * Prompt 要求严格按 Schema 输出，不允许多余字段

---

### 5.4 Normalizer（归一化与校验）

* **功能**：

  * 将 LLM 输出 JSON **强制校验**为 Notion 可接收格式
  * **规则**：

    * `title`：必须非空
    * `select/status`：仅允许现有选项，失败时采用最近似匹配或置空
    * `multi_select`：数组中逐一校验
    * `date`：标准化为 ISO8601
    * `number`：强制 float/int
    * `url/email/phone`：正则校验，不合法置空
  * **输出**：Notion API 需要的 `properties` payload

---

### 5.5 NotionWriter（写库）

* **功能**：

  * 将归一化结果写入 Notion Database
  * 幂等策略：根据 URL 判断是否已存在

    * 已存在 → `PATCH` 更新
    * 不存在 → `POST` 新建

---

## 6. 接口设计

### 6.1 输入

```http
POST /ingest
Content-Type: application/json

{
  "url": "https://example.com/job/123",
  "database_id": "xxxxxxxxxxxx"
}
```

### 6.2 输出

```json
{
  "ok": true,
  "schema_version": "sha1:ab12cd...",
  "page_id": "xxxx",
  "data": {
    "Company": "快手",
    "Position": "数据分析师",
    "Location": "北京",
    "Industry": "互联网/科技",
    "URL": "https://example.com/job/123",
    "Status": "Applied",
    "Date": "2025-08-18"
  }
}
```

---

## 7. 环境与配置

### 7.1 依赖

```txt
playwright>=1.47.0
html2text>=2024.2.26
requests>=2.31.0
python-dotenv>=1.0.1
openai>=1.51.0
pydantic>=2.8.2
```

### 7.2 环境变量

```bash
DASHSCOPE_API_KEY=sk-xxx
NOTION_TOKEN=secret_xxx
NOTION_DATABASE_ID=xxx
NOTION_VERSION=2022-06-28
```

---

## 8. 非功能需求

* **性能**：单条处理 < 5 秒
* **可靠性**：LLM 输出必须通过 Schema 校验
* **安全性**：API Key 使用环境变量，不得硬编码
* **可观测性**：

  * 爬虫日志
  * LLM 请求耗时与 Token 使用
  * Notion API 响应状态码与失败重试

---

## 9. 错误处理与兜底策略

* **Schema 变更**：多余字段忽略，缺失必填字段报错或人工介入
* **枚举不匹配**：

  * `status`：严格匹配，失败置空并报警
  * `select/multi_select`：配置 `strict=true/false`，决定是否允许新增选项
* **异常**：网络/Notion API/LLM 调用失败 → 自动重试（指数退避）并记录日志

---

## 10. 流程时序

```
User → API / CLI
    → WebScraper.scrape_to_markdown()
    → NotionSchema.get_database_schema()
    → build_llm_schema_from_notion()
    → Extractor.llm_infer(scraped_text, schema)
    → Normalizer.validate_and_normalize()
    → NotionWriter.create_or_update_page()
    → 返回 page_id
```

---

## 11. 未来扩展

* **批量处理**：支持 URL 列表输入，结合消息队列（Celery/Redis/SQS）
* **更多存储**：支持 Airtable、Supabase、Postgres
* **前端界面**：可视化管理与筛选
* **通知提醒**：写入成功后推送到 Slack/邮件

---

## 12. 开发任务清单

1. **WebScraper**：爬虫模块（已完成 demo）
2. **NotionSchema**：动态获取并缓存 Notion Database Schema
3. **LLM Schema Builder**：由 Schema 生成 JSON Schema/函数调用参数
4. **Extractor**：基于动态 Schema 调用 LLM 并返回 JSON
5. **Normalizer**：强校验与 Notion payload 构造
6. **NotionWriter**：实现 Upsert（create/update）逻辑
7. **API Service**：封装为 FastAPI 服务，暴露 `/ingest`
8. **测试**：单元测试 + 端到端测试（真实网页 → Notion 记录）

---

📌 **总结**：
该系统通过 **爬虫 → 动态 Schema 解析 → LLM 抽取 → Normalizer → Notion 写库** 实现了灵活可扩展的职位信息自动入库。核心优势是 **动态适配 Notion Database 字段**，避免硬编码字段映射，保证在数据库字段变动时系统仍可稳定运行。