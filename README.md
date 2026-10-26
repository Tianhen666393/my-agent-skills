# my-agent-skills

个人 AI Agent 技能仓库（Agent Skills），适用于 Codex、Antigravity (Gemini CLI)、Claude Code、CC Switch 等多 Agent 环境。

## 技能列表 (Skills)

| 技能名称 | 目录 | 简要说明 |
| :--- | :--- | :--- |
| **article-to-pdf** | [`skills/article-to-pdf`](skills/article-to-pdf) | 将网页教程文章（微信公众号、CSDN 等）转为含原文排版、高清截图和页码的离线 A4 PDF，支持去广告、步聚防跨页断裂及索引自动维护。 |
| **ai-tool-ledger** | [`skills/ai-tool-ledger`](skills/ai-tool-ledger) | 维护跨 Agent 共用的 AI 工具安装台账（Excel），支持组件安装自检与核实、集中备份（.agent_backups）与过期自动归档（.agent_trash）。 |

---

## 目录结构规范

本仓库遵循标准 Agent Skill 仓库结构，支持通过 CC Switch 仓库源一键添加与同步：

```text
my-agent-skills/
├── README.md
└── skills/
    └── <skill-name>/
        ├── SKILL.md                  # 核心技能说明与触发规范
        ├── assets/                   # 样式表、静态资源
        ├── references/               # 参考备忘、平台适配笔记
        └── scripts/                  # 辅助执行脚本与工具
```

## 在 CC Switch 中使用

1. 打开 CC Switch 客户端，进入 **技能 (Skills)** 页面。
2. 在 **技能源 (Skill Repos)** 中添加本仓库：`Tianhen666393/my-agent-skills`（分支：`main`）。
3. 发现并安装技能后，一键分发至所需的 Agent（Codex、Antigravity、Claude 等）。
4. 后续更新技能后，在 CC Switch 点击 **“检测更新”** 即可全量同步。
