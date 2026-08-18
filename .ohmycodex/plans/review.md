Status: complete
Owner: Jerry Wu
Updated: 2026-08-13

# DeepSee 全应用复审

## 审查范围

- 核心库与 FastAPI 网关: `/Users/jerrywu/Documents/DeepSee`
- React Web/Desktop 原型: `/Users/jerrywu/Documents/DeepSee-Desktop/frontend`
- 当前网关、完整消息历史与 Desktop reliability 规格
- 当前未提交工作树，包括鉴权、限流、追踪、HTTP bridge、图片附件与前端可靠性改动

本次只修改本审查记录，没有修改应用源码，也没有调用真实付费上游 API。

## 发布结论

**No-go，暂不应把当前产物声明为完整 DeepSee Desktop 应用。**

核心库和网关已从上次的不可集成状态明显推进到可测试的预发布状态；React 网站也已经真实接入本地 HTTP 网关。但仍有多个 P1 契约缺陷，且 Tauri 主进程、Codewhale、服务进程托管、原生配置/密钥存储和桌面打包尚未实现。

## Standards 轴

### P1: 畸形请求会消耗限流额度并抢占并发槽

证据: `deepsee_server/app.py:141` 在 JSON 与协议校验前调用 `RequestGuard.acquire()`。实测第一条非法 JSON 返回 400 后，同身份下一条合法请求在 `rate_limit=1` 时返回 429；并发槽已满时，非法 JSON 返回 503，而不是自身应有的 400。

后果: 已认证调用方可用低成本畸形请求耗尽其他合法请求的额度或队列，违反网关设计“普通 4xx 不占推理并发名额”。

最小修复: 保留鉴权在解析前执行，但把 guard 获取移动到各推理端点完成请求校验之后、首次调用视觉或 DeepSeek 上游之前。

### P1: OpenAI 字符成本上限可由工具字段绕过

证据: `deepsee_server/request_limits.py:71` 只统计 message content 中的 text；`tools[].function.description`、历史 `tool_calls[].function.arguments` 等原样透传字段没有计入。实测 200,001 字符的工具描述通过验证。

后果: 请求仍可在 32 MiB 请求体范围内制造远高于文档所述 20 万字符的上游 prompt 成本。

最小修复: 对所有允许透传并参与上游 prompt 的字符串字段做结构化累计，继续保留消息、图片与输出 token 的独立限制。

### P1: 流式上游错误没有写入请求追踪

证据: `deepsee_server/protocols/openai.py:216` 把 `ComposeError` 编码为 SSE error chunk 后吞掉异常；`deepsee_server/app.py:204` 的 trace 最终记录 `status=200, error_type=None`。实测响应包含 `upstream_error`，管理 trace 却显示无错误。

后果: 请求日志和错误率会把失败流量统计为成功，线上问题难以诊断。

最小修复: 流编码器在发送错误 chunk 前通知 trace context，或让应用层统一捕获并标记流式失败。

### P2: 源码包夹带内部审查和开发文件

证据: `pyproject.toml:26` 只配置 wheel packages，没有约束 sdist。当前 616 KiB sdist 包含 `.ohmycodex/plans/review.md`、team-run 记录、全部测试、流程图脚本和大量实施规格。

最小修复: 为 sdist 明确 include/exclude；保留发布需要的 README、许可证和必要源码，排除内部审查、测试缓存和生成工具。

## Spec / Application 轴

### P1: “检查连接”会清空会话和当前页 API key

证据: `frontend/src/features/api/ServiceOverview.tsx:46` 直接执行 `window.location.reload()`。浏览器实测创建会话后点击该按钮，重载后会话消失。会话与 public/admin key 都仅驻留内存，因此 key 也同时丢失。

后果: 一个看似只读的诊断动作会造成未持久化用户数据丢失，并使后续认证请求失败。

最小修复: 新增 `refreshConnection()`，只调用 `getServiceStatus()` 并递增 connection revision，禁止刷新整个页面。

### P1: 设置 Sheet 不是完整模态层

证据: `frontend/src/features/api/SettingsSheet.tsx:23` 只把 ModelRouting 内的兄弟节点设为 inert；标题栏和 API 工具栏仍可聚焦/点击。`frontend/src/styles.css:1177` 的 Sheet z-index 为 24，低于标题栏的 30。浏览器实测标题栏 `inert=false` 且位于 Sheet 之上。

后果: Tab trap 可被外层控件绕过，用户可在对话框打开时切换页面或触发操作，不符合批准的可访问模态规格。

最小修复: 把模态层提升到 AppShell 根级 portal，统一 inert 页面内容，并让遮罩层高于所有应用 chrome；增加键盘和背景交互测试。

### P1: 设置保存后的连接失败状态不符合规格

证据: `frontend/src/state/AppStateContext.tsx:201` 保存设置后没有捕获 status refresh 失败；`frontend/src/bridge/HttpDesktopBridge.ts:179` 又把网络异常映射为 `stopped`。规格要求保留新设置并把状态设为 `error`。

后果: UI 会把刷新失败误报成“服务已停止”或“设置保存失败”，无法区分不可达、服务停止与保存失败。

最小修复: 分离保存错误和刷新错误；保存成功后立即保留设置与 revision，刷新异常统一落到 `serviceStatus="error"`。

### P1: 损坏的 API key 文件导致受保护路由裸 500

证据: `deepsee_server/auth.py:43` 直接 `json.loads()`，未映射 JSON、读取或 schema 错误。实测损坏的 key 文件使 `/v1/models` 返回 `500 Internal Server Error`。

后果: 单个配置文件损坏会让整个网关失去可用性且没有可操作的结构化错误，也缺少对应回归测试。

最小修复: 在启动时验证 key-store schema并 fail closed；运行期把存储错误映射为 503 `configuration_error`，日志记录文件位置但不记录 key 内容。

### P2: 陈旧会话 ID 没有按规格忽略

证据: `frontend/src/state/AppStateContext.tsx:170` 无条件写入传入 ID。传入已删除或过期 ID 会让当前会话变成空白，违反“stale ids silently ignored”。

最小修复: 更新前先确认 ID 存在；不存在时保持当前选择不变，并补一条 focused test。

### P2: Desktop 安装与状态文档已经过时

证据: `DeepSee-Desktop/README.md:6` 和 `docs/GUI-DEV-HANDOFF.md:21` 仍写 `pip install deepsee[server]`，但实际发布名是 `seedeep`；README:27 还称当前不会访问 8712，而生产前端已使用 `HttpDesktopBridge` 访问本地网关。

后果: 用户可能安装 PyPI 上无关的 `deepsee` 项目，并误判当前集成能力。

最小修复: 全部改为 `pip install "seedeep[server]"`，并把产品状态更新为“React 网站 + HTTP bridge”，明确尚非 Tauri Desktop。

## 已确认修复与正向证据

- 核心网关已有 fail-closed public/admin 鉴权、摘要密钥存储、loopback-only `--no-auth`、限速、并发租约、请求体/图片/token 上限和静态站点托管。
- OpenAI 入口已支持完整消息历史、工具字段、生成参数、原始响应、视觉上下文替换与流式资源关闭。
- Desktop 已有真实 `HttpDesktopBridge`、完整历史、图片附件、工具调用增量、流结束校验、会话回访和定向重新生成。
- 浏览器检查在 1440x900、1024x768、820x900 下没有页面级横向溢出；Sheet 的基本 Escape、焦点恢复和末尾 Tab 回绕可工作。

## 验证证据

- 核心 Python 3.13: `395 passed, 2 skipped`
- 项目 `.venv` Python 3.10: `397 passed`
- `compileall`、`uv lock --check`、核心 `git diff --check`: 通过
- Desktop: `8 files / 28 tests passed`
- Desktop `pnpm lint`、`pnpm build`、`git diff --check`: 通过
- 浏览器: 首屏/API 页面、三种视口、设置 Sheet、检查连接数据丢失均已实际复核

## 未实现但已明确延期的能力

- Tauri 2 / Rust 主进程与原生桌面打包
- Codewhale `exec`、sessions/resume 集成
- DeepSee 服务进程启动、停止与生命周期托管
- `deepsee.toml` 原生读写和系统钥匙串
- 会话跨应用重启持久化

这些不是当前 frontend-only reliability 规格的回归，但在完成前，产品只能称为 Web 前端原型或本地网关控制台，不能称为完整桌面应用。

## 剩余验证风险

- 未使用真实 DeepSeek/VLM key 做付费端到端冒烟。
- 未做慢速请求、大量工具定义、真实客户端断连和多 worker 压测。
- 没有跨两个仓库启动真实网关后执行的自动化浏览器 E2E。
- 仓库仍缺 CI、依赖安全扫描和发布包内容门禁。
