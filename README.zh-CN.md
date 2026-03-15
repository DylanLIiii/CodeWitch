# CodeWitch 中文使用教程

CodeWitch 是一个 Python CLI 工具，用于在 Claude Code 和 Codex 之间切换环境变量，支持独立的工具命令和配置管理。

## 功能特性

- **工具专属命令**: 使用 `cw claude-code ...` 和 `cw codex ...` 分别管理 Claude Code 和 Codex
- **独立配置文件**: Claude Code 使用 `~/.claude/cc.yaml`，Codex 使用 `~/.codex/cw.yaml`
- **终端级切换**: 使用 `use` 命令仅在当前终端生效（通过 `--export` 打印环境变量）
- **全局切换**: 使用 `apply` 命令持久化修改全局配置
- **Codex 认证模式**: 支持官方登录（login）或 API Key 两种认证方式

## 安装

### 方法一：使用 pip

```bash
pip install -e .
```

### 方法二：使用 uv

```bash
uv pip install -e .
```

安装完成后，可以使用 `cw` 命令：

```bash
cw --help
```

## 快速开始

### 1. 配置环境

#### Claude Code 配置

创建 `~/.claude/cc.yaml` 文件：

```yaml
# Claude Code 配置文件
duckcoding:
  url: "https://jp.duckcoding.com"
  token: "sk-ant-api03-xxx"
  timeout: 600000
  tokens: 65000

huoshan:
  url: "https://ark.cn-beijing.volces.com/api/coding"
  token: "sk-ant-api03-xxx"
  model: "ark-code-latest"
  fast: "ark-code-latest"
```

配置项说明：
- `url`: API 端点地址
- `token`: Anthropic API Token
- `model`: 使用的模型名称
- `fast`: 快速响应使用的模型
- `timeout`: 超时时间（毫秒）
- `tokens`: 最大输出 tokens 数量

#### Codex 配置

创建 `~/.codex/cw.yaml` 文件：

```yaml
# Codex 配置文件

# 方式一：使用官方登录（需要先运行 codex login）
official:
  auth_mode: "login"
  model: "gpt-5.4"

# 方式二：使用 API Key（兼容 OpenAI 的端点）
proxy:
  auth_mode: "apikey"
  base_url: "https://your-openai-compatible-endpoint/v1"
  api_key: "sk-xxx"
  model: "gpt-5.4"
```

配置项说明：
- `auth_mode`: 认证模式，`login` 或 `apikey`
- `base_url`: API 端点地址（apikey 模式需要）
- `api_key`: API Key（apikey 模式需要）
- `model`: 使用的模型名称

### 2. 查看环境列表

```bash
# 查看 Claude Code 环境
cw claude-code list

# 查看 Codex 环境
cw codex list
```

### 3. 切换环境

#### 终端级切换（仅当前终端生效）

```bash
# Claude Code
cw claude-code use <环境名称>
cw claude-code use <环境名称> --export

# Codex
cw codex use <环境名称>
cw codex use <环境名称> --export
```

**使用 --export 的用法：**

```bash
# Bash/Zsh
eval "$(cw claude-code use duckcoding --export)"
eval "$(cw codex use proxy --export)"

# Fish
eval (cw claude-code use duckcoding --export)
eval (cw codex use proxy --export)
```

Codex 的 `use` 命令会创建一个隔离的 `CODEX_HOME`，确保切换只影响当前终端。

#### 全局切换（持久生效）

```bash
# Claude Code - 修改 ~/.claude/settings.json
cw claude-code apply <环境名称>

# Codex - 修改 ~/.codex/config.toml 和 ~/.codex/auth.json
cw codex apply <环境名称>
```

### 4. 查看当前状态

```bash
# 查看当前 Claude Code 环境
cw claude-code current

# 查看当前 Codex 环境
cw codex current
```

### 5. 取消切换

```bash
# 取消终端级切换
cw claude-code unset
cw codex unset

# 取消全局切换
cw claude-code unset --global
cw codex unset --global
```

### 6. 查看环境详情

```bash
# 查看特定 Claude Code 环境配置
cw claude-code info <环境名称>

# 查看特定 Codex 环境配置
cw codex info <环境名称>
```

## 完整命令参考

### Claude Code 命令

| 命令 | 说明 |
|------|------|
| `cw claude-code list` | 列出所有 Claude Code 环境 |
| `cw claude-code use <env>` | 终端级切换到指定环境 |
| `cw claude-code use <env> --export` | 输出环境变量导出命令 |
| `cw claude-code apply <env>` | 全局应用指定环境 |
| `cw claude-code current` | 查看当前使用的环境 |
| `cw claude-code unset` | 取消终端级切换 |
| `cw claude-code unset --global` | 取消全局切换 |
| `cw claude-code info <env>` | 查看环境详细信息 |

### Codex 命令

| 命令 | 说明 |
|------|------|
| `cw codex list` | 列出所有 Codex 环境 |
| `cw codex use <env>` | 终端级切换到指定环境 |
| `cw codex use <env> --export` | 输出环境变量导出命令 |
| `cw codex apply <env>` | 全局应用指定环境 |
| `cw codex current` | 查看当前使用的环境 |
| `cw codex unset` | 取消终端级切换 |
| `cw codex unset --global` | 取消全局切换 |
| `cw codex info <env>` | 查看环境详细信息 |

## 常见问题

### Q: 使用 Codex 的 login 模式需要什么前提条件？

A: 需要先运行官方的 `codex login` 命令完成登录，确保 `~/.codex/auth.json` 中存在有效的登录凭证。

### Q: 如何使用自定义的 API 端点？

A: 在 Codex 配置中使用 `apikey` 模式，设置 `base_url` 为你的兼容 OpenAI 的 API 端点。

### Q: 终端级切换和全局切换有什么区别？

A:
- **终端级切换 (`use`)**: 仅影响当前终端会话，关闭终端后失效
- **全局切换 (`apply`)**: 持久修改配置文件，对所有终端生效

### Q: 如何同时使用 Claude Code 和 Codex？

A: 分别配置 `~/.claude/cc.yaml` 和 `~/.codex/cw.yaml`，然后使用对应的命令进行管理。它们相互独立，互不影响。

## 开发

```bash
# 安装依赖
pip install -r requirements.txt
pip install -e .

# 运行测试
pytest
```

## 许可证

MIT
