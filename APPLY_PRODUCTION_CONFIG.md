# Apply Production Configuration Changes

## ⚠️ IMPORTANT: Your containers are running with OLD configuration!

The verification script detected that your containers are still using the old configuration:
- ❌ nginx is on port **9001** (should be **9002**)
- ❌ datahub-frontend-react is **exposed** on 127.0.0.1:9002 (should be **internal only**)
- ❌ datahub-gms is **exposed** on port 8888 (should be **internal only** - SECURITY RISK!)

## To Apply New Production Configuration

### Option 1: Recreate All Containers (Recommended)

This will apply all security fixes and configuration changes. **Data is preserved** in volumes.

```bash
# Stop and remove containers (keeps data)
docker compose -f datahub-with-data-quality.yml down

# Start with new configuration
docker compose -f datahub-with-data-quality.yml up -d

# Monitor startup
docker compose -f datahub-with-data-quality.yml logs -f
```

**Wait time**: 2-3 minutes for all services to become healthy

### Option 2: Rolling Update (Less Downtime)

Update specific services one at a time:

```bash
# Update nginx (changes port 9001 → 9002)
docker compose -f datahub-with-data-quality.yml up -d --force-recreate nginx

# Remove port exposures (security fix)
docker compose -f datahub-with-data-quality.yml up -d --force-recreate datahub-frontend-react datahub-gms datahub-actions
```

## Verify New Configuration

After recreating containers, run:

```bash
# Windows
verify-production.bat

# Linux/Mac
./verify-production.sh
```

Expected changes:
```
nginx: port 9002 (was 9001) ✓
datahub-frontend-react: no external port (was 127.0.0.1:9002) ✓
datahub-gms: no external port (was 0.0.0.0:8888) ✓
datahub-actions: no external port (was 127.0.0.1:8082) ✓
```

## Access Application After Update

- **New URL**: http://localhost:9002
- **Old URL**: ~~http://localhost:9001~~ (no longer works)

## What Changed

| Component | Old Config | New Config | Reason |
|-----------|-----------|------------|---------|
| nginx | Port 9001 | Port 9002 | Backward compatibility (was your standard port) |
| datahub-frontend | Exposed 127.0.0.1:9002 | Internal only | Security - access via nginx |
| datahub-gms | Exposed 0.0.0.0:8888 | Internal only | **CRITICAL** - prevents auth bypass |
| datahub-actions | Exposed 127.0.0.1:8082 | Internal only | Security - access via nginx |
| All services | Mixed restart policies | `unless-stopped` | Auto-recovery from crashes |
| Secrets | Hardcoded | Environment vars | Security - no secrets in repo |

## Troubleshooting

### Port 9002 Already in Use
```bash
# Windows - find process using port 9002
netstat -ano | findstr 9002

# Kill process (replace PID)
taskkill /PID <pid> /F

# Or use different port (add to .env)
echo NGINX_PORT=9003 >> .env
```

### Can't Access Application After Update
```bash
# Check nginx is running on correct port
docker compose -f datahub-with-data-quality.yml ps nginx

# Check logs
docker compose -f datahub-with-data-quality.yml logs nginx

# Verify port mapping
docker port datahub-nginx-1
```

### Services Not Starting
```bash
# Check which service is failing
docker compose -f datahub-with-data-quality.yml ps

# View logs for failed service
docker compose -f datahub-with-data-quality.yml logs <service-name>

# Common issues:
# - MySQL password changed: remove volume and restart
# - Out of memory: increase Docker memory limit
# - Port conflict: check ports in use
```

## Rollback (If Needed)

If you need to rollback to old configuration:

```bash
# Stop new containers
docker compose -f datahub-with-data-quality.yml down

# Revert git changes
git checkout datahub-with-data-quality.yml nginx/nginx.conf

# Start old configuration
docker compose -f datahub-with-data-quality.yml up -d
```

**Note**: You'll lose the security improvements and auto-restart features.
