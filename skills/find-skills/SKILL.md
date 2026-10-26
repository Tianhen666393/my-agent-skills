---
name: find-skills
description: 查找、核实、介绍和比较可安装的 Agent Skill。用户要求“查找 skill”“找 skill”“搜索 skill”或推荐、介绍、比较 Skill 时使用；按 skills.sh 详情核实用途和动态数据，仅在明确要求安装时安装。
---

# Find Skills

> [!NOTE]
> **上游出处 (Upstream Source)**：本技能源自开源生态 [`vercel-labs/skills`](https://github.com/vercel-labs/skills)（作者：Vercel Labs，生态平台：[skills.sh](https://www.skills.sh/)）。
> **天痕定制说明**：针对官方原版“只罗列安装命令、缺乏功能详细解读且易凭名字推测用途”的痛点，进行了**中文本土化重构**，前置注入了【用户的检索与安装规则】：强制要求逐个打开详情页核实功能用途后再向用户介绍、动态排行指标必须注明查询日期、严禁未经明确授权擅自安装。

This skill helps you discover and install skills from the open agent skills ecosystem.

## 用户的检索与安装规则（优先于下方通用示例）

- “查找 skill”“找 skill”“搜索 skill”及推荐、介绍、比较 Skill 的执行请求使用本技能；仅讨论或引用这些触发词不执行检索。
- 优先访问 https://www.skills.sh/，不能仅依据本地已安装列表回答公开技能发现请求。
- 逐个打开对应的 skills.sh 详情页，阅读用途和能力说明后再介绍；不得凭名称、榜单摘要或仓库名推测用途。
- 当前排名前 N、热门、安装量最高等动态信息以当次网站数据为准，并注明查询日期。CLI 结果不能替代网站公开排名。
- 输出尽量包括排名或安装量、名称、来源仓库、已核实用途及对应详情页。没有公开排名或安装量时说明缺失，不编造。
- 可用 `npx skills find [query]` 补充检索。网站无法访问或详情信息不足时说明限制，不猜测用途和排名。
- 只有用户明确要求安装才执行安装；仅查找、介绍、比较时不自动安装。

## When to Use This Skill

Use this skill when the user:

- Asks "how do I do X" where X might be a common task with an existing skill
- Says "find a skill for X" or "is there a skill for X"
- Asks "can you do X" where X is a specialized capability
- Expresses interest in extending agent capabilities
- Wants to search for tools, templates, or workflows
- Mentions they wish they had help with a specific domain (design, testing, deployment, etc.)

## What is the Skills CLI?

The Skills CLI (`npx skills`) is the package manager for the open agent skills ecosystem. Skills are modular packages that extend agent capabilities with specialized knowledge, workflows, and tools.

**Key commands:**

- `npx skills find [query] [--owner <owner>]` - Search for skills interactively or by keyword, optionally scoped to a GitHub owner
- `npx skills add <package>` - Install a skill from GitHub or other sources
- `npx skills update` - Update all installed skills

**Browse skills at:** https://skills.sh/

## How to Help Users Find Skills

### Step 1: Understand What They Need

When a user asks for help with something, identify:

1. The domain (e.g., React, testing, design, deployment)
2. The specific task (e.g., writing tests, creating animations, reviewing PRs)
3. Whether this is a common enough task that a skill likely exists

### Step 2: Check the Leaderboard First

Before running a CLI search, check the [skills.sh leaderboard](https://skills.sh/) to see if a well-known skill already exists for the domain. Read the active leaderboard tab and its stated time window; report only the metric shown by the current page. Popularity does not establish task suitability or quality.

Search the current page for relevant candidates rather than treating a remembered list or historical install count as current ranking evidence.

### Step 3: Search for Skills

If the leaderboard doesn't cover the user's need, run the find command:

```bash
npx skills find [query] [--owner <owner>]
```

For example:

- User asks "how do I make my React app faster?" → `npx skills find react performance`
- User asks "can you help me with PR reviews?" → `npx skills find pr review`
- User asks "I need to create a changelog" → `npx skills find changelog`

### Step 4: Verify Quality Before Recommending

**Do not recommend a skill based solely on search results.** Always verify:

1. **Purpose and fit** — Read each skills.sh detail page and verify what tasks it supports.
2. **Source** — Check the source repository and the author or organization.
3. **Dynamic metrics** — Report available install counts and repository stars with the query date; these are context, not proof of quality.

### Step 5: Present Options to the User

When you find relevant skills, present them to the user with:

1. The skill name and what it does
2. The install count and source
3. The install command they can run
4. A link to learn more at skills.sh

Example response:

```
I found a skill that might help! The "react-best-practices" skill provides
React and Next.js performance optimization guidelines from Vercel Engineering.
(install count verified on the query date)

To install it:
npx skills add vercel-labs/agent-skills@react-best-practices

Learn more: https://skills.sh/vercel-labs/agent-skills/react-best-practices
```

### Step 6: Offer to Install

If the user wants to proceed, you can offer to install or synchronize the skill:

- **Via Skills CLI:**
  `ash
  npx skills add <owner/repo@skill> -g -y
  `
  The -g flag installs globally (user-level) and -y skips confirmation prompts.
- **Via Skill Management Tools / Git:**
  Skills can also be installed via skill management tools (such as CC Switch repository sources) or directly cloned into the agent's skills directory.

## Common Skill Categories

When searching, consider these common categories:

| Category        | Example Queries                          |
| --------------- | ---------------------------------------- |
| Web Development | react, nextjs, typescript, css, tailwind |
| Testing         | testing, jest, playwright, e2e           |
| DevOps          | deploy, docker, kubernetes, ci-cd        |
| Documentation   | docs, readme, changelog, api-docs        |
| Code Quality    | review, lint, refactor, best-practices   |
| Design          | ui, ux, design-system, accessibility     |
| Productivity    | workflow, automation, git                |

## Tips for Effective Searches

1. **Use specific keywords**: "react testing" is better than just "testing"
2. **Try alternative terms**: If "deploy" doesn't work, try "deployment" or "ci-cd"
3. **Check popular sources**: Many skills come from `vercel-labs/agent-skills` or `ComposioHQ/awesome-claude-skills`

## When No Skills Are Found

If no relevant skills exist:

1. Acknowledge that no existing skill was found
2. Offer to help with the task directly using your general capabilities
3. Suggest the user could create their own skill with `npx skills init`

Example:

```
I searched for skills related to "xyz" but didn't find any matches.
I can still help you with this task directly! Would you like me to proceed?

If this is something you do often, you could create your own skill:
npx skills init my-xyz-skill
```
