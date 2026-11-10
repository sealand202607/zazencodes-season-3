# Software Factory for Codex

把 GitHub issue 交给 Codex，按需求评估、规格、实现、测试、审查、批准的顺序处理。每个被接受的需求有独立的 Git worktree 和 PR。测试失败会带着日志退回修改，审查全部通过后，批准角色可以自动合并，也可以把具体决定留给人。

这是 ZazenCodes 的 [Software Factory for Claude Code v2](../software-factory-claude-code-v2) 的 Codex 移植版，沿用上游的 Python 状态机、GitHub 工作流和看板。[GPLv3 许可证](LICENSE)

## 开始使用

在**要处理 issue 的目标项目**打开 Codex，输入下面这句话，即可让 Codex 按安装说明配置。目标项目需要 GitHub Issues、可推送的 GitHub 账号、Python 3.10+ 和支持技能与子代理的 Codex。

```text
请按 https://github.com/sealand202607/zazencodes-season-3/blob/main/src/software-factory-codex-v2/INSTALL.md 把 Codex 软件工厂安装到当前仓库，并接入项目现有测试。
```

也可以直接运行安装脚本，然后按指南配置测试、基线分支和标签。[安装指南](INSTALL.md)

给一个小 issue 加上 `factory` 标签，在目标项目的 Codex 对话中输入：

```text
$factory run 12
```

这会处理第 12 号 issue。用 `$factory run` 处理队列，用 `$factory 查看 12 的状态` 看进度。终端脚本也可以从已安装的仓库根目录调用技能，使用单引号保留美元符号。例如，查看已有任务：

```bash
codex exec --sandbox workspace-write '$factory 查看任务状态'
```

## 一项需求怎样流转

| 阶段 | 产物或结果 |
| --- | --- |
| 需求评估 | 读取已标记的 issue，写明接受的范围、风险及 UI 或安全影响，也可以追问或拒绝。 |
| 规格与实现 | 基于目标分支建立 worktree，写可验证的验收条件，实现、提交并打开草稿 PR。 |
| 测试 | 主检出中的 `factory/checks.sh` 在该 worktree 中运行，结果记录到对应轮次。 |
| 审查 | 默认做代码审查。改动涉及界面时增加 UI 和 UX 审查，涉及安全时增加安全审查。要求修改便进入下一轮。 |
| 批准 | 批准后同步基线、重新测试、通过 GitHub 合并。超出轮数或需要人决定时，保留原因和 PR 供处理。 |

`factory/config.json` 默认同时处理 3 个任务，每个任务最多 3 轮。八个角色定义在 `.codex/agents/`。默认沿用 Codex 的模型配置，可以按角色设置模型，也可以在路由表中为不同风险的审查指定模型。此版本不读取 Claude 会话，未提供按任务估算费用。

任务记录在目标项目的 `factory/jobs/`。中断后重新运行同一条指令会从已保存的阶段继续。在项目根目录运行以下命令，可以在本机查看每轮的测试日志、审查意见与 PR 链接。[本地看板](http://127.0.0.1:8000/dashboard.html)

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory factory
```

上游示例展示了计算器需求合并、界面审查和退回人工处理时的完整产物。[原版示例](../software-factory-claude-code-v2/examples/jobs)
