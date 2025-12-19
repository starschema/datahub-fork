# Secret Encryption Key Migration Guide

## Overview

This migration fixes a critical bug where all secrets (Snowflake credentials, database passwords, API keys) were lost on every container restart due to auto-generated encryption keys.

## Impact

**All existing secrets will become unreadable after this update.** This is a one-time migration that prevents future secret loss.

## Pre-Migration Checklist

Before updating, document all your current credentials:

### 1. Snowflake Credentials
- [ ] Account ID (e.g., `ORGNAME-ACCOUNTNAME`)
- [ ] Username
- [ ] Password
- [ ] Warehouse
- [ ] Role
- [ ] Databases being ingested

### 2. Other Data Source Credentials
- [ ] MySQL/PostgreSQL databases
- [ ] S3 access keys
- [ ] API tokens
- [ ] Any other ingestion source credentials

### 3. Export Current Configuration
```bash
# Before stopping containers, export ingestion source configs
docker exec custom-datahub-datahub-gms-1 curl -s http://localhost:8080/config > datahub-config-backup.json
```

## Migration Steps

### Step 1: Backup Current State
```bash
# Stop containers but keep data
docker-compose -f datahub-with-data-quality.yml down

# Backup volumes (optional but recommended)
docker run --rm -v custom-datahub_mysqldata:/data -v $(pwd):/backup \
  alpine tar czf /backup/mysql-backup-$(date +%Y%m%d).tar.gz /data
```

### Step 2: Update to New Version
```bash
# Pull latest changes
git pull

# The .env file should already exist with SECRET_SERVICE_ENCRYPTION_KEY
# If not, it will be created automatically with a secure random key
```

### Step 3: Start Updated Containers
```bash
docker-compose -f datahub-with-data-quality.yml up -d
```

### Step 4: Re-enter All Secrets

#### Via DataHub UI (Recommended)
1. Go to http://localhost:9002
2. Login with `datahub` / `datahub`
3. Navigate to **Ingestion → Secrets**
4. Delete old unreadable secrets
5. Create new secrets with your documented credentials
6. Navigate to **Ingestion → Sources**
7. Re-create or update each ingestion source with the new secrets

#### Via CLI (Alternative)
Update your recipe files with credentials and run:
```bash
datahub ingest -c your-recipe.yml
```

### Step 5: Verify
1. Run a test ingestion to verify credentials work
2. Check that secrets persist after container restart:
   ```bash
   docker-compose -f datahub-with-data-quality.yml restart
   # Secrets should still work after restart
   ```

## Post-Migration

### ✅ Benefits After Migration
- Secrets persist across all container restarts
- Production-ready secret management
- No more credential re-entry on every restart

### 🔒 Security Best Practices
1. **Never commit `.env` file** (already in `.gitignore`)
2. **Backup your `.env` file** securely (contains SECRET_SERVICE_ENCRYPTION_KEY)
3. **Rotate credentials** if you suspect they may have been exposed

## Troubleshooting

### Problem: Can't remember credentials
**Solution:** Check these sources:
- Password manager (1Password, LastPass, etc.)
- Secret vaults (AWS Secrets Manager, HashiCorp Vault)
- Team documentation (Confluence, Notion, wiki)
- Ask the person who originally set up the ingestion
- Check Snowflake/database admin to reset passwords

### Problem: Secrets still not persisting after migration
**Solution:** Verify encryption key is set:
```bash
docker exec custom-datahub-datahub-gms-1 printenv SECRET_SERVICE_ENCRYPTION_KEY
# Should output the key from .env file
```

### Problem: Different encryption key on different services
**Solution:** Ensure all services use the same key:
```bash
# Both should output the same value
docker exec custom-datahub-datahub-gms-1 printenv SECRET_SERVICE_ENCRYPTION_KEY
docker exec custom-datahub-datahub-frontend-react-1 printenv SECRET_SERVICE_ENCRYPTION_KEY
```

## Need Help?

- Open an issue on GitHub
- Contact your DataHub administrator
- Check DataHub Slack community

## Future Updates

After this migration, future updates will NOT require re-entering secrets as long as:
1. You keep the same SECRET_SERVICE_ENCRYPTION_KEY in .env
2. You don't delete the MySQL volume (where encrypted secrets are stored)
