# CodeWitch

A Python CLI tool built with Typer to switch Claude Code and Codex environments with explicit tool commands.

## Features

- Tool-specific commands: `cw claude-code ...` and `cw codex ...`
- Separate config files: `~/.claude/cc.yaml` and `~/.codex/cw.yaml`
- `use` for terminal-only switching (prints exports via `--export`)
- `apply` for persistent global switching
- Claude multi-model mapping (`opus`/`sonnet`/`haiku`) with backward compatibility for `fast`
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
  model: "sonnet" # keep an alias so auto mode and capability detection work
  fast: "ark-code-fast" # legacy fast-model override
  models:
    opus: "claude-opus-4-6"
    sonnet: "ark-code-latest" # the provider's real model ID
    haiku: "claude-haiku-4-5"
  capabilities:
    sonnet: "effort,thinking" # declare features an opaque ID can't advertise
  max_context_tokens: 256000 # correct the window guess for unrecognized IDs
  auto_mode: true # `apply` writes permissions.defaultMode=auto
  auto_mode_server: false # → CLAUDE_CODE_AUTO_MODE_SERVER=0
  model_overrides: # `apply` merges these into settings.json modelOverrides
    claude-sonnet-5: "ark-code-latest"
```

Claude mapping behavior:
- `model` → `ANTHROPIC_MODEL`. Prefer an alias (`sonnet`, `opus`, `fable`, `haiku`) or an ID containing a known model name (e.g. `my-gateway/claude-opus-5`): Claude Code only enables auto mode, effort levels, and thinking for models it recognizes. An opaque ID like `glm-4.7` is automatically pinned behind the `sonnet` alias (`ANTHROPIC_MODEL=sonnet` + `ANTHROPIC_DEFAULT_SONNET_MODEL=<id>`) unless `models.sonnet` is already set, so the wire ID is unchanged while the session keeps a recognized model identity.
- `models.opus` → `ANTHROPIC_DEFAULT_OPUS_MODEL`
- `models.sonnet` → `ANTHROPIC_DEFAULT_SONNET_MODEL`
- `models.haiku` → `ANTHROPIC_DEFAULT_HAIKU_MODEL`
- `models.fable` → `ANTHROPIC_DEFAULT_FABLE_MODEL` (top-level `fable:` also works)
- `capabilities.<opus|sonnet|haiku|fable|custom>` → `ANTHROPIC_DEFAULT_*_MODEL_SUPPORTED_CAPABILITIES`; accepts a comma-separated string or a YAML list
- `fast` remains supported and maps to `ANTHROPIC_SMALL_FAST_MODEL` (deprecated upstream; it also falls back as `haiku` when `models.haiku` is missing)
- `max_context_tokens` → `CLAUDE_CODE_MAX_CONTEXT_TOKENS`
- `auto_mode_server` → `CLAUDE_CODE_AUTO_MODE_SERVER` (`true`→`1`, `false`→`0`); set `false` to skip server-side classifier review on gateways that don't support it
- `custom_model`, `custom_model_name`, `custom_model_description`, `custom_model_capabilities` → `ANTHROPIC_CUSTOM_MODEL_OPTION{,_NAME,_DESCRIPTION,_SUPPORTED_CAPABILITIES}`: adds a row to the `/model` picker
- `auto_mode` (apply only) → `permissions.defaultMode: "auto"` in `~/.claude/settings.json`; `use` can't set it, so in terminal-only sessions switch with Shift+Tab or `claude --permission-mode auto`. `unset --global` or applying an env without it restores the previous value
- `model_overrides` (apply only) → merged into `settings.json` `modelOverrides` (Anthropic model ID → provider ID); `unset --global` removes only the keys CodeWitch added

`apply` merges into `settings.json`: env vars and `modelOverrides` keys that you manage by hand are preserved, and `unset --global` removes only what CodeWitch wrote.

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
