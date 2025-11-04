# Optimized DataHub Actions image with governance plugin
# Uses multi-stage caching to avoid rebuilding dependencies on code changes

FROM python:3.11-slim

# Install system dependencies required for DataHub Actions
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    make \
    librdkafka-dev \
    libssl-dev \
    curl \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package installer required by executor action)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    chmod +x /usr/local/bin/uv

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel build

# Set working directory
WORKDIR /app

# ==========================================
# OPTIMIZATION: Install dependencies FIRST
# This layer gets cached and only rebuilds when setup.py changes
# ==========================================

# Copy only dependency files first
COPY setup.py README.md ./
COPY src/datahub_actions/_version.py ./src/datahub_actions/_version.py

# Create minimal package structure for dependency installation
RUN mkdir -p src/datahub_actions/plugin/action && \
    touch src/datahub_actions/__init__.py && \
    touch src/datahub_actions/plugin/__init__.py && \
    touch src/datahub_actions/plugin/action/__init__.py

# Install dependencies (this gets cached!)
RUN pip install -e ".[data_quality,executor,ai_assistant]"

# ==========================================
# Copy source code AFTER dependencies installed
# Code changes don't invalidate dependency cache
# ==========================================

# Copy all source code
COPY src/ ./src/
COPY tests/ ./tests/

# ==========================================
# Copy and prepare startup scripts
# Use dos2unix instead of sed (faster and more reliable)
# ==========================================

COPY start_actions.sh start_ai_assistant.sh /usr/local/bin/
RUN dos2unix /usr/local/bin/start_actions.sh /usr/local/bin/start_ai_assistant.sh && \
    chmod +x /usr/local/bin/start_actions.sh /usr/local/bin/start_ai_assistant.sh

# ==========================================
# Build and install the actual package
# ==========================================

# Build the wheel (fast because dependencies already installed)
RUN python -m build --wheel

# Install the built wheel (overwrites the -e editable install)
RUN WHEEL=$(ls dist/*.whl) && pip install --force-reinstall "${WHEEL}"

# Build-time assertion: Verify entry points are registered
RUN python -c "from importlib.metadata import entry_points; \
    eps = [ep.name for ep in entry_points(group='datahub_actions.action.plugins')]; \
    required = ['data_quality', 'executor', 'governance']; \
    missing = [r for r in required if r not in eps]; \
    assert not missing, f'Missing entry points: {missing}. Found: {eps}'; \
    print(f'✓ Entry point verification passed: {required}')"

# Create datahub user for security
RUN useradd -m -u 1000 datahub && \
    mkdir -p /etc/datahub/actions/conf && \
    chown -R datahub:datahub /etc/datahub

# Switch to datahub user
USER datahub

# Default command to run both DataHub Actions server AND AI Assistant API
CMD ["/bin/bash", "-c", "/usr/local/bin/start_ai_assistant.sh & /usr/local/bin/start_actions.sh"]
