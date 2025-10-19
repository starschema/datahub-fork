# Clean DataHub Actions image with custom data_quality plugin
# Uses system Python only to avoid entry point discovery issues

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
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package installer required by executor action)
# Install to /usr/local/bin so it's available to all users
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    chmod +x /usr/local/bin/uv

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel build

# Set working directory
WORKDIR /app

# Copy startup script first (before copying all source code)
COPY start_actions.sh /usr/local/bin/start_actions.sh
# Convert Windows line endings to Unix and make executable
RUN sed -i 's/\r$//' /usr/local/bin/start_actions.sh && chmod +x /usr/local/bin/start_actions.sh

# Copy the entire datahub-actions source code
COPY . .

# Build the package as a wheel
RUN python -m build --wheel

# Force install the wheel with data_quality and executor extras
# The [data_quality] extra includes SQLAlchemy for data quality plugin
# The [executor] extra includes acryl-executor for UI-based ingestion
RUN WHEEL=$(ls dist/*.whl) && pip install --force-reinstall "${WHEEL}[data_quality,executor]"

# Build-time assertion: Verify both data_quality and executor entry points are registered
RUN python -c "from importlib.metadata import entry_points; \
    eps = [ep.name for ep in entry_points(group='datahub_actions.action.plugins')]; \
    assert 'data_quality' in eps, f'data_quality not found in entry points: {eps}'; \
    assert 'executor' in eps, f'executor not found in entry points: {eps}'; \
    print('✓ Entry point verification passed: data_quality and executor are registered')"

# Create datahub user for security
RUN useradd -m -u 1000 datahub && \
    mkdir -p /etc/datahub/actions/conf && \
    chown -R datahub:datahub /etc/datahub

# Switch to datahub user
USER datahub

# Default command to run DataHub Actions server with multiple pipelines
# Note: Configuration files are expected to be mounted in /etc/datahub/actions/conf/
CMD ["/usr/local/bin/start_actions.sh"]
