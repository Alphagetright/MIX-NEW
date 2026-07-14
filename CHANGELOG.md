# 项目变更日志

> 自动记录代码变更。由 change-log skill 维护。
> 格式: 时间 | 文件 | 操作 | 位置 | 说明

## 2026-07-14

| 时间 | 文件 | 操作 | 位置 | 说明 |
|------|------|------|------|------|
| 21:00 | index.html | 新建 | 根目录 | 技术作品集单页：Hero+4项目+技能+About，深色工程师风 |
| 21:00 | README.md | 新建 | 根目录 | 项目README：三系统概览+技术要点+数据规模 |
| 21:15 | index.html | 重写 | 根目录 | 全文中文化：项目描述/技能/About 转中文 |
| 21:15 | README.md | 重写 | 根目录 | 中文版README |
| 21:30 | repo | 公开 | GitHub | 仓库 private→public |
| 21:30 | Pages | 启用 | GitHub | GitHub Pages main/root 部署 |
| 21:45 | .gitignore | 新建 | 根目录 | 排除users.json/state.db/pycache/exports/杂项/chapters |
| 21:45 | 敏感文件 | 移除 | 全仓库 | 删除 users.json、state.db、41个pycache、exports、settings.local.json |
| 22:00 | index.html | 修改 | About | 软著"已获得"→"已申请" |
| 22:00 | index.html | 修改 | About | 新增数据量级+技术深度段 |
| 22:00 | index.html | 修改 | 项目2/3 | Poem Lab截图→docs/screenshots/；TangCLI截图→clii/cli_ops/screenshots/ |
| 22:30 | index.html | 重构 | 全页 | 招聘导向优化：4个项目各加Role badge/Workflow数据流/Results列表 |
| 22:30 | README.md | 重构 | 全页 | 新增Architecture/Features/Results结构 |
| 22:30 | index.html | 修改 | Hero | 强化"在校·可实习·独立交付"定位 |
| 23:00 | 分析系统/docs/screenshots/ | 追踪 | docs | Force-add Poem Lab真实5步流水线截图（被inner .gitignore屏蔽） |
| 23:30 | clii/capture_ss.py | 新建 | clii/ | TangCLI截图自动生成脚本：跑真实CLI命令→Pillow渲染PNG |
| 23:30 | clii/cli_ops/screenshots/ | 覆写 | clii/ | 10张CLI截图全部重新生成（当前迭代版本） |

### 战略成果
- **作品集上线**：https://alphagetright.github.io/MIX-NEW/ ，BOSS直聘可直接贴链接
- **隐私保护**：密码哈希/用户数据/会话记录/个人思考全部排除
- **招聘适配**：Role badge消除"这东西是不是你做的"信任疑虑；Workflow让技术面试官10秒看懂架构
- **可持续维护**：capture_ss.py 一次写好，CLI迭代后跑一下即可更新截图

## 2026-07-06

| 时间 | 文件 | 操作 | 位置 | 说明 |
|------|------|------|------|------|
| 21:46 | ~/.claude/skills/project-memory.md | 新建 | — | 四阶段代码解析 skill，生成 .claude/memory/ |
| 21:47 | ~/.claude/skills/change-log.md | 新建 | — | 项目+思考双轨迭代引擎 skill |
| 21:47 | ~/.claude/skills/launcher.md | 新建 | — | 总入口 skill，意图识别+路由+会话恢复 |
| 21:47 | ~/.claude/CLAUDE.md | 新建 | — | 全局配置：skills系统+项目记忆+协作偏好 |
| 21:48 | ~/.claude/settings.json | 修改 | — | 添加 PostToolUse + Stop hooks |
| 21:53 | .claude/memory/overview.md | 新建 | — | 项目全景：三子系统架构+技术栈+数据流 |
| 21:56 | .claude/memory/modules/clii.md | 新建 | — | clii 模块深度分析：28模块+三层架构 |
| 21:57 | .claude/memory/modules/analysis-system.md | 新建 | — | 分析系统模块分析：格律/统计/Web三线 |
| 21:59 | .claude/memory/coupling.md | 新建 | — | 耦合关系图+影响地图+改动清单 |
| 22:00 | .claude/memory/conventions.md | 新建 | — | 编码规范提取 |
| 22:00 | .claude/session.md | 新建 | — | 会话快照机制 |
| 22:18 | .claude/memory/thoughts.md | 新建 | — | 思考日志：4条战略思考记录 |
| 22:22 | ~/.claude/skills/change-log.md | 覆写 | — | 升级为双轨迭代引擎（代码+思考并行） |
| 22:32 | .claude/session.md | 覆写 | — | 更新会话快照至完成状态 |
| 22:37 | ~/.claude/local-plugins/ | 新建 | — | 本地插件市场：9个skill转标准插件，3个插件组 |
| 22:37 | ~/.claude/settings.json | 修改 | — | 注册 extraKnownMarketplaces + 启用本地插件 |
| 22:38 | ~/.claude/plugins/known_marketplaces.json | 修改 | — | 注册 local-toolkit 市场 |
