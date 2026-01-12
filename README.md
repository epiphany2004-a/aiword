## AI 单词助手（aiword）

一个基于 **FastAPI + MySQL** 的英语单词智能学习与复习系统，集成大模型能力，支持：

- **智能背单词**：从词书中按每日目标推送新词，自动生成音标、释义、谐音/词根助记与例句  
- **间隔复习（SRS）**：根据记忆程度自动安排复习时间，生成句子填空题  
- **学习统计与打卡**：连续学习天数、掌握单词量、学习效率曲线等可视化数据  
- **AI 作文批改**：上传或录入作文，由大模型给出分数、维度雷达图和逐点修改建议  

---

## 功能概览

- **用户系统**
  - 注册 / 登录、Session Cookie 维持登录状态（`/api/register`、`/api/login`、`/api/check-login`、`/api/logout`）
- **学习模块**
  - 从当前词书中按「每日新词目标」分配待学单词：`GET /api/start-task`
  - 每个单词由大模型生成结构化解释，前端展示音标、中文释义、谐音、词根词缀、例句
  - 学习进度上报：`POST /api/save-progress`（不认识 / 不确定 / 认识），驱动 SRS 调度
- **复习模块**
  - 获取今日应复习单词及复习句子：`GET /api/review_words`
  - 对于缺少复习句子的单词，通过 DeepSeek 生成句子填空题并入库缓存
  - 复习进度上报：`POST /api/review/progress`
- **学习统计**
  - `/api/learning-logs`、`/api/learning-stats`、`/api/learning-stats/chart` 提供首页看板和图表数据
- **AI 作文批改**
  - 使用 DeepSeek 对作文进行打分和多维度分析（见 `api/agent.py` 中 `deepseek_agent_get_essay_structure`）
- **前端界面**
  - `static/html/login.html`：登录 / 注册
  - `static/html/index.html`：首页看板、开始学习 / 复习、学习设置、词书选择、AI 作文入口
  - `static/html/learning.html`：单词学习页（AI 助记与例句）
  - `static/html/review.html`：句子填空复习页
  - `static/html/writing.html`：AI 作文批改页

---

## 技术栈

- **后端**
  - Python 3.9
  - FastAPI、Uvicorn
  - SQLAlchemy 2.x
  - MySQL 8.0
- **AI / 第三方**
  - `openai` 客户端（通过代理服务调用 Gemini 模型）
  - `google-genai`（Gemini OCR）
  - DeepSeek API（单词解释与句子填空 / 作文批改）
- **前端**
  - 纯 HTML + CSS + 原生 JS
  - Chart.js（学习数据可视化）

---

## 目录结构（简要）

```text
aiword/
  main.py                 # FastAPI 入口，挂载路由与静态文件
  api/                    # 业务接口
    login.py              # 注册、登录、会话管理
    setting.py            # 学习设置、词书选择
    learning.py           # 开始学习任务、保存学习进度
    review.py             # 复习任务与复习进度
    score.py              # 作文评分相关接口
    get_log.py            # 学习日志 / 统计
    agent.py              # 调用 Gemini / DeepSeek / Gemini OCR 的封装
  models/                 # SQLAlchemy ORM 模型
  db/
    database.py           # 数据库引擎与 Session
  static/
    html/                 # 页面模板（登录、首页、学习、复习、作文等）
    css/                  # 对应页面样式
  aiword_db.sql           # 初始化数据库数据（词书、单词等）
  init_db.py              # 启动前自动建表并导入 SQL
  Dockerfile
  docker-compose.yml
  requirements.txt
  start.sh                # 容器启动脚本：初始化数据库 + 启动 Uvicorn
```

---

## 环境要求

- Python **3.9**（建议使用虚拟环境）
- MySQL **8.0+**
- 已获取可用的：
  - DeepSeek API Key
  - Gemini / OpenAI 兼容 API Key（视你的实际服务商而定）
  - Google Gemini API Key（用于 OCR，可选）

> **安全提示**：当前仓库中的 `api/agent.py` 包含示例用的明文 API Key，**实际部署前务必替换为你自己的 Key，并改为从环境变量加载，避免泄露。**

---

## 本地运行（不使用 Docker）

1. **克隆项目并进入目录**

   ```bash
   git clone <your-repo-url>
   cd aiword
   ```

2. **创建虚拟环境并安装依赖**

   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows PowerShell
   # 或 source venv/bin/activate # macOS / Linux

   pip install -r requirements.txt
   ```

3. **准备 MySQL 数据库**

   - 创建数据库：

     ```sql
     CREATE DATABASE aiword_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     ```

   - 手动导入 `aiword_db.sql` **或** 直接使用项目提供的初始化脚本（推荐）：

     ```bash
     # 确保 db/database.py 中的连接配置指向你的本地 MySQL
     python init_db.py
     ```

4. **配置环境变量（可选，但推荐）**

   在你的终端 / 系统中设置：

   - 数据库相关（如未设置则采用默认值：`root` / `Tang0312@` / `localhost` / `3306` / `aiword_db`）

     ```bash
     set DB_USER=your_user
     set DB_PASSWORD=your_password
     set DB_HOST=localhost
     set DB_PORT=3306
     set DB_NAME=aiword_db
     ```

   - AI Key（建议你修改 `api/agent.py`，从环境变量读取，例如 `DEEPSEEK_API_KEY`、`GEMINI_API_KEY` 等）。

5. **启动后端服务**

   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

6. **访问前端页面**

   - 登录页（默认）：`http://127.0.0.1:8000/`
   - 首页：`http://127.0.0.1:8000/index`

---

## 使用 Docker 一键启动（推荐）

本项目已提供 `Dockerfile` 与 `docker-compose.yml`，可一键拉起 **应用 + MySQL**。

1. **如果需要，自行修改 docker-compose 中默认数据库密码**

   ```yaml
   # docker-compose.yml 中的环境变量
   DB_USER: root
   DB_PASSWORD: Tang0312@
   DB_HOST: db
   DB_PORT: "3306"
   DB_NAME: aiword_db
   ```

   如修改，请保持：

   - `docker-compose.yml` 的 `app` 和 `db` 两个 service 中的密码一致
   - `.env` / 部署环境中的变量与之对应

2. **构建并启动**

   ```bash
   docker-compose up -d --build
   ```

   - 应用容器：`aiword-app`，监听 `8000` 端口（宿主机映射为 `8000:8000`）
   - 数据库容器：`aiword-db`，MySQL 端口映射为 `3307:3306`

3. **首次启动时**

   - `start.sh` 会自动调用 `init_db.py`：
     - 等待 MySQL 就绪
     - 检查是否已有表和数据
     - 若没有，则依据 `aiword_db.sql` 初始化表结构与基础数据

4. **访问服务**

   - 浏览器打开：`http://localhost:8000/`

5. **停止服务**

   ```bash
   docker-compose down
   ```

---

## 配置说明（关键点）

- **数据库配置**
  - 来自环境变量：`DB_USER`、`DB_PASSWORD`、`DB_HOST`、`DB_PORT`、`DB_NAME`
  - 初始化逻辑见：`init_db.py`
- **AI Key / 模型**
  - `api/agent.py` 中目前用的是写死的 Key 和代理地址，实际使用时建议：
    - 将 Key 换成你自己的
    - 改为从环境变量读取
    - 如需使用不同模型，可调整：
      - `ChatAgent.model`
      - 调用的 `base_url`
- **静态资源**
  - `main.py` 中：
    - `/` → `static/html/login.html`
    - `/index` → `static/html/index.html`
    - `/register` → `static/html/register.html`
    - `/static/*` → `static/` 目录（CSS、图片等）

---

## 常见问题

- **Q：第一次启动报数据库连接失败怎么办？**  
  **A**：确认 MySQL 已启动且账号密码正确；若使用 Docker，请等 `aiword-db` 完全健康后，`aiword-app` 会自动重试连接。

- **Q：AI 相关功能一直报错？**  
  **A**：检查 `api/agent.py` 中的 API Key 是否有效、调用的 base_url 是否可达，或将相关 Key 改为从环境变量读取并正确设置。

- **Q：能否只用本地数据库、不用 Docker？**  
  **A**：可以，只需按照「本地运行」部分配置好本机 MySQL，并运行 `init_db.py` 即可。

---

## 开发建议

- 将所有敏感信息（数据库密码、API Key）迁移到环境变量或 `.env` 文件中，不要直接写入代码仓库。  
- 新增接口时，在 `main.py` 中通过 `app.include_router` 挂载到统一的 `/api` 前缀下，保持前后端路由风格一致。  
- 如需扩展更多 AI 能力（如听力、口语打分等），建议在 `api/agent.py` 中增加相应封装函数，并在 `api/` 下新增对应路由模块。

