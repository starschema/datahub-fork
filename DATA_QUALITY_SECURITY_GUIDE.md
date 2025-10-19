# Data Quality Testing - Security Guide

## Credential Management Strategy

### Configuration File Approach (Recommended)

We use **explicit connector configuration in YAML** instead of environment variables for several reasons:

✅ **Pros:**
- Clean, centralized configuration
- Easy to read and maintain
- No shell escaping issues
- Works consistently across platforms
- Simple Docker volume mount

⚠️ **Security Requirements:**
- **NEVER commit config file with credentials to git**
- Use `.gitignore` to exclude config files
- Store production credentials in secure vault
- Use read-only database credentials when possible

### File Structure

```
datahub/
├── data-quality-action-config.TEMPLATE.yaml  ← Template with placeholders (safe to commit)
├── data-quality-action-config.yaml           ← Actual credentials (NEVER commit!)
└── .gitignore                                 ← Must include config file
```

## Security Setup Steps

### 1. Configure .gitignore

Add to your `.gitignore`:

```gitignore
# Data Quality Action Config (contains credentials)
data-quality-action-config.yaml
*-config.yaml
!*-config.TEMPLATE.yaml

# Environment files
.env
.env.local
*.env
```

### 2. Create Config from Template

```bash
# Copy template
cp data-quality-action-config.TEMPLATE.yaml data-quality-action-config.yaml

# Edit with your credentials
nano data-quality-action-config.yaml

# Verify it's not tracked by git
git status | grep data-quality-action-config.yaml
# Should return nothing!
```

### 3. Set Proper File Permissions

```bash
# Make config readable only by owner
chmod 600 data-quality-action-config.yaml

# Verify
ls -l data-quality-action-config.yaml
# Should show: -rw------- (600)
```

### 4. Use Read-Only Credentials

Create a dedicated read-only user for quality tests:

**Snowflake Example:**
```sql
-- Create read-only role
CREATE ROLE DATAHUB_QUALITY_RO;

-- Grant minimal permissions
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE DATAHUB_QUALITY_RO;
GRANT USAGE ON DATABASE PROD_DB TO ROLE DATAHUB_QUALITY_RO;
GRANT USAGE ON ALL SCHEMAS IN DATABASE PROD_DB TO ROLE DATAHUB_QUALITY_RO;
GRANT SELECT ON ALL TABLES IN DATABASE PROD_DB TO ROLE DATAHUB_QUALITY_RO;
GRANT SELECT ON FUTURE TABLES IN DATABASE PROD_DB TO ROLE DATAHUB_QUALITY_RO;

-- Create user and assign role
CREATE USER datahub_quality_user PASSWORD='SecurePassword123';
GRANT ROLE DATAHUB_QUALITY_RO TO USER datahub_quality_user;
```

**PostgreSQL Example:**
```sql
-- Create read-only user
CREATE USER datahub_quality_ro WITH PASSWORD 'SecurePassword123';

-- Grant minimal permissions
GRANT CONNECT ON DATABASE prod_db TO datahub_quality_ro;
GRANT USAGE ON SCHEMA public TO datahub_quality_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO datahub_quality_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO datahub_quality_ro;
```

## Code-Level Security

### 1. Credentials Are Never Logged

The implementation ensures credentials never appear in logs:

```python
# connector_registry.py

# ✅ SAFE: Logs platform, not credentials
logger.debug(f"Using connector for platform: {platform}")

# ❌ NEVER DONE: Would expose credentials
# logger.debug(f"Connection string: {connection_string}")
```

### 2. SQLAlchemy Configuration

```python
engine = create_engine(
    connection_string,
    echo=False,  # Disable SQL echo (prevents credential logging)
    hide_parameters=True,  # Hide query parameters
)
```

### 3. Error Message Sanitization

```python
except Exception as e:
    # Sanitize error messages to remove connection strings
    error_msg = str(e).replace(connection_string, "***CONNECTION_STRING***")
    logger.error(f"Query failed: {error_msg}")
```

## Production Deployment

### Option 1: Docker Secrets (Recommended for Production)

```yaml
# docker-compose.yml
services:
  datahub-actions:
    secrets:
      - datahub_snowflake_conn
    volumes:
      - ./generate-config.sh:/usr/local/bin/generate-config.sh:ro
    entrypoint: ["/usr/local/bin/generate-config.sh"]

secrets:
  datahub_snowflake_conn:
    external: true
```

```bash
# generate-config.sh
#!/bin/bash
CONNECTION_STRING=$(cat /run/secrets/datahub_snowflake_conn)

cat > /etc/datahub/actions/conf/data-quality.yaml <<EOF
action:
  type: "data_quality"
  config:
    connectors:
      snowflake:
        connection_string: "${CONNECTION_STRING}"
    tests:
      # ... rest of config
EOF

# Start actions
exec datahub-actions start
```

### Option 2: External Secrets Manager

Use Kubernetes secrets, AWS Secrets Manager, Azure Key Vault, etc.:

```python
# Custom secrets loader
import boto3

def load_connection_string():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='datahub/snowflake/connection')
    return response['SecretString']
```

### Option 3: Encrypted Config Files

Use tools like `sops` or `age` to encrypt the config file:

```bash
# Encrypt config
sops --encrypt data-quality-action-config.yaml > data-quality-action-config.enc.yaml

# Decrypt at runtime
sops --decrypt data-quality-action-config.enc.yaml > /tmp/config.yaml
```

## Security Checklist

Before deploying to production:

- [ ] Config file added to `.gitignore`
- [ ] Template file (without credentials) committed
- [ ] Actual config file (with credentials) NOT in git
- [ ] File permissions set to 600 (owner read/write only)
- [ ] Using read-only database credentials
- [ ] Credentials use strong passwords (20+ characters)
- [ ] Database user has minimal required permissions
- [ ] Tested credential rotation procedure
- [ ] Logs reviewed for credential leaks
- [ ] Monitoring set up for failed authentication attempts

## Credential Rotation

### Process

1. **Create new credentials** in database
2. **Update config file** with new credentials
3. **Restart DataHub Actions** to pick up changes
   ```bash
   docker-compose restart datahub-actions
   ```
4. **Verify** tests still run successfully
5. **Revoke old credentials** after verification

### Automation

```bash
#!/bin/bash
# rotate-credentials.sh

# Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# Update database
psql -c "ALTER USER datahub_quality_ro WITH PASSWORD '$NEW_PASSWORD';"

# Update config
sed -i "s/:.*@/:$NEW_PASSWORD@/" data-quality-action-config.yaml

# Restart service
docker-compose restart datahub-actions

# Verify
docker logs datahub-actions | grep "Data Quality Action configured"
```

## Audit and Monitoring

### Log Monitoring

Monitor for potential security issues:

```bash
# Check for credential exposure (should find NOTHING)
docker logs datahub-actions 2>&1 | grep -iE 'password|secret|key='

# Monitor failed connections
docker logs datahub-actions 2>&1 | grep -i "failed to connect"

# Track test execution
docker logs datahub-actions 2>&1 | grep "Executing data quality tests"
```

### Database Audit

```sql
-- Snowflake: Check query history
SELECT
    query_text,
    user_name,
    execution_status,
    error_message
FROM snowflake.account_usage.query_history
WHERE user_name = 'DATAHUB_QUALITY_USER'
    AND start_time > DATEADD(day, -1, CURRENT_TIMESTAMP())
ORDER BY start_time DESC;

-- PostgreSQL: Enable logging
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
SELECT pg_reload_conf();
```

## Incident Response

If credentials are compromised:

1. **Immediately revoke** database credentials
   ```sql
   -- Snowflake
   ALTER USER datahub_quality_user SET DISABLED = TRUE;

   -- PostgreSQL
   REVOKE ALL PRIVILEGES ON DATABASE prod_db FROM datahub_quality_ro;
   DROP USER datahub_quality_ro;
   ```

2. **Generate new credentials**
3. **Update config file**
4. **Restart services**
5. **Review audit logs** for unauthorized access
6. **Rotate credentials** for all related services
7. **Update incident response documentation**

## Best Practices Summary

1. ✅ **Never commit credentials** to version control
2. ✅ **Use read-only credentials** whenever possible
3. ✅ **Set restrictive file permissions** (600)
4. ✅ **Rotate credentials regularly** (quarterly minimum)
5. ✅ **Monitor logs** for credential exposure
6. ✅ **Use secrets management** in production
7. ✅ **Test credential rotation** before production
8. ✅ **Document procedures** for your team
9. ✅ **Audit database access** regularly
10. ✅ **Have incident response plan** ready
