#!/bin/bash
# Pull pre-built custom DataHub images from GitHub Container Registry (GHCR)
#
# This script pulls the pre-built custom DataHub images so you don't have to build them locally.
#
# Prerequisites:
#   1. Docker is installed and running
#   2. For private repos, authenticate with GHCR:
#      echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
#
# Usage:
#   ./pull-images.sh [TAG]
#
# Arguments:
#   TAG    Optional: specific tag to pull (default: latest)
#
# Examples:
#   ./pull-images.sh          # Pull latest images
#   ./pull-images.sh abc1234  # Pull images tagged with git commit abc1234

set -euo pipefail

# Configuration
GITHUB_USER="starschema"
REGISTRY="ghcr.io"

# Image names
FRONTEND_REGISTRY_IMAGE="${REGISTRY}/${GITHUB_USER}/custom-datahub-frontend-react"
ACTIONS_REGISTRY_IMAGE="${REGISTRY}/${GITHUB_USER}/datahub-actions"

# Default tag
TAG="${1:-latest}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_warn "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
}

# Pull images
pull_images() {
    log_info "Pulling custom DataHub images from GHCR..."
    log_info "Tag: ${TAG}"
    echo

    log_info "Pulling frontend image..."
    docker pull "${FRONTEND_REGISTRY_IMAGE}:${TAG}"
    # Also pull with hcltech tag and tag locally
    docker tag "${FRONTEND_REGISTRY_IMAGE}:${TAG}" "custom-datahub-frontend-react:hcltech"
    log_success "Frontend image pulled and tagged as custom-datahub-frontend-react:hcltech"
    echo

    log_info "Pulling actions image..."
    docker pull "${ACTIONS_REGISTRY_IMAGE}:${TAG}"
    # Tag locally for compatibility with docker-compose files
    docker tag "${ACTIONS_REGISTRY_IMAGE}:${TAG}" "my-datahub-actions:latest"
    log_success "Actions image pulled and tagged as my-datahub-actions:latest"
}

# Show summary
show_summary() {
    echo
    log_success "=========================================="
    log_success "Images Pulled Successfully!"
    log_success "=========================================="
    echo
    echo "Local images available:"
    echo "  - custom-datahub-frontend-react:hcltech"
    echo "  - my-datahub-actions:latest"
    echo
    echo "You can now start DataHub using docker-compose"
    echo "See QUICKSTART.md for more information"
}

# Main execution
main() {
    check_docker
    pull_images
    show_summary
}

# Run main function
main
