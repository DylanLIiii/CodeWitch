# CodeWitch

A Python CLI tool built with Typer to manage Claude Code environment variable configurations, supporting both local (session-specific) and global (persistent) environment switch modes.

## Features

- List available environments from `~/.claude/cc.yaml`
- Activate environments locally or globally
- Show current active environment and variables
- Clear active environments
- Show detailed info about environments

## Installation

### Using pip
```bash
pip install -e .
```

### Using uv
```bash
# Install from local directory
uv pip install -e .

# Or install directly from GitHub
uvx github.com/username/codewitch  # TODO: Update with actual GitHub URL

# Or clone and install
git clone https://github.com/username/codewitch
cd codewitch
uv pip install -e .
```

## Usage

```bash
cw list                     # List available environments
cw use <environment>        # Activate environment locally
cw use --global <environment> # Activate environment globally
cw apply <environment>      # Convenience wrapper for applying environment
cw apply --global <environment> # Apply environment globally
cw current                  # Show current active environment
cw unset                    # Clear local environment
cw unset --global           # Clear global environment
cw info <environment>       # Show detailed environment info
```

### Applying Environment Variables

The `cw use` command prints export commands that you can evaluate in your shell to set environment variables:

```bash
eval "$(cw use <environment> --export)"
```

For global activation, add the `--global` flag:

```bash
eval "$(cw use --global <environment> --export)"
```

### Behavior Notes

- **Local mode** (`cw use <environment>`): Activates environment only for the current session. This clears any global environment variables from `~/.claude/settings.json` and stores the environment variables in a local state file (`~/.claude/cw_current.json`).
- **Global mode** (`cw use --global <environment>`): Persists environment variables in `~/.claude/settings.json` and also sets them locally for immediate use.

## Configuration

Create `~/.claude/cc.yaml` with your environment configurations:

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

glm:
  url: "https://open.bigmodel.cn/api/anthropic"
  token: "sk-ant-api03-xxx"
  model: "glm-4.7"
  fast: "glm-4.5-air"
  timeout: 600000
  tokens: 65000
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run tests
pytest
```

## License

MIT