# =============================================================================
# MixSeek-Core CI Environment Dockerfile
# =============================================================================
# This Dockerfile creates a minimal CI environment with:
# - Python 3.13.9 (fixed version) + uv package manager
# - Essential build tools for Python dependencies
# - Security-focused configuration
# - No Node.js or AI development tools
#
# Build Args:
#   MIXSEEK_USERNAME: Container user name (default: mixseek_core)
#   MIXSEEK_UID: User ID for permission synchronization (default: 1000)
#   MIXSEEK_GID: Group ID for permission synchronization (default: 1000)

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# =============================================================================
# METADATA & LABELS
# =============================================================================

ARG BUILD_DATE

LABEL org.opencontainers.image.title="MixSeek-Core CI Environment"
LABEL org.opencontainers.image.description="Minimal CI environment for MixSeek-Core testing and validation"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.created="${BUILD_DATE:-2025-11-23}"
LABEL org.opencontainers.image.source="https://github.com/AlpacaTechSolution/mixseek-core"
LABEL mixseek.environment.type="ci"
LABEL mixseek.node.enabled="false"
LABEL mixseek.ai-tools.enabled="false"

# =============================================================================
# BUILD ARGUMENTS
# =============================================================================

ARG MIXSEEK_USERNAME=mixseek_core
ARG MIXSEEK_UID=1000
ARG MIXSEEK_GID=1000

# =============================================================================
# SYSTEM PACKAGES
# =============================================================================

# Install essential packages for CI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Core build tools
        git \
        build-essential \
        cmake \
        pkg-config \
        # Protocol buffers (for certain Python packages)
        libprotobuf-dev \
        protobuf-compiler \
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
RUN groupadd -g ${MIXSEEK_GID} ${MIXSEEK_USERNAME} && \
    useradd -m -u ${MIXSEEK_UID} -g ${MIXSEEK_GID} -s /bin/bash ${MIXSEEK_USERNAME}

# Create application and virtual environment directories
RUN mkdir -p /app /venv && \
    chown -R ${MIXSEEK_USERNAME}:${MIXSEEK_USERNAME} /app /venv

# =============================================================================
# PYTHON ENVIRONMENT SETUP
# =============================================================================

# Switch to application user
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

# Copy .python-version to pin Python 3.13.9
COPY --chown=${MIXSEEK_USERNAME}:${MIXSEEK_USERNAME} .python-version /app/.python-version

# Install Python 3.13.9 (version specified in .python-version)
RUN uv python install

# Create Python virtual environment (uses .python-version)
RUN uv venv /venv

# =============================================================================
# PROJECT DEPENDENCIES
# =============================================================================

# Copy dependency files with proper ownership
COPY --chown=${MIXSEEK_USERNAME}:${MIXSEEK_USERNAME} pyproject.toml uv.lock README.md LICENSE /app/

# Install external dependencies only (excludes local package mixseek-core)
# This layer will be cached unless pyproject.toml or uv.lock changes
RUN --mount=type=cache,target=/home/${MIXSEEK_USERNAME}/.cache/uv,uid=${MIXSEEK_UID},gid=${MIXSEEK_GID} \
    uv sync --frozen --group dev --group docs --no-install-project

# Copy source code
COPY --chown=${MIXSEEK_USERNAME}:${MIXSEEK_USERNAME} src /app/src

# Install local package (mixseek-core) in editable mode
# This layer will rebuild when src/ changes, but external dependencies are cached
RUN uv pip install --no-deps -e .

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Remove setuid bits from system binaries (security hardening)
USER root
RUN find /usr/bin /usr/local/bin -perm /4000 -exec chmod -s {} + 2>/dev/null || true

# Switch back to application user
USER ${MIXSEEK_USERNAME}

# =============================================================================
# FINAL CONFIGURATION
# =============================================================================

# Set working directory
WORKDIR /app
