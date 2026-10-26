---
name: ai-tool-ledger
description: 维护跨 Agent 共用的 AI 工具安装台账。安装、配置或卸载工具、skill、插件后登记记录，采用单一真理源（SSOT）架构管理共用组件，支持多应用联合登记与双重路径自检。
---

# AI 工具台账

台账默认位于当前用户的真实文档目录下 `my-pc-ledger/AI工具安装清单.xlsx`（兼容历史 `AI工具台账/` 路径）。Windows 通过系统 MyDocuments 获取，支持文档目录重定向；Linux 优先使用 XDG 文档目录，其他情况使用用户主目录下的 Documents。`--workbook` 可覆盖此位置；不得写死用户名。
固定脚本：本技能的 `scripts/ledger.mjs`。规则和脚本留在技能目录，新增备份统一放在台账源盘的 `.agent_backups`，不再写入文档目录的 `backups/`。既有旧备份另行获准后迁移。
详细字段、分类和格式见 [references/schema.md](references/schema.md)，登记前读取。

## 单一真理源（SSOT）与自检边界

- **单一资产主体**：用户下载或创建、按共用方式管理的 Skill 与插件统一记录于《共用Skill与插件》工作表。严格采用“一物一行”原则，绝对地址指向 Git 源码仓库（`my-agent-skills\skills\<name>`）或 CC Switch 托管源（`.cc-switch\skills\<name>`），不得按不同 Agent 拆成多行。
- **多应用联合标注**：`apps`（适用应用 / 核实范围）以分号分隔各应用状态（如 `Codex (已同步生效)；Antigravity (已同步生效)`）。各 Agent 仅更新或追加属于自己的核验标记，严禁覆盖其他应用的有效信息。
- **双重自检核验（Double Verification）**：
  - 核查 1（源头）：核验单一真理源路径下的 `SKILL.md` frontmatter 身份是否正确。
  - 核查 2（生效态）：探针检测当前 Agent 专属运行时目录（Antigravity 为 `.gemini\config\skills\<name>`，Codex 为 `.codex\skills\<name>`）是否已同步就绪。
  - 两者均具备方可标记为“已同步生效”，防止源头存在但运行时缺失的假在线隐患。
- **应用自带表边界**：当前应用内部私有管理或内置组件放入“应用名自带”工作表（如 `Antigravity自带`、`Codex自带`）。各 Agent 仅维护自己的自带表，不扫描其他 Agent。
- **共用工具**：整机开发环境、第三方命令行工具等放“共用工具”表，同样遵循单一行原则与多应用适配标注。

## 登记与核实流程

1. **沿用会话已有授权**：自检和预览可直接执行；新增、修改、移除台账记录遵守用户的写入确认规则。台账维护不授权安装、卸载、外部发送或发布。
2. **实际核实路径**：skill 读取真理源 `SKILL.md`，核对 frontmatter 名称及用途；插件读取对应清单或入口。同时探针检测当前应用运行时生效副本。
3. **中文用途说明**：说明能做什么、适用任务。安装细节、历史路径和测试限制放“安装备注”。版本没有证据时写“未提供”。
4. **生成请求与预览**：创建请求 JSON，先用固定脚本预览核查，再带 `--apply` 写入。
5. **集中备份与归档铁律**：写入前自动备份 Excel 至源盘 `.agent_backups/YYYY-MM-DD/AI工具台账-路径标识/唯一备份目录/`，同时生成中文 `备份说明.md` 和 `backup.json`。写入成功后，自动将超过 30 天的已识别旧备份安全移入同盘 `.agent_trash/当天日期/`，绝不物理删除。
6. **回读校验**：保存后重新加载 Excel，核对名称、用途、分类和记录数，保证数据零丢失。

## 固定脚本使用

使用当前应用已有的 Node 和 `@oai/artifact-tool`，不自动安装依赖，通过 `--dependency-root` 加载运行时。

```text
node scripts/ledger.mjs inspect --agent Antigravity
node scripts/ledger.mjs check --agent Antigravity
node scripts/ledger.mjs init --agent Antigravity --apply
node scripts/ledger.mjs upsert --agent Antigravity --request work/entry.json
node scripts/ledger.mjs upsert --agent Antigravity --request work/entry.json --apply
node scripts/ledger.mjs consolidate --agent Antigravity
node scripts/ledger.mjs consolidate --agent Antigravity --apply
node scripts/ledger.mjs remove --agent Antigravity --request work/exact-entry.json --apply
```

- `--workbook` 可指定测试副本；`--preview-dir` 输出工作目录中的核查截图。
- `consolidate` 指令：用于将既有台账中因旧版规则产生的重复记录自动合并为单一真理源标准行，合并历史备注与各应用状态。

## 跨应用分发与协同规范

### 1. 分发机制与权限
- 本技能统一由个人技能仓库 `Tianhen666393/my-agent-skills` 维护，通过 CC Switch 或 Git 跨应用分发。
- 各 Agent 统一遵循 `AGENTS.md` 全局规范按名称调用，不依赖私有绝对路径。

### 2. 写入与合并机制
- 《共用Skill与插件》中以 `name` + `kind` 为唯一键，既有记录自动执行 `apps` 追加与备注合并，确保全表整洁不重复。
- 自带表完全私有隔离。
