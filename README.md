# CodeWitch

A Python CLI tool built with Typer to switch Claude Code and Codex environments with explicit tool commands.

## Features

- Tool-specific commands: `cw claude-code ...` and `cw codex ...`
- Separate config files: `~/.claude/cc.yaml` and `~/.codex/cw.yaml`
- `use` for terminal-only switching (prints exports via `--export`)
- `apply` for persistent global switching
- Codex auth mode switching: official login or API key
- Current status, environment listing, and detailed environment info

## Installation

### Using pip

```bash
pip install -e .
```

### Using uv

```bash
uv pip install -e .
```

## Usage

### Claude Code

```bash
cw claude-code list
cw claude-code use <environment>
cw claude-code use <environment> --export
cw claude-code apply <environment>
cw claude-code current
cw claude-code unset
cw claude-code unset --global
cw claude-code info <environment>
```

### Codex

```bash
cw codex list
cw codex use <environment>
cw codex use <environment> --export
cw codex apply <environment>
cw codex current
cw codex unset
cw codex unset --global
cw codex info <environment>
```

### Terminal-only switching

```bash
eval "$(cw claude-code use <environment> --export)"
eval "$(cw codex use <environment> --export)"
```

For Codex, `use` creates a managed `CODEX_HOME` so the switch only affects the current terminal.

### Global switching

- `cw claude-code apply <environment>` updates `~/.claude/settings.json`
- `cw codex apply <environment>` updates `~/.codex/config.toml` and `~/.codex/auth.json`

## Configuration

### Claude Code

Create `~/.claude/cc.yaml`:

```yaml
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

### Codex

Create `~/.codex/cw.yaml`:

```yaml
official:
  auth_mode: "login"
  model: "gpt-5.4"

proxy:
  auth_mode: "apikey"
  base_url: "https://your-openai-compatible-endpoint/v1"
  api_key: "sk-xxx"
  model: "gpt-5.4"
```

Codex official login requires an existing `codex login` session in `~/.codex/auth.json`.

## Development

```bash
pip install -r requirements.txt
pip install -e .
pytest
```

## License

MIT
