#!/bin/bash
# Startup script for running multiple DataHub Actions pipelines
# This script starts both executor and data_quality actions

set -euo pipefail

echo "Starting DataHub Actions with multiple pipelines..."

# Array of configuration files to run
CONFIGS=(
    "/etc/datahub/actions/conf/executor-action.yaml"
    "/etc/datahub/actions/conf/data-quality-action.yaml"
    "/etc/datahub/actions/conf/governance-action.yaml"
)

# Build the command with multiple --config flags
CMD="datahub-actions actions run"
for config in "${CONFIGS[@]}"; do
    if [ -f "$config" ]; then
        echo "Found configuration: $config"
        CMD="$CMD --config $config"
    else
        echo "Warning: Configuration file not found: $config"
    fi
done

echo "Executing: $CMD"
exec $CMD
