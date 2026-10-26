---
name: pc-app-ledger
description: 维护个人电脑（如天选 5 Pro 笔记本、台式机）的本机应用软件安装台账。支持初次智能扫描勘察已安装应用、日常增量登记、路径有效性巡检及一键同步至私有 GitHub 仓库。当用户要求“登记应用”、“应用台账”、“扫描已安装软件”、“更新软件清单”或记录软件安装路径时使用。
---

# 本机应用安装台账 (PC App Ledger)

台账默认位于当前用户文档目录下的 `my-pc-ledger/` 仓库中，按设备分文件维护：
* 当前笔记本：`应用安装清单-天选5pro.xlsx`
* 未来台式机：`应用安装清单-台式机.xlsx`
* 详细字段定义见 [references/schema.md](references/schema.md)。

## 核心工作流

```text
初次使用 (全机智能勘察) ──> 审阅候选清单 ──> 批量生成初始底账
日常使用 (按需增量登记) ──> 装了新软件 ──> Agent 单条追加更新 ──> 一键云端同步
定期维护 (健康路径巡检) ──> 检查失效死链 ──> 标记或清理已卸载项
```

### 1. 初次激活：全机智能勘察 (Survey)
初次为一台新设备建立应用台账时，调用扫描脚本提取候选清单，免去手动输入之苦：

```powershell
python scripts/survey.py
```
* **功能**：自动遍历 32/64 位 Windows 注册表已安装项、常见自定义盘符（如 `T:\APP`、`T:\Electronic`），自动过滤补丁、运行库与系统组件，输出清晰的候选软件名称、版本与安装路径。
* **流程**：将扫描结果展示给用户确认，剔除不需要记录的琐碎项后，批量录入台账。

### 2. 日常使用：按需增量登记 (Upsert)
日常装了新软件（如 EDA 仿真工具、编程环境、专业驱动）后，执行单条或少量追加：

```powershell
# 1. 预览登记
python scripts/app_ledger.py upsert --device 天选5pro --request work/app_entry.json

# 2. 写入生效（写入前自动生成安全备份）
python scripts/app_ledger.py upsert --device 天选5pro --request work/app_entry.json --apply
```

* **请求格式 (`work/app_entry.json`)**：
```json
{
  "entries": [
    {
      "name": "Altium Designer",
      "category": "专业EDA与电路设计",
      "purpose": "EDA电路原理图与PCB设计",
      "version": "26.0.0.14",
      "path": "T:\\Electronic\\AD2026\\X2.EXE",
      "notes": "已配置本地元件库；工程库位于 T:\\Electronic\\AD_lib"
    }
  ]
}
```
* **自动规则**：
  * 若同名软件已存在：就地更新版本、路径与备注；
  * 若为新软件：自动追加到末尾，并重新计算排序递增 `序号`。

### 3. 健康巡检：路径有效性检查 (Check)
随时检查台账中记录的绝对路径是否存在：

```powershell
python scripts/app_ledger.py check --device 天选5pro
```
* 自动检测所有路径是否在磁盘上依然存活，标记 `已核实有效` 或 `路径不存在/失效`。

### 4. 移除软件记录 (Remove)

```powershell
python scripts/app_ledger.py remove --device 天选5pro --name "旧软件名称" --apply
```
* 移除后自动重排剩余软件的 `序号`，保持 1..N 连续。

### 5. 一键云端同步 (Sync)
登记或更新后，自动刷新在线看板：

```powershell
python scripts/app_ledger.py sync
```
* 重新读取 Excel，刷新 `my-pc-ledger/README.md` 中的 Markdown 表格。
* 用户可在目录中双击 `一键同步.bat` 直接一键推送到私有 GitHub 仓库。

## 安全与集中备份规范

每次写操作（`upsert --apply` 或 `remove --apply`）前，脚本严格遵守 `file-backup-cleanup` 规范，在源盘根目录生成独立工作备份：
`C:\.agent_backups\YYYY-MM-DD\应用台账-路径哈希\备份-时间戳\`
内含 Excel 完整原件副本、中文 `备份说明.md` 与机器可读 `backup.json`，确保误操作随时可回退。
