# GHCR Setup Summary

This document summarizes the GitHub Container Registry (GHCR) setup for custom DataHub images.

## What Was Configured

### 1. Build and Push Scripts

**Location:** `docker/build-push-images.sh`

A comprehensive script that:
- Builds custom frontend image for **multiple platforms** (linux/amd64, linux/arm64)
- Builds custom actions image for native platform
- Tags them with git SHA and latest
- Pushes to GitHub Container Registry
- Supports selective building (frontend-only, actions-only)
- Provides colored output and progress tracking
- Uses Docker Buildx for multi-platform builds

**Usage:**
```bash
cd docker
./build-push-images.sh              # Build and push both images
./build-push-images.sh --no-push    # Build locally without pushing
./build-push-images.sh --frontend-only  # Only build frontend
./build-push-images.sh --actions-only   # Only build actions
```

### 2. Pull Script for Team Members

**Location:** `docker/pull-images.sh`

A simple script for team members to pull pre-built images:
- Pulls both custom images from GHCR
- Tags them correctly for local use
- Provides clear feedback on progress

**Usage:**
```bash
./docker/pull-images.sh        # Pull latest images
./docker/pull-images.sh abc1234  # Pull specific version
```

### 3. Updated Docker Compose Files

**Files Updated:**
- `datahub-with-data-quality.yml`
- `docker/quickstart/docker-compose-data-quality.override.yml`

**Changes:**
- Default to GHCR images instead of local builds
- Support environment variables to override with local images
- Added clear comments on how to switch between GHCR and local images

**Environment Variables:**
```bash
# Use local images instead of GHCR
export DATAHUB_FRONTEND_IMAGE=custom-datahub-frontend-react:hcltech
export DATAHUB_ACTIONS_IMAGE=my-datahub-actions:latest
```

### 4. Comprehensive Documentation

**Location:** `GHCR-IMAGES-README.md`

Complete guide covering:
- Quick start for team members
- Authentication for public and private repositories
- Step-by-step PAT creation and GHCR login
- Available images and their features
- Building and pushing images
- Troubleshooting common issues
- Best practices for team and maintainers

**Updated:** `QUICKSTART.md`
- Added step to pull images before starting DataHub
- References GHCR documentation

### 5. GitHub Actions Automation

**Location:** `.github/workflows/build-push-custom-images.yml`

Automated CI/CD workflow that:
- Detects when frontend or actions code changes
- Builds only the images that need updating
- Builds frontend for **multiple platforms** (linux/amd64, linux/arm64)
- Pushes to GHCR automatically on commits to main/master
- Supports manual triggering
- Builds on releases/tags
- Uses Docker Buildx with GitHub's cache for faster builds
- Requires no secrets (uses automatic GITHUB_TOKEN)

**Triggers:**
- Push to main/master branch (only if relevant files changed)
- Manual workflow dispatch
- New releases

---

## Image Registry Details

### Organization and Repository
- GitHub Organization: `starschema`
- GitHub Repository: `Custom-Datahub`
- Registry: GitHub Container Registry (ghcr.io)

### Image Paths

**Frontend Image (Multi-Architecture):**
```
ghcr.io/starschema/custom-datahub-frontend-react:latest
ghcr.io/starschema/custom-datahub-frontend-react:hcltech
ghcr.io/starschema/custom-datahub-frontend-react:<git-sha>
```

**Supported Platforms:**
- `linux/amd64` - Intel/AMD 64-bit (Linux servers, Intel Macs)
- `linux/arm64` - ARM 64-bit (Apple Silicon M1/M2/M3 Macs)

Docker automatically selects the correct architecture when pulling.

**Actions Image (Native Platform):**
```
ghcr.io/starschema/datahub-actions:latest
ghcr.io/starschema/datahub-actions:<git-sha>
```

---

## Next Steps

### For You (Maintainer)

#### 1. **Initial Image Push** (One-time setup)

First, build the images locally to ensure everything works:

```bash
cd docker
./build-push-images.sh --no-push
```

If successful, authenticate with GHCR and push:

```bash
# Authenticate (if not already done)
# Use a Personal Access Token with write:packages permission
echo YOUR_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Build and push images
./build-push-images.sh
```

#### 2. **Verify Images on GitHub**

After pushing, verify images are visible:
- Go to: https://github.com/orgs/starschema/packages
- You should see:
  - `custom-datahub-frontend-react`
  - `datahub-actions`

#### 3. **Set Package Visibility** (if needed)

If the repository is private:
1. Go to each package's settings
2. Set visibility to match repository (public/private)
3. Ensure team members have read access

#### 4. **Test the Pull Script**

From a clean state (delete local images):

```bash
# Remove local images
docker rmi custom-datahub-frontend-react:hcltech my-datahub-actions:latest

# Pull from GHCR
./docker/pull-images.sh

# Verify images exist
docker images | grep -E "(custom-datahub|datahub-actions)"
```

#### 5. **Enable GitHub Actions** (optional but recommended)

If you want automatic builds:
1. Go to repository Settings → Actions → General
2. Enable "Read and write permissions" for workflows
3. Save changes
4. The workflow will automatically run on the next push to main/master

---

### For Your Team Members

Share these instructions with your colleagues:

#### Quick Start (2 minutes)

```bash
# 1. Clone repository (if not already done)
git clone https://github.com/starschema/Custom-Datahub.git
cd Custom-Datahub

# 2. Authenticate with GHCR (only if repository is private)
echo YOUR_GITHUB_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# 3. Pull pre-built images
./docker/pull-images.sh

# 4. Start DataHub
cd docker/quickstart
docker compose -f docker-compose.quickstart.yml up -d
```

#### For Private Repository Access

Team members need a GitHub Personal Access Token:
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token with `read:packages` scope
3. Use it to authenticate with GHCR (see Quick Start above)

**See `GHCR-IMAGES-README.md` for detailed instructions.**

---

## Benefits

### Time Savings
- **Building locally:** ~1+ hour
- **Pulling from GHCR:** ~2-5 minutes
- **Savings per team member:** ~55-58 minutes

### Other Advantages
1. **Consistency:** Everyone uses the same images
2. **Onboarding:** New team members get started faster
3. **Cross-Platform:** Works on both Intel/AMD and Apple Silicon Macs
4. **CI/CD:** Automated builds ensure images are always up to date
5. **Version control:** Images tagged with git commits for reproducibility
6. **Bandwidth:** Team members download once, not build repeatedly

---

## File Structure

```
Custom-Datahub/
├── .github/
│   └── workflows/
│       └── build-push-custom-images.yml   # GitHub Actions workflow
├── docker/
│   ├── build-push-images.sh               # Build and push script
│   ├── pull-images.sh                     # Pull script for team
│   └── quickstart/
│       └── docker-compose-data-quality.override.yml  # Updated for GHCR
├── datahub-with-data-quality.yml          # Updated for GHCR
├── GHCR-IMAGES-README.md                  # Complete documentation
├── GHCR-SETUP-SUMMARY.md                  # This file
└── QUICKSTART.md                          # Updated with pull step
```

---

## Maintenance

### When to Rebuild Images

Rebuild and push new images when:
- Frontend code changes (branding, theme, UI)
- Actions code changes
- Dependencies are updated
- Security patches are applied

### Manual Rebuild

```bash
cd docker
./build-push-images.sh
```

### Automatic Rebuild

If GitHub Actions is enabled, images automatically rebuild when relevant code changes on main/master branch.

### Notifying Team

When new images are pushed, notify team members:
```
📦 New custom images available!

Please pull the latest images:
./docker/pull-images.sh

Changes: [describe what changed]
```

---

## Troubleshooting

### Common Issues

1. **"Authentication required"**
   - Team member needs to login to GHCR
   - See `GHCR-IMAGES-README.md` for authentication steps

2. **"Cannot find images"**
   - Images haven't been pushed yet
   - Run `./build-push-images.sh` to build and push
   - Or check package visibility on GitHub

3. **Build script fails**
   - Check Docker is running
   - Verify you have push permissions
   - Try building without pushing: `--no-push`

4. **GitHub Actions fails**
   - Check workflow permissions in repository settings
   - Verify GITHUB_TOKEN has package write permissions

5. **"no matching manifest for linux/amd64" or platform errors**
   - Image was built before multi-arch support was added
   - Rebuild and push a new version: `./build-push-images.sh`
   - Verify multi-arch manifest: `docker manifest inspect ghcr.io/starschema/custom-datahub-frontend-react:latest`

---

## Support

For issues or questions:
1. Check `GHCR-IMAGES-README.md` for detailed documentation
2. Review this summary for quick reference
3. Contact repository maintainer
4. Open an issue on GitHub

---

## Success Criteria

✅ You're all set up when:
- [ ] Images successfully pushed to GHCR
- [ ] Team members can pull images without building
- [ ] Docker compose files reference GHCR images
- [ ] GitHub Actions workflow enabled (optional)
- [ ] Team members notified and have documentation
- [ ] At least one team member successfully pulled and started DataHub

---

**Last Updated:** $(date)
**Repository:** https://github.com/starschema/Custom-Datahub
