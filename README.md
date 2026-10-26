# my-agent-skills

个人 AI Agent 技能仓库（Agent Skills），适用于 Codex、Antigravity (Gemini CLI)、Claude Code、CC Switch 等多 Agent 环境。

## 技能列表 (Skills)

### 一、 个人自研与深度定制技能 (Personal & Dedicated)

| 技能名称 | 目录 | 简要说明 |
| :--- | :--- | :--- |
| **file-backup-cleanup** | [`skills/file-backup-cleanup`](skills/file-backup-cleanup) | 本机全局文件安全删除（同盘日期回收站 `.agent_trash`）、操作分级授权（A/B/C 级）与工作备份集中管理（`.agent_backups` 及中文备份说明）核心安全规范。 |
| **article-to-pdf** | [`skills/article-to-pdf`](skills/article-to-pdf) | 将网页教程文章（微信公众号、CSDN 等）转为含原文排版、高清截图和页码的离线 A4 PDF，支持去广告、步聚防跨页断裂及索引自动维护。 |
| **ai-tool-ledger** | [`skills/ai-tool-ledger`](skills/ai-tool-ledger) | 维护跨 Agent 共用的 AI 工具安装台账（Excel），支持组件安装自检与核实、集中备份（`.agent_backups`）与过期自动归档（`.agent_trash`）。 |
| **baidu-netdisk-organize** | [`skills/baidu-netdisk-organize`](skills/baidu-netdisk-organize) | 百度网盘自动化分类整理：按文档/音频/截图/拍照/视频等固定桶分流、本地 OCR 与 CLIP 隐私隔离、待确认清单生成与服务端安全移动。 |
| **github-open-source-discovery** | [`skills/github-open-source-discovery`](skills/github-open-source-discovery) | 按触发词持续检索、核验并增量收录 GitHub 开源项目，包含“检索与推荐底线”、电赛与电子信息专项跟踪及到期项目定期复核机制。 |
| **markdown-technical-writing** | [`skills/markdown-technical-writing`](skills/markdown-technical-writing) | Markdown 技术文档规范：规范数值、物理量与常用单位书写，约束 LaTeX 公式排版与显示数学语法，确保 MathJax/KaTeX 跨平台渲染兼容。 |
| **adversarial-doc-reviewer** | [`skills/adversarial-doc-reviewer`](skills/adversarial-doc-reviewer) | 学术论文与敏感方案红军对抗评审：模拟苛刻审稿人或对立视角挖掘逻辑漏洞与事实防御薄弱点，并在严格保全实验数据与事实前提下进行抗辩强化改写。 |

---

### 二、 社区开源精选与本地深度定制技能 (Curated & Customized Upstream)

以下技能衍生自开源社区优秀项目，日常由天痕根据个人多 Agent 规范进行本地路径修正、防幻觉加固与环境适配。出处及官方最新动态请见上游原仓库：

| 技能名称 | 目录 | 上游开源项目 (Upstream) | 简要说明与本地维护说明 |
| :--- | :--- | :--- | :--- |
| **find-skills** | [`skills/find-skills`](skills/find-skills) | [`vercel-labs/skills`](https://github.com/vercel-labs/skills)<br>*(by Vercel Labs)* | 查找、核实、介绍和比较开源 Agent Skills 生态技能。**天痕深度定制增强版**：中文本土化、防幻觉强制核验 skills.sh 详情页功能、标注动态查询日期，并严格执行未授权禁止私自安装安全门禁。 |
| **brainstorming** | [`skills/brainstorming`](skills/brainstorming) | [`obra/superpowers`](https://github.com/obra/superpowers)<br>*(by @obra)* | 协作式头脑风暴与架构设计：探索意图与约束、设计门禁把控、产出规范设计文档。本地版本修复了 `docs/specs/` 路径硬编码与断链依赖。 |
| **opencli-browser** | [`skills/opencli-browser`](skills/opencli-browser) | [`jackwener/OpenCLI`](https://github.com/jackwener/OpenCLI)<br>*(by Jack Wener)* | 驱动真实 Chrome 窗口执行网页交互：提供选择器优先目标契约、复合表单控件识别、DOM 指纹防漂移、网络请求捕获与可机读结构化信封。 |
| **opencli-usage** | [`skills/opencli-usage`](skills/opencli-usage) | [`jackwener/OpenCLI`](https://github.com/jackwener/OpenCLI)<br>*(by Jack Wener)* | OpenCLI 工具体系总入口与使用指南：提供全平台适配器发现、无头/有头浏览器桥接诊断、多格式输出与桌面应用 CDP 驱动规范。 |

---

## 目录结构规范

本仓库遵循标准 Agent Skill 仓库结构，支持通过各类技能管理工具（如 CC Switch、Magpie 等）或 Git 机制在各应用间无缝同步：

```text
my-agent-skills/
├── README.md
└── skills/
    └── <skill-name>/
        ├── SKILL.md                  # 核心技能说明与触发规范
        ├── agents/                   # Agent 界面与元数据配置 (openai.yaml 等)
        ├── assets/                   # 样式表、静态资源
        ├── references/               # 参考备忘、平台适配笔记
        └── scripts/                  # 辅助执行脚本与工具
```

## 在技能管理工具（如 CC Switch）中使用

1. 打开管理工具，进入 **技能 (Skills) ➔ 技能仓库管理**；
2. 添加本仓库：`Tianhen666393/my-agent-skills`（分支：`main`）；
3. 一键分发至所需的 Agent（Codex、Antigravity、Claude 等）；
4. 本地仓库执行 `git push` 更新后，在客户端点击 **“检测更新”** 即可一键全平台同步生效。
