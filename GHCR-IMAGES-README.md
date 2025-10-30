# Custom DataHub Images on GitHub Container Registry (GHCR)

This document explains how to use pre-built custom DataHub images from GitHub Container Registry instead of building them locally (which can take over an hour).

## Table of Contents
- [Quick Start for Team Members](#quick-start-for-team-members)
- [Authentication](#authentication)
- [Available Images](#available-images)
- [Building and Pushing Images](#building-and-pushing-images)
- [Troubleshooting](#troubleshooting)

---

## Quick Start for Team Members

### Option 1: Automated Pull Script (Recommended)

The easiest way to get the pre-built images:

```bash
# Navigate to the repository
cd Custom-Datahub

# Run the pull script
./docker/pull-images.sh
```

This will:
1. Pull both custom images from GHCR
2. Tag them correctly for local use
3. Make them ready for use with docker-compose

### Option 2: Manual Pull

If you prefer to pull images manually:

```bash
# Pull frontend image
docker pull ghcr.io/starschema/custom-datahub-frontend-react:latest
docker tag ghcr.io/starschema/custom-datahub-frontend-react:latest custom-datahub-frontend-react:hcltech

# Pull actions image
docker pull ghcr.io/starschema/datahub-actions:latest
docker tag ghcr.io/starschema/datahub-actions:latest my-datahub-actions:latest
```

### Starting DataHub

After pulling images, start DataHub normally:

```bash
cd docker/quickstart
docker compose -f docker-compose.quickstart.yml up -d
```

Or with data quality features:

```bash
docker compose -f datahub-with-data-quality.yml up -d
```

---

## Authentication

### For Public Repositories

If the `starschema/Custom-Datahub` repository is public, **no authentication is required** - anyone can pull the images.

### For Private Repositories

If the repository is private, team members need to authenticate:

#### Step 1: Create GitHub Personal Access Token (PAT)

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name (e.g., "DataHub GHCR Access")
4. Select scopes:
   - ✅ `read:packages` - Download packages from GitHub Package Registry
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again!)

#### Step 2: Authenticate Docker with GHCR

```bash
# Using your GitHub username and the PAT you just created
echo YOUR_PERSONAL_ACCESS_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

Example:
```bash
echo ghp_xxxxxxxxxxxxxxxxxxxx | docker login ghcr.io -u jdoe --password-stdin
```

You should see: `Login Succeeded`

#### Step 3: Verify Access

Test that you can pull images:

```bash
docker pull ghcr.io/starschema/custom-datahub-frontend-react:latest
```

### Access Permissions

**Repository Owners/Maintainers:** If a team member can't access the images, grant them access:

1. Go to the GitHub repository: https://github.com/starschema/Custom-Datahub
2. Click "Packages" on the right sidebar
3. Click on the image name (e.g., "custom-datahub-frontend-react")
4. Click "Package settings"
5. Under "Manage Access", click "Add people or teams"
6. Add your team member with at least "Read" permission

**Note:** Anyone with read access to the repository should automatically have read access to the packages.

---

## Available Images

### Custom Frontend Image (HCLTech Branding)

**Image:** `ghcr.io/starschema/custom-datahub-frontend-react`

**Features:**
- HCLTech logo and branding
- Custom purple theme (#6B4EFF)
- Customized navigation and UI elements

**Tags:**
- `latest` - Most recent build
- `hcltech` - Stable HCLTech branded version
- `<git-sha>` - Specific commit versions (e.g., `abc1234`)

**Supported Architectures:**
- `linux/amd64` - Intel/AMD 64-bit (Linux servers, Intel Macs)
- `linux/arm64` - ARM 64-bit (Apple Silicon M1/M2/M3 Macs)

Docker automatically pulls the correct architecture for your system.

**Size:** ~1.22GB (per architecture)

### Custom Actions Image (Data Quality + Executor)

**Image:** `ghcr.io/starschema/datahub-actions`

**Features:**
- Data quality action for automated testing
- Executor action for UI-based ingestion
- Pre-configured with all necessary dependencies

**Tags:**
- `latest` - Most recent build
- `<git-sha>` - Specific commit versions (e.g., `abc1234`)

**Size:** ~1.42GB

---

## Building and Pushing Images

### For Maintainers: Building and Pushing to GHCR

If you've made changes to the frontend or actions code and need to push new images:

#### Prerequisites
1. Have push access to the `starschema/Custom-Datahub` repository
2. Authenticate with GHCR (with `write:packages` permission)
3. Docker with Buildx support is installed and running (Docker 19.03+)

#### Build and Push Both Images

```bash
cd Custom-Datahub/docker

# Build and push both images
./build-push-images.sh
```

This will:
1. Build custom frontend image for **multiple platforms** (linux/amd64, linux/arm64)
2. Build custom actions image for native platform
3. Tag them with git SHA and `latest`
4. Push to GHCR

**Note:** Multi-platform frontend builds take longer (~2-3x) but ensure compatibility across Intel/AMD and Apple Silicon Macs.

#### Build and Push Specific Images

```bash
# Build and push only frontend
./build-push-images.sh --frontend-only

# Build and push only actions
./build-push-images.sh --actions-only

# Build without pushing (for testing)
./build-push-images.sh --no-push

# Build with custom tag
./build-push-images.sh --tag v1.2.3
```

#### Verify Images Were Pushed

Check the packages on GitHub:
- https://github.com/orgs/rykalc/packages?repo_name=Custom-Datahub

---

## Troubleshooting

### "no basic auth credentials" or "authentication required"

**Problem:** Docker can't authenticate with GHCR.

**Solution:**
1. Authenticate using the steps in [Authentication](#authentication)
2. Make sure your PAT hasn't expired
3. Verify your PAT has `read:packages` scope

### "manifest unknown" or "not found"

**Problem:** Image doesn't exist or you don't have access.

**Solutions:**
1. Check the image name is correct
2. Verify you have read access to the repository/package
3. Contact repository owner to grant you access

### "no matching manifest for linux/amd64" or Platform Mismatch

**Problem:** Image was built for a different CPU architecture than your system.

**Solution (for frontend images):**
As of the latest updates, frontend images are **multi-architecture** and support both:
- `linux/amd64` (Intel/AMD processors)
- `linux/arm64` (Apple Silicon M1/M2/M3)

If you see this error:
1. Pull the latest image version:
   ```bash
   docker pull ghcr.io/starschema/custom-datahub-frontend-react:latest
   ```
2. Verify the image has multi-arch support:
   ```bash
   docker manifest inspect ghcr.io/starschema/custom-datahub-frontend-react:latest | grep -A 3 "platform"
   ```
3. If the image is older (pre-multi-arch), ask maintainers to rebuild and push a new version

### Images Pull But Don't Work

**Problem:** Wrong tag or outdated image.

**Solutions:**
1. Pull the latest version:
   ```bash
   docker pull ghcr.io/starschema/custom-datahub-frontend-react:latest --no-cache
   docker pull ghcr.io/starschema/datahub-actions:latest --no-cache
   ```
2. Check which version you're running:
   ```bash
   docker images | grep -E "(custom-datahub-frontend|datahub-actions)"
   ```

### "Cannot connect to the Docker daemon"

**Problem:** Docker is not running.

**Solution:** Start Docker Desktop and wait for it to fully initialize.

### Pull is Very Slow

**Problem:** Network speed or Docker daemon issues.

**Solutions:**
1. Check your internet connection
2. Try a different network
3. Restart Docker Desktop
4. Use a Docker mirror/proxy if available in your organization

### Need to Use Local Images Instead

If you need to switch back to using locally-built images:

```bash
# Set environment variables
export DATAHUB_FRONTEND_IMAGE=custom-datahub-frontend-react:hcltech
export DATAHUB_ACTIONS_IMAGE=my-datahub-actions:latest

# Start docker-compose
docker compose -f docker-compose.quickstart.yml up -d
```

Or build images locally:

```bash
./docker/build-push-images.sh --no-push
```

---

## Image Update Policy

### When Are New Images Built?

Images are rebuilt and pushed when:
- Frontend code is modified (branding, theme, UI changes)
- Actions configurations are updated
- Dependencies are upgraded
- Bug fixes or security patches are applied

### How to Know When to Pull New Images

Team members should pull new images when:
1. **After pulling latest code from GitHub**
   ```bash
   git pull origin master
   ./docker/pull-images.sh
   ```

2. **When you see build-related changes in commits**
   - Look for commits mentioning "frontend", "actions", "docker", or "image"

3. **When maintainers announce new image versions**
   - Check team communication channels
   - Look at GitHub releases/tags

### Checking Image Age

See when your local images were pulled:

```bash
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}" | grep -E "(custom-datahub|datahub-actions)"
```

Compare with latest commit on GitHub to see if you need to update.

---

## Best Practices

### For Team Members

1. **Pull images regularly** - Before starting work on DataHub
2. **Use the pull script** - Easier than manual commands
3. **Don't build unless necessary** - Building takes over an hour
4. **Report issues** - If images don't work, notify the team

### For Maintainers

1. **Push after significant changes** - Keep team members up to date
2. **Tag releases properly** - Use semantic versioning for releases
3. **Test before pushing** - Build locally with `--no-push` first
4. **Document changes** - Update CHANGELOG when pushing new images
5. **Communicate updates** - Let team know when new images are available

---

## Support

If you have issues:

1. Check this troubleshooting guide
2. Ask in the team Slack/Teams channel
3. Contact the repository maintainers
4. Open an issue on GitHub

---

## Additional Resources

- [Docker Authentication Documentation](https://docs.docker.com/engine/reference/commandline/login/)
- [GitHub Packages Documentation](https://docs.github.com/en/packages)
- [DataHub Quickstart Guide](./QUICKSTART.md)
- [Building Docker Images](./docker/README.md)
