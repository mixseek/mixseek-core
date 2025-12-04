# =============================================================================
# MixSeek-Core Production Environment Dockerfile
# =============================================================================
# This is a multi-stage Dockerfile that creates a minimal, secure production
# environment with:
# - Python 3.13.9 runtime only
# - Minimal system packages
# - Security hardening
# - No development tools, Node.js, or AI tools
#
# Build Args:
#   USERNAME: Container user name (default: appuser)
#   UID: User ID for permission synchronization (default: 1000)
#   GID: Group ID for permission synchronization (default: 1000)

# =============================================================================
# STAGE 1: BUILDER - Build dependencies and virtual environment
# =============================================================================

FROM ghcr.io/astral-sh/uv:0.8.24-python3.13-bookworm-slim AS builder

LABEL stage=builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md /app/

# Create virtual environment and install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /venv && \
    uv sync --frozen --no-dev --no-editable

# =============================================================================
# STAGE 2: RUNTIME - Minimal production image
# =============================================================================

FROM python:3.13-slim-bookworm AS runtime

# =============================================================================
# METADATA & LABELS
# =============================================================================

ARG BUILD_DATE

LABEL org.opencontainers.image.title="MixSeek-Core Production Environment"
LABEL org.opencontainers.image.description="Minimal secure production environment for MixSeek-Core"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.created="${BUILD_DATE:-2025-10-15}"
LABEL org.opencontainers.image.source="https://github.com/your-org/mixseek-core"
LABEL mixseek.environment.type="prod"
LABEL mixseek.node.enabled="false"
LABEL mixseek.ai-tools.enabled="false"

# =============================================================================
# BUILD ARGUMENTS
# =============================================================================

ARG MIXSEEK_USERNAME=appuser
ARG MIXSEEK_UID=1000
ARG MIXSEEK_GID=1000

# =============================================================================
# MINIMAL SYSTEM PACKAGES
# =============================================================================

# Install only essential runtime packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Essential for HTTPS connections
        ca-certificates \
        # Process management
        dumb-init \
        # Time zone data
        tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# =============================================================================
# SECURITY HARDENING
# =============================================================================

# Remove unnecessary packages and files
RUN apt-get autoremove -y && \
    apt-get autoclean && \
    rm -rf /usr/share/doc/* && \
    rm -rf /usr/share/man/* && \
    rm -rf /usr/share/locale/* && \
    rm -rf /var/log/* && \
    rm -rf /tmp/* && \
    rm -rf /var/tmp/*

# Remove setuid and setgid bits from all files
RUN find / -type f \( -perm -4000 -o -perm -2000 \) -exec chmod -s {} + 2>/dev/null || true

# =============================================================================
# USER SETUP
# =============================================================================

# Create production user with specified UID/GID
RUN groupadd -g ${MIXSEEK_GID} ${MIXSEEK_USERNAME} && \
    useradd -m -u ${MIXSEEK_UID} -g ${MIXSEEK_GID} -s /bin/bash ${MIXSEEK_USERNAME} && \
    # Lock the user account (no password login)
    usermod -L ${MIXSEEK_USERNAME}

# Create application directory
RUN mkdir -p /app && \
    chown -R ${MIXSEEK_USERNAME}:${MIXSEEK_USERNAME} /app

# =============================================================================
# PYTHON ENVIRONMENT SETUP
# =============================================================================

# Copy virtual environment from builder stage
COPY --from=builder /venv /venv

# Set up Python environment variables
ENV VIRTUAL_ENV=/venv
ENV PATH="/venv/bin:${PATH}"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Production-specific Python settings
ENV PYTHONHASHSEED=random
ENV PYTHONIOENCODING=utf-8

# =============================================================================
# APPLICATION SETUP
# =============================================================================

# Switch to application user
USER ${MIXSEEK_USERNAME}

# Set working directory
WORKDIR /app

# Copy application code (this should be done by the deployment process)
# COPY --chown=${MIXSEEK_USERNAME}:${MIXSEEK_USERNAME} . /app/

# Create necessary directories
RUN mkdir -p /home/${MIXSEEK_USERNAME}/.config && \
    mkdir -p /home/${MIXSEEK_USERNAME}/.cache && \
    mkdir -p /app/logs && \
    mkdir -p /app/data

# =============================================================================
# PRODUCTION CONFIGURATION
# =============================================================================

# Set production environment variables
ENV ENVIRONMENT=production
ENV DEBUG=false
ENV LOG_LEVEL=WARNING
ENV PYTHONHASHSEED=random

# Switch to root to create startup script
USER root

# Create production startup script (in /usr/local/bin for PATH accessibility)
RUN echo '#!/bin/bash' > /usr/local/bin/prod-startup.sh && \
    echo 'set -e' >> /usr/local/bin/prod-startup.sh && \
    echo 'echo "🚀 MixSeek-Core Production Environment"' >> /usr/local/bin/prod-startup.sh && \
    echo 'echo "📂 Working directory: $(pwd)"' >> /usr/local/bin/prod-startup.sh && \
    echo 'echo "🐍 Python version: $(python --version)"' >> /usr/local/bin/prod-startup.sh && \
    echo 'echo "👤 Running as: $(whoami) ($(id))"' >> /usr/local/bin/prod-startup.sh && \
    echo 'echo "🌍 Environment: ${ENVIRONMENT:-production}"' >> /usr/local/bin/prod-startup.sh && \
    echo 'echo "🔒 Debug mode: ${DEBUG:-false}"' >> /usr/local/bin/prod-startup.sh && \
    echo 'echo "📋 Log level: ${LOG_LEVEL:-WARNING}"' >> /usr/local/bin/prod-startup.sh && \
    echo 'echo ""' >> /usr/local/bin/prod-startup.sh && \
    echo '# Validate critical environment variables' >> /usr/local/bin/prod-startup.sh && \
    echo 'if [ "$DEBUG" = "true" ]; then' >> /usr/local/bin/prod-startup.sh && \
    echo '    echo "⚠️  WARNING: Debug mode is enabled in production!"' >> /usr/local/bin/prod-startup.sh && \
    echo 'fi' >> /usr/local/bin/prod-startup.sh && \
    echo '' >> /usr/local/bin/prod-startup.sh && \
    echo '# Health check function' >> /usr/local/bin/prod-startup.sh && \
    echo 'health_check() {' >> /usr/local/bin/prod-startup.sh && \
    echo '    python -c "import sys; print('\''Health check passed'\''); sys.exit(0)" 2>/dev/null || {' >> /usr/local/bin/prod-startup.sh && \
    echo '        echo "❌ Health check failed"' >> /usr/local/bin/prod-startup.sh && \
    echo '        return 1' >> /usr/local/bin/prod-startup.sh && \
    echo '    }' >> /usr/local/bin/prod-startup.sh && \
    echo '}' >> /usr/local/bin/prod-startup.sh && \
    echo '' >> /usr/local/bin/prod-startup.sh && \
    echo '# Run health check on startup' >> /usr/local/bin/prod-startup.sh && \
    echo 'health_check' >> /usr/local/bin/prod-startup.sh && \
    echo '' >> /usr/local/bin/prod-startup.sh && \
    echo '# Start the application' >> /usr/local/bin/prod-startup.sh && \
    echo 'exec "$@"' >> /usr/local/bin/prod-startup.sh && \
    chmod +x /usr/local/bin/prod-startup.sh

# Switch back to application user
USER ${MIXSEEK_USERNAME}

# =============================================================================
# SECURITY FINAL HARDENING
# =============================================================================

# Switch back to root for final security configuration
USER root

# Remove any remaining development files and caches
RUN find /venv -name "*.pyc" -delete && \
    find /venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /venv -name "*.pyo" -delete && \
    rm -rf /root/.cache

# Set secure permissions
RUN chmod 750 /app && \
    chmod 755 /home/${MIXSEEK_USERNAME}/prod-startup.sh

# Final switch to application user
USER ${MIXSEEK_USERNAME}

# =============================================================================
# HEALTH CHECK
# =============================================================================

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('Production health check passed'); sys.exit(0)" || exit 1

# =============================================================================
# RUNTIME CONFIGURATION
# =============================================================================

# Expose application port (if needed - should be configured in docker run)
# EXPOSE 8000

# Use dumb-init as PID 1 to handle signals properly
ENTRYPOINT ["dumb-init", "/usr/local/bin/prod-startup.sh"]

# Default command - this should be overridden in production deployment
CMD ["python", "-c", "print('MixSeek-Core production container is running'); import time; time.sleep(86400)"]

# =============================================================================
# FINAL IMAGE OPTIMIZATION
# =============================================================================

# Set optimal file permissions
USER root
RUN find /app -type f -exec chmod 644 {} \; && \
    find /app -type d -exec chmod 755 {} \; && \
    find /venv -type f -exec chmod 644 {} \; && \
    find /venv -type d -exec chmod 755 {} \;

# Switch back to application user for runtime
USER ${MIXSEEK_USERNAME}

# Set working directory
WORKDIR /app