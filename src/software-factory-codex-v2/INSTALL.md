# 安装到目标项目

工厂在目标项目的 Git 仓库根目录运行。先确认有 Python 3.10+、Git、已登录的 Codex 和 GitHub CLI。Codex 客户端需要支持项目技能和子代理。目标仓库需要启用 Issues，运行者需要推送分支、管理标签和操作 PR 的权限。若项目有页面需要验收，按项目的浏览器工具调整 builder、UI 和 UX 三个角色（模板默认使用 `agent-browser`）。

运行任务的 Codex 环境需要能写工作树与 Git 元数据，并能访问 GitHub。交互式会话可以按现有权限设置授权相应命令。无人值守运行前，请确认该环境已具备这些权限。

## 1. 复制模板

在**目标项目**的终端执行。已有这个 fork 的本地副本时，直接执行其中的 `install.sh /path/to/target-repo` 即可。

```bash
ref=$(mktemp -d)
git clone --depth 1 --filter=blob:none --sparse https://github.com/sealand202607/zazencodes-season-3.git "$ref/source"
git -C "$ref/source" sparse-checkout set src/software-factory-codex-v2
"$ref/source/src/software-factory-codex-v2/install.sh" .
```

脚本复制 `.agents/skills/factory/`、八个 `.codex/agents/` 角色和 `factory/`，并把运行记录和 worktree 加进目标项目的 `.gitignore`。遇到已有的同名文件会在复制前退出。如果已有 Claude 工厂，请对照现有配置迁移项目专用的检查命令和保护路径。

## 2. 接入项目

1. 核对 `git remote get-url origin` 与 `gh repo view --json nameWithOwner,defaultBranchRef` 指向同一目标仓库，尤其是 fork。GitHub CLI 默认指向上游时，在目标检出运行 `gh repo set-default OWNER/REPO` 后复查。
2. 把项目 CI 中实际使用的测试、lint、类型检查或构建命令写入 `factory/checks.sh`。保留 `set -euo pipefail`，使任何失败都能阻止进入审查。模板在尚未配置时会返回非零。把新检出的依赖安装和验证方式写入项目的 `AGENTS.md`。
3. 在 `factory/config.json` 设置 `base_branch` 和仓库允许的 `merge_method`。需要一次只跑一项时，把 `concurrency` 设为 1。审查路由的模型值默认是 `null`，可填写本账号可用的 Codex 模型。各角色的 TOML 也支持 `model`。同一角色若在 TOML 固定了模型，该设置优先于调用时的模型选择。
4. 在目标仓库新建下列缺少的标签。

```bash
gh label create factory --color 5319E7 --description 'Build this issue with the factory'
gh label create factory:needs-info --color FBCA04 --description 'The factory needs an answer from the author'
gh label create factory:needs-human --color D93F0B --description 'The factory needs a human decision'
```

## 3. 验证并启用

在目标仓库根目录运行：

```bash
bash factory/checks.sh
factory/bin/job queue
git check-ignore factory/jobs/probe .worktrees/probe
git status --short --untracked-files=all
```

确认检查通过，查询队列成功，运行目录被忽略，而技能文件、八个角色和脚本均可提交。按该项目的发布流程把安装改动合入 `origin/<base_branch>`。工厂从这个远端分支创建任务 worktree。随后在受信任的目标项目中打开新的 Codex 对话，给一个 issue 加 `factory` 标签，输入 `$factory run <编号>`。运行会写入 issue、创建 PR，并可能自动合并。只想查看时输入 `$factory 查看任务状态`。
