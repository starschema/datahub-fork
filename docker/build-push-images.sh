#!/bin/bash
# Build, tag, and push custom DataHub images to GitHub Container Registry (GHCR)
#
# This script builds the custom DataHub images and pushes them to GHCR so team members
# can pull pre-built images instead of building locally.
#
# Prerequisites:
#   1. Docker with Buildx support is installed and running (Docker 19.03+)
#   2. Authenticated with GHCR: docker login ghcr.io -u YOUR_GITHUB_USERNAME
#   3. Have push permissions to the starschema/Custom-Datahub repository
#
# Note: All images are built for multi-platform (linux/amd64, linux/arm64)
#
# Usage:
#   ./build-push-images.sh [OPTIONS]
#
# Options:
#   --frontend-only    Build and push only the frontend image
#   --actions-only     Build and push only the actions image
#   --no-push          Build and tag images but don't push to registry
#   --tag TAG          Use custom tag instead of default (git SHA + latest)
#   --help             Show this help message

set -euo pipefail

# Configuration
GITHUB_USER="starschema"
GITHUB_REPO="Custom-Datahub"
REGISTRY="ghcr.io"

# Image names
FRONTEND_IMAGE_NAME="custom-datahub-frontend-react"
ACTIONS_IMAGE_NAME="datahub-actions"

# Full registry paths
FRONTEND_REGISTRY_IMAGE="${REGISTRY}/${GITHUB_USER}/${FRONTEND_IMAGE_NAME}"
ACTIONS_REGISTRY_IMAGE="${REGISTRY}/${GITHUB_USER}/${ACTIONS_IMAGE_NAME}"

# Get git commit SHA for tagging
GIT_SHA=$(git rev-parse --short HEAD)
GIT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
DEV_VERSION="1!0.0.0.dev0"

# Default settings
BUILD_FRONTEND=true
BUILD_ACTIONS=true
PUSH_IMAGES=true
CUSTOM_TAG=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    grep '^#' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --frontend-only)
            BUILD_FRONTEND=true
            BUILD_ACTIONS=false
            shift
            ;;
        --actions-only)
            BUILD_FRONTEND=false
            BUILD_ACTIONS=true
            shift
            ;;
        --no-push)
            PUSH_IMAGES=false
            shift
            ;;
        --tag)
            CUSTOM_TAG="$2"
            shift 2
            ;;
        --help)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Determine tags to use
if [ -n "$CUSTOM_TAG" ]; then
    TAGS=("$CUSTOM_TAG")
elif [ -n "$GIT_TAG" ]; then
    TAGS=("$GIT_TAG" "latest")
else
    TAGS=("$GIT_SHA" "latest")
fi

log_info "Tags to be used: ${TAGS[*]}"

# Check if Docker Buildx is available
check_docker_buildx() {
    log_info "Checking Docker Buildx support..."
    if ! docker buildx version >/dev/null 2>&1; then
        log_error "Docker Buildx is not available"
        log_error "Multi-platform builds require Docker 19.03+ with Buildx"
        log_error "See: https://docs.docker.com/buildx/working-with-buildx/"
        exit 1
    fi
    log_success "Docker Buildx is available"
}

# Check if authenticated with GHCR
check_ghcr_auth() {
    if [ "$PUSH_IMAGES" = true ]; then
        log_info "Checking GHCR authentication..."
        if ! docker login ghcr.io --get-login >/dev/null 2>&1; then
            log_warn "Not authenticated with GHCR. Run: docker login ghcr.io -u YOUR_GITHUB_USERNAME"
            read -p "Do you want to continue without pushing? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            PUSH_IMAGES=false
        else
            log_success "GHCR authentication verified"
        fi
    fi
}

# Build frontend image
build_frontend() {
    log_info "Building custom DataHub frontend image (multi-platform: linux/amd64, linux/arm64)..."
    log_info "This includes HCLTech branding and theme customizations"

    # The frontend needs to be built first with gradle
    log_warn "Note: This requires the frontend to be pre-built"
    log_warn "If the build fails, run: cd ../.. && ./gradlew :datahub-frontend:build"

    # Build all tags for multi-platform
    cd ../..

    # Prepare all tags for buildx
    BUILDX_TAGS=""
    for tag in "${TAGS[@]}"; do
        BUILDX_TAGS="${BUILDX_TAGS} -t ${FRONTEND_REGISTRY_IMAGE}:${tag}"
    done
    BUILDX_TAGS="${BUILDX_TAGS} -t ${FRONTEND_REGISTRY_IMAGE}:hcltech"

    if [ "$PUSH_IMAGES" = true ]; then
        log_info "Building and pushing multi-platform image to registry..."
        docker buildx build \
            -f docker/datahub-frontend/Dockerfile \
            --platform linux/amd64,linux/arm64 \
            --build-arg APP_ENV=prod \
            ${BUILDX_TAGS} \
            --push \
            .
    else
        log_warn "Building for host platform only (--no-push mode)"
        docker buildx build \
            -f docker/datahub-frontend/Dockerfile \
            --build-arg APP_ENV=prod \
            -t "${FRONTEND_IMAGE_NAME}:hcltech" \
            --load \
            .

        # Tag for GHCR (local only)
        for tag in "${TAGS[@]}"; do
            log_info "Tagging frontend image as ${FRONTEND_REGISTRY_IMAGE}:${tag}"
            docker tag "${FRONTEND_IMAGE_NAME}:hcltech" "${FRONTEND_REGISTRY_IMAGE}:${tag}"
        done
        docker tag "${FRONTEND_IMAGE_NAME}:hcltech" "${FRONTEND_REGISTRY_IMAGE}:hcltech"
    fi

    log_success "Frontend image built successfully"
    cd docker
}

# Build actions image
build_actions() {
    log_info "Building custom DataHub actions image (multi-platform: linux/amd64, linux/arm64)..."
    log_info "This includes data quality and executor actions"

    # Build the Docker image from root
    cd ../..

    # Prepare all tags for buildx
    BUILDX_TAGS=""
    for tag in "${TAGS[@]}"; do
        BUILDX_TAGS="${BUILDX_TAGS} -t ${ACTIONS_REGISTRY_IMAGE}:${tag}"
    done

    if [ "$PUSH_IMAGES" = true ]; then
        log_info "Building and pushing multi-platform image to registry..."
        docker buildx build \
            -f docker/datahub-actions/Dockerfile \
            --platform linux/amd64,linux/arm64 \
            --build-arg APP_ENV=full \
            --build-arg RELEASE_VERSION="${DEV_VERSION}" \
            --build-arg BUNDLED_CLI_VERSION="${DEV_VERSION}" \
            ${BUILDX_TAGS} \
            --push \
            .
    else
        log_warn "Building for host platform only (--no-push mode)"
        docker buildx build \
            -f docker/datahub-actions/Dockerfile \
            --build-arg APP_ENV=full \
            --build-arg RELEASE_VERSION="${DEV_VERSION}" \
            --build-arg BUNDLED_CLI_VERSION="${DEV_VERSION}" \
            -t "${ACTIONS_IMAGE_NAME}:latest" \
            --load \
            .

        # Tag for GHCR (local only)
        for tag in "${TAGS[@]}"; do
            log_info "Tagging actions image as ${ACTIONS_REGISTRY_IMAGE}:${tag}"
            docker tag "${ACTIONS_IMAGE_NAME}:latest" "${ACTIONS_REGISTRY_IMAGE}:${tag}"
        done
    fi

    log_success "Actions image built successfully"
    cd docker
}

# Push images to GHCR
push_images() {
    if [ "$PUSH_IMAGES" = false ]; then
        log_warn "Skipping push (--no-push flag or not authenticated)"
        log_info "Note: Multi-platform builds are pushed during the build step when using --push"
        return
    fi

    # Note: For multi-platform builds, images are already pushed during docker buildx build
    # with the --push flag, so no separate push step is needed
    log_info "Images were pushed during the build step (multi-platform builds)"
}

# Show summary
show_summary() {
    echo
    log_success "=========================================="
    log_success "Build and Push Complete!"
    log_success "=========================================="
    echo

    if [ "$BUILD_FRONTEND" = true ]; then
        echo "Frontend Image:"
        for tag in "${TAGS[@]}"; do
            echo "  - ${FRONTEND_REGISTRY_IMAGE}:${tag}"
        done
        echo "  - ${FRONTEND_REGISTRY_IMAGE}:hcltech"
    fi

    if [ "$BUILD_ACTIONS" = true ]; then
        echo
        echo "Actions Image:"
        for tag in "${TAGS[@]}"; do
            echo "  - ${ACTIONS_REGISTRY_IMAGE}:${tag}"
        done
    fi

    echo
    echo "Team members can now pull these images with:"
    if [ "$BUILD_FRONTEND" = true ]; then
        echo "  docker pull ${FRONTEND_REGISTRY_IMAGE}:latest"
    fi
    if [ "$BUILD_ACTIONS" = true ]; then
        echo "  docker pull ${ACTIONS_REGISTRY_IMAGE}:latest"
    fi
    echo
    echo "See GHCR-IMAGES-README.md for full documentation"
}

# Main execution
main() {
    log_info "Starting build and push process..."
    log_info "Repository: ${GITHUB_USER}/${GITHUB_REPO}"
    log_info "Git SHA: ${GIT_SHA}"
    [ -n "$GIT_TAG" ] && log_info "Git Tag: ${GIT_TAG}"

    check_docker_buildx
    check_ghcr_auth

    if [ "$BUILD_FRONTEND" = true ]; then
        build_frontend
    fi

    if [ "$BUILD_ACTIONS" = true ]; then
        build_actions
    fi

    push_images
    show_summary
}

# Run main function
main
