# =============================================================================
# MixSeek-Core Development Environment Dockerfile
# =============================================================================
# This Dockerfile creates a comprehensive development environment with:
# - Python 3.13.9 + uv package manager
# - Node.js 22.20.0 for AI development tools
# - Claude Code, Codex, and Gemini CLI
# - Development tools and debugging support
#
# Build Args:
#   USERNAME: Container user name (default: appuser)
#   UID: User ID for permission synchronization (default: 1000)
#   GID: Group ID for permission synchronization (default: 1000)

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# =============================================================================
# METADATA & LABELS
# =============================================================================

ARG BUILD_DATE

LABEL org.opencontainers.image.title="MixSeek-Core Development Environment"
LABEL org.opencontainers.image.description="Comprehensive development environment for MixSeek-Core with AI tools"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.created="${BUILD_DATE:-2025-10-15}"
LABEL org.opencontainers.image.source="https://github.com/your-org/mixseek-core"
LABEL mixseek.environment.type="dev"
LABEL mixseek.node.enabled="true"
LABEL mixseek.ai-tools.enabled="true"

# =============================================================================
# BUILD ARGUMENTS
# =============================================================================

ARG MIXSEEK_USERNAME=appuser
ARG MIXSEEK_UID=1000
ARG MIXSEEK_GID=1000

# =============================================================================
# SYSTEM PACKAGES
# =============================================================================

# Install essential development packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Core development tools
        curl \
        git \
        build-essential \
        cmake \
        pkg-config \
        # Protocol buffers (for certain Python packages)
        libprotobuf-dev \
        protobuf-compiler \
        # Additional tools for Python development
        sqlite3 \
        # Network tools for debugging
        iputils-ping \
        netcat-openbsd \
        # Process management
        supervisor \
        # Text editing (optional)
        vim \
        nano \
        # Locale support
        locales \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# LOCALE CONFIGURATION
# =============================================================================

# Generate Japanese locale and set environment variables
RUN sed -i -e 's/# ja_JP.UTF-8 UTF-8/ja_JP.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen

ENV LANG=ja_JP.UTF-8
ENV LC_ALL=ja_JP.UTF-8
ENV LANGUAGE=ja_JP:ja

# =============================================================================
# USER SETUP
# =============================================================================

# Create user and group with specified UID/GID for permission synchronization
# Note: No sudo privileges granted for security. If additional packages are needed,
# install them in the root section above or use USER root temporarily in this file.
RUN groupadd -g ${MIXSEEK_GID} ${MIXSEEK_USERNAME} && \
    useradd -m -u ${MIXSEEK_UID} -g ${MIXSEEK_GID} -s /bin/bash ${MIXSEEK_USERNAME}

# Create application and virtual environment directories
RUN mkdir -p /app /venv && \
    chown -R ${MIXSEEK_USERNAME}:${MIXSEEK_USERNAME} /app /venv

# =============================================================================
# PYTHON ENVIRONMENT SETUP
# =============================================================================

# Switch to non-root user for Python setup
USER ${MIXSEEK_USERNAME}
WORKDIR /app

# Set up Python environment variables
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Virtual environment configuration
ENV VIRTUAL_ENV=/venv
ENV PATH="/venv/bin:${PATH}"

# uv optimization settings
ENV UV_HTTP_TIMEOUT=120
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/venv

# =============================================================================
# NODE.JS SETUP (Development Environment Only)
# =============================================================================

# NVM and Node.js environment variables
ENV NVM_DIR=/home/${MIXSEEK_USERNAME}/.nvm
ENV NODE_VERSION=22.20.0

# Install nvm and Node.js
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && \
    bash -c ". $NVM_DIR/nvm.sh && \
        nvm install $NODE_VERSION && \
        nvm alias default $NODE_VERSION && \
        nvm use default"

# Update PATH to include Node.js
ENV PATH=$NVM_DIR/versions/node/v${NODE_VERSION}/bin:$PATH

# Verify Node.js installation and install AI development tools
RUN bash -c ". $NVM_DIR/nvm.sh && \
        node --version && \
        npm --version && \
        # Install AI development tools globally
        npm install -g @anthropic-ai/claude-code && \
        npm install -g @openai/codex && \
        npm install -g @google/gemini-cli"

# =============================================================================
# PROJECT DEPENDENCIES
# =============================================================================

# Copy dependency files with proper ownership
COPY --chown=${MIXSEEK_USERNAME}:${MIXSEEK_USERNAME} pyproject.toml uv.lock README.md LICENSE /app/

# Install Python dependencies using uv with cache mounting
RUN --mount=type=cache,target=/home/${MIXSEEK_USERNAME}/.cache/uv,uid=${MIXSEEK_UID},gid=${MIXSEEK_GID} \
    uv sync --frozen --no-install-project

# コマンドインストール
COPY --chown=${MIXSEEK_USERNAME}:${MIXSEEK_USERNAME} src/ /app/src/
RUN --mount=type=cache,target=/home/${MIXSEEK_USERNAME}/.cache/uv,uid=${MIXSEEK_UID},gid=${MIXSEEK_GID} \
    uv sync --frozen

# =============================================================================
# DEVELOPMENT TOOLS CONFIGURATION
# =============================================================================

# Create directories for development tools
RUN mkdir -p /home/${MIXSEEK_USERNAME}/.config /home/${MIXSEEK_USERNAME}/.cache /home/${MIXSEEK_USERNAME}/.codex

# Create symlink from /app/.codex/prompts to /home/${MIXSEEK_USERNAME}/.codex/prompts
# This allows codex to access spec-kit prompts from the home directory
# Note: /app/.codex/prompts is mounted from the host at runtime
RUN ln -s /app/.codex/prompts /home/${MIXSEEK_USERNAME}/.codex/prompts

# Set up debugging port
EXPOSE 5678

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Switch to root to create startup script and perform security hardening
USER root

# Create startup script for development environment (in /usr/local/bin for PATH accessibility)
RUN echo '#!/bin/bash' > /usr/local/bin/start-dev.sh && \
    echo 'echo "🚀 MixSeek-Core Development Environment"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "📂 Working directory: $(pwd)"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "🐍 Python version: $(python --version)"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "📦 uv version: $(uv --version)"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "🟢 Node.js version: $(node --version)"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "📦 npm version: $(npm --version)"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo ""' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "🤖 AI Development Tools:"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "  - Claude Code: $(claude-code --version 2>/dev/null || echo "not available")"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "  - Codex: $(codex --version 2>/dev/null || echo "not available")"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "  - Gemini CLI: $(gemini-cli --version 2>/dev/null || echo "not available")"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo ""' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "💡 Available commands:"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "  - make lint       # Run code linting"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "  - make format     # Format code"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "  - make unittest   # Run tests"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo "  - claude-code     # AI code assistance"' >> /usr/local/bin/start-dev.sh && \
    echo 'echo ""' >> /usr/local/bin/start-dev.sh && \
    echo 'exec "$@"' >> /usr/local/bin/start-dev.sh && \
    chmod +x /usr/local/bin/start-dev.sh

# Remove setuid bits from system binaries (security hardening)
RUN find /usr/bin /usr/local/bin -perm /4000 -exec chmod -s {} + 2>/dev/null || true

# Switch back to non-root user
USER ${MIXSEEK_USERNAME}

# =============================================================================
# FINAL CONFIGURATION
# =============================================================================

# Set working directory
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('Health check passed'); sys.exit(0)" || exit 1

# Default command (keeps container running for development)
ENTRYPOINT ["/usr/local/bin/start-dev.sh"]
CMD ["sleep", "infinity"]