<p align="center">
  <img src="docs/assets/mixseek700x144_Navy.svg" alt="MixSeek" width="350">
</p>

<p align="center">
  <a href="https://github.com/mixseek/mixseek-core/actions/workflows/ci.yml"><img src="https://github.com/mixseek/mixseek-core/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://mixseek.github.io/mixseek-core/"><img src="https://img.shields.io/badge/docs-GitHub%20Pages-blue" alt="Documentation"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.13+-blue.svg" alt="Python"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.ja.md">日本語</a>
</p>

A multi-agent orchestration framework for LLM-powered workflows. MixSeek enables hierarchical task delegation with Leader and Member agents, round-based evaluation, and parallel team execution.

## Features

- Multi-agent orchestration with Leader/Member hierarchy
- Support for multiple LLM providers (Google, OpenAI, Anthropic, xAI)
- Round-based evaluation with customizable judgment criteria
- Parallel team execution with leaderboard ranking
- Streamlit-based web UI for execution monitoring
- CLI tools for workspace management and agent execution

## Installation

### As a CLI Tool (Recommended)

Install globally as a command-line tool using `uv`:

```bash
# Install as a CLI tool (requires uv)
uv tool install git+https://github.com/mixseek/mixseek-core.git

# Or install from a cloned repository
git clone https://github.com/mixseek/mixseek-core.git
cd mixseek-core
uv tool install .
```

After installation, `mixseek` commands will be available globally:

```bash
mixseek --version
```

### As a Python Package

Install as a library for programmatic use:

```bash
# Using pip
pip install git+https://github.com/mixseek/mixseek-core.git

# Using uv
uv pip install git+https://github.com/mixseek/mixseek-core.git

# Add to project dependencies (uv)
uv add git+https://github.com/mixseek/mixseek-core.git
```

For development setup, see [Development Guide](docs/developer-guide.md).

## Quick Start

### Set Environment Variables

Choose one LLM provider and set the corresponding API key:

```bash
# Workspace directory (required)
export MIXSEEK_WORKSPACE=$HOME/mixseek-workspace

# Google Gemini (default in sample configs)
export GOOGLE_API_KEY=your-api-key

# OpenAI
export OPENAI_API_KEY=your-api-key

# Anthropic
export ANTHROPIC_API_KEY=your-api-key

# xAI (Grok)
export GROK_API_KEY=your-api-key
```

### Initialize Workspace

```bash
mixseek init
```

This creates sample configuration files in your workspace:
- `configs/search_news.toml` - Simple orchestrator
- `configs/search_news_multi_perspective.toml` - Multi-team orchestrator
- `configs/agents/` - Team configurations

### Run Orchestration

```bash
# Execute with orchestrator config
mixseek exec "Search for the latest AI news" \
  --config $MIXSEEK_WORKSPACE/configs/search_news.toml

# Run single team
mixseek team "Analyze this topic" \
  --config $MIXSEEK_WORKSPACE/configs/agents/team_general_researcher.toml

# Launch web UI
mixseek ui
```

## Supported LLM Providers

| Provider | Model Format | Environment Variable |
|----------|-------------|---------------------|
| Google Gemini | `google-gla:gemini-2.5-flash` | `GOOGLE_API_KEY` |
| Google Vertex AI | `google-vertex:gemini-2.5-flash` | `GOOGLE_APPLICATION_CREDENTIALS` |
| OpenAI | `openai:gpt-4o` | `OPENAI_API_KEY` |
| Anthropic | `anthropic:claude-sonnet-4-5-20250929` | `ANTHROPIC_API_KEY` |
| xAI | `xai:grok-3` | `GROK_API_KEY` |

## Documentation

Full documentation: https://mixseek.github.io/mixseek-core/

- [Getting Started (Basic)](docs/getting-started.md) - 5-minute quick start guide
- [Getting Started (Advanced)](docs/getting-started-advanced.md) - Multi-perspective search and customization
- [Quick Start Guide](docs/quickstart.md) - Detailed setup instructions
- [Member Agents Guide](docs/member-agents.md) - Agent types and configuration
- [Team Guide](docs/team-guide.md) - Team execution and delegation
- [Orchestrator Guide](docs/orchestrator-guide.md) - Multi-team parallel execution
- [Configuration Reference](docs/configuration-reference.md) - All configuration options
- [Docker Setup](docs/docker-setup.md) - Container-based development

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
