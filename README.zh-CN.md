# agents-teamwork

[![status](https://img.shields.io/badge/status-v1-blue)]() [![tools](https://img.shields.io/badge/tools-12-green)]() [![license](https://img.shields.io/badge/license-Apache--2.0-lightgrey)]() [![stars](https://img.shields.io/github/stars/jessexu1818/agents-teamwork?style=social)]()

![agents-teamwork：一个 team-orchestrator 技能 + 12 种编程工具的角色配置](assets/social-preview.png)

通用多 IDE 智能体协作技能：一个 `team-orchestrator` 技能加按工具生成的角色配置，
把任何受支持的 IDE 变成“根节点 + 专家子智能体”团队。根节点负责架构、任务分解、
集成、验证和最终答复；子智能体只提供有边界的证据和执行结果。

## 为什么

- 一个技能文件到处可用，即使没有任何生成配置（纯技能模式）也能工作。
- 生成的角色文件为每种工具预填模型、沙箱和路由默认值。
- 显式的委托契约让并行子智能体互不干扰：每个文件或子系统只有一个写者，
  归属冲突由根节点仲裁。
- 分类路由（`quick` / `deep` / `ultrabrain` / `visual`）按任务难度调配成本。

## TL;DR 安装

| 模式 | 命令 / 指引 |
| --- | --- |
| 纯技能（30 秒） | `cp templates/skills/team-orchestrator/SKILL.md <repo>/.agents/skills/team-orchestrator/SKILL.md` |
| 完整安装 | `./setup.sh --target <repo> --tools all --components all --yes` |
| 全局安装 | 见 [guides/global-setup.md](guides/global-setup.md) |

粘贴到你的智能体：

```text
请按本仓库 guides/quickstart.md 安装 team-orchestrator。除非我要求完整安装，否则使用纯技能模式，并报告复制了哪些文件。
```

## 拓扑结构

```text
                    team-orchestrator (root)
                    架构师 + 集成者
        ____________________|____________________
        |        |         |         |           |
    explorer  worker    tester   reviewer   researcher   （核心）
        |        |         |                        |
     planner  oracle   designer   ........（可选扩展）
     (.plans/  架构咨询  UI/视觉
      访谈规划)
```

根节点通过有边界的契约（目标、范围、背景、约束、交付物、验收标准）分发任务，
再合并返回的切片。没有真实的子智能体调用，就不能声称做过委托。

## 快速开始

三种方式，按顺序排列。请从第一种开始。

### （1）纯技能安装——首选，30 秒，零脚本

把单个技能文件复制到你的仓库。这个文件本身就够了：根节点可以直接按其中
的角色契约内联行事，不需要任何生成配置。

```sh
cp templates/skills/team-orchestrator/SKILL.md <repo>/.agents/skills/team-orchestrator/SKILL.md
```

各工具的技能目标位置（同一文件，不同目录）：

| 工具 | 把 SKILL.md 复制到 |
| --- | --- |
| Claude | `<repo>/.claude/skills/team-orchestrator/SKILL.md` |
| Codex | `<repo>/.agents/skills/team-orchestrator/SKILL.md` |
| Cursor | `<repo>/.cursor/skills/team-orchestrator/SKILL.md` |
| opencode | `<repo>/.opencode/skills/team-orchestrator/SKILL.md` |
| Kiro | `<repo>/.kiro/skills/team-orchestrator/SKILL.md` |
| CodeBuddy | `<repo>/.codebuddy/skills/team-orchestrator/SKILL.md` |
| 通用 agents | `<repo>/.agents/skills/team-orchestrator/SKILL.md` |
| Antigravity | `<repo>/.agents/skills/team-orchestrator/SKILL.md` |
| Copilot | `<repo>/.github/skills/team-orchestrator/SKILL.md` |
| Windsurf | `<repo>/.windsurf/skills/team-orchestrator/SKILL.md` |
| Qoder | `<repo>/.qoder/skills/team-orchestrator/SKILL.md` |
| Trae | `<repo>/.trae/skills/team-orchestrator/SKILL.md` |

然后这样调用：

```text
$team-orchestrator 梳理 src/auth 下的认证流程并列出安全的编辑点。不要修改任何代码。
```

5 分钟完整演练见 [guides/quickstart.md](guides/quickstart.md)。

### （2）完整安装——生成角色 + AGENTS.md

需要模型/沙箱默认值和按角色文件时，把安装器运行到一个已存在的目标目录
（必须与本源码目录不同）：

```sh
./setup.sh --target ../my-project --tools all --components all
```

常用变体：

```sh
# 仅安装技能（无角色文件、无 AGENTS.md）
./setup.sh --target ../my-project --tools claude,agents --components skills-only --yes
# 增加可选角色
./setup.sh --target ../my-project --components all --extra planner,oracle,designer --yes
# 更便宜的预设，或锁定单个模型
./setup.sh --target ../my-project --preset plus --yes
./setup.sh --target ../my-project --reviewer-model gpt-5 --reviewer-effort high --yes
```

`scripts/generate.py` 接受相同的标志（另有 `--preset pro|plus|custom` 和
`--<role>-model` 覆盖）；`setup.sh` 是安全封装：先暂存、有覆盖时提示确认，
再复制进去。Windows 请用与 `setup.sh` 对等的 `setup.ps1`。

### （3）全局安装

v1 的各工具全局安装均为手动操作：安装器的 `--global` 会被拒绝。请按
[guides/global-setup.md](guides/global-setup.md) 中的按工具用户目录路径和
合并规则操作。

## 工具矩阵

`--tools all` 覆盖 12 种工具。技能写入各工具的 `skills/` 目录；角色写入各
工具的 `agents/` 目录（仅 `all` 组件）。

| 工具 | 技能输出 | 角色输出 |
| --- | --- | --- |
| claude | `.claude/skills/team-orchestrator/SKILL.md` | `.claude/agents/<role>.md` |
| codex | `.agents/skills/team-orchestrator/SKILL.md` | `.codex/agents/<role>.toml` + `.codex/config.toml` |
| cursor | `.cursor/skills/team-orchestrator/SKILL.md` | `.cursor/agents/<role>.md` |
| opencode | `.opencode/skills/team-orchestrator/SKILL.md` | `.opencode/agents/<role>.md` |
| kiro | `.kiro/skills/team-orchestrator/SKILL.md` | `.kiro/agents/<role>.md` |
| codebuddy | `.codebuddy/skills/team-orchestrator/SKILL.md` | `.codebuddy/agents/<role>.md` |
| agents | `.agents/skills/team-orchestrator/SKILL.md` | `.agents/agents/<role>.md` |
| antigravity | `.agents/skills/team-orchestrator/SKILL.md` | `.agent/agents/<role>.md` |
| copilot | `.github/skills/team-orchestrator/SKILL.md` | `.github/agents/<role>.agent.md` |
| windsurf | `.windsurf/skills/team-orchestrator/SKILL.md` | `.windsurf/rules/<role>.md` |
| qoder | `.qoder/skills/team-orchestrator/SKILL.md` | `.qoder/agents/<role>.md` |
| trae | `.trae/skills/team-orchestrator/SKILL.md` | `.trae/rules/<role>.md` |

完整安装还会在目标根目录写入 `AGENTS.md`。Codex 是例外：角色转为 TOML
（`model`、`sandbox_mode`、原始数字 `temperature`、`developer_instructions`）；
其他工具保留 Markdown，由 `model:` 前置字段代入模型名。各工具说明见
[guides/tools/](guides/tools/)。

## 模型配置

预设决定各角色模型；标志可以覆盖预设。

| 预设 | 编排者 | 评审者 | 其余所有角色 | 评审强度 |
| --- | --- | --- | --- | --- |
| pro（默认） | gpt-5 | gpt-5 | gpt-5-mini | low |
| plus | gpt-5-mini | gpt-5 | gpt-5-mini | low |
| custom | gpt-5-mini | gpt-5-mini | gpt-5-mini | low |

按角色锁定：

```sh
./setup.sh --target ../my-project --orchestrator-model gpt-5 --worker-model gpt-5-mini --yes
python3 scripts/generate.py --target /tmp/demo --tools claude --preset plus --reviewer-effort high
```

分类路由在调用时选择，不在安装时决定：
`--category quick|deep|ultrabrain|visual`。见
[guides/model-matrix.md](guides/model-matrix.md) 和
[guides/categories.md](guides/categories.md)。

优先级（越高越优先）：

```text
调用时标志 (--orchestrator/--worker/--reviewer/--category/--extra)
  > 按角色锁定 (--<role>-model, --reviewer-effort)
    > 分类路由 (quick/deep/ultrabrain/visual)
      > 预设默认值 (pro/plus/custom)
```

## 角色

| 角色 | 职责 | 是否必需 |
| --- | --- | --- |
| explorer | 代码映射、流程、约束 | 核心 |
| worker | 有范围的实现（quick / deep） | 核心 |
| tester | 复现与针对性验证 | 核心 |
| reviewer | 变更后的独立审计 | 核心 |
| researcher | 外部与版本相关事实 | 核心 |
| planner | 访谈式规划，写入 `.plans/` | （可选） |
| oracle | 变更前的架构与排障咨询 | （可选） |
| designer | UI 结构加图片 / PDF 解读 | （可选） |

核心角色默认安装。可选角色需要 `--extra`
（例如 `--extra planner,oracle,designer`，可取任意子集）。

## 使用技能

当任务跨文件、需要并行探索、独立测试或评审、版本相关的外部资料，或用户
要求委托/子智能体时，触发 `$team-orchestrator`。琐碎的单文件编辑和简单问答
不要用它。

```text
$team-orchestrator --category deep --extra 公开 API 保持不变。 \
  把 src/orders 下的优惠券校验重构为可测试模块。
```

调用参数：`--orchestrator <model>`、`--worker <model>`、
`--reviewer <model>`、`--category <quick|deep|ultrabrain|visual>`、
`--extra <text>`（自由文本约束，追加到每个委托契约）。单次运行的标志优先
于生成文件。详见 [guides/planning.md](guides/planning.md)。

## Token 与成本说明

- 纯技能模式不增加额外成本：没有生成文件，没有锁定的高价模型。
- 默认预设把映射、构建、检查放在 `gpt-5-mini` 上；`gpt-5` 只留给编排者与
  评审者（pro）或仅评审者（plus）。
- `ultrabrain`（oracle 咨询 + 高强度评审）只留给最难的推理任务；紧凑的单点
  修复用 `quick`。
- 子智能体只返回结论（路径、符号、命令、结果），不倾倒原文；根节点上下文
  只保留决策、摘要、diff 和风险。

## 指南索引

- [guides/quickstart.md](guides/quickstart.md)——5 分钟分步指南
- [guides/model-matrix.md](guides/model-matrix.md)——预设、锁定、路由、优先级
- [guides/categories.md](guides/categories.md)——quick/deep/ultrabrain/visual
- [guides/planning.md](guides/planning.md)——planner 访谈流程
- [guides/global-setup.md](guides/global-setup.md)——手动全局安装
- [guides/tools/](guides/tools/)——各工具路径、模型字段、限制

## 贡献与许可

见 [CONTRIBUTING.md](CONTRIBUTING.md)、[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)、
[SECURITY.md](SECURITY.md) 和 [LICENSE](LICENSE)（MIT）。
