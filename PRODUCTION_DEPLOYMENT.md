# DataHub Production Deployment Guide

## Quick Start

### 1. Verify Production Configuration
```bash
# Windows
verify-production.bat

# Linux/Mac
./verify-production.sh
```

This script will check:
- ✓ .env file exists and is properly configured
- ✓ Secrets are not using default values
- ✓ .env is gitignored (security)
- ✓ Docker is running
- ✓ All required environment variables are set

### 2. Start Production Services
```bash
docker compose -f datahub-with-data-quality.yml up -d
```

### 3. Monitor Startup
```bash
# Watch all logs
docker compose -f datahub-with-data-quality.yml logs -f

# Watch specific service
docker compose -f datahub-with-data-quality.yml logs -f datahub-gms

# Check container status
docker compose -f datahub-with-data-quality.yml ps
```

### 4. Access Application
Once all services are healthy (takes 2-3 minutes):
- **Application URL**: http://localhost:9002
- **Default credentials**: datahub / datahub (change after first login!)

---

## Production Configuration Summary

### Network Architecture
```
External Access (Port 9002)
       ↓
    Nginx (Reverse Proxy)
       ↓
       ├─→ DataHub Frontend (Port 9002 internal)
       │        ↓
       │   DataHub GMS (Port 8080 internal)
       │
       └─→ AI Assistant API (Port 8082 internal)
```

### Security Features
- ✅ Only nginx port (9002) exposed externally
- ✅ GMS API not directly accessible (requires auth via frontend)
- ✅ All infrastructure services isolated from external access
- ✅ Strong randomly generated secrets
- ✅ All secrets stored in .env (not committed to git)
- ✅ Authentication enabled by default

### Services Restart Policy
All services have `restart: unless-stopped` policy:
- **nginx** - Reverse proxy (port 9002)
- **datahub-frontend-react** - Web UI with authentication
- **datahub-gms** - Core metadata service
- **datahub-actions** - Data quality + AI assistant
- **datahub-mce-consumer** - Metadata change consumer
- **datahub-mae-consumer** - Metadata audit consumer
- **elasticsearch** - Search and indexing
- **mysql** - Metadata storage
- **broker** - Kafka message broker
- **zookeeper** - Kafka coordination
- **schema-registry** - Kafka schema management

### Port Mapping
| Service | Internal Port | External Port | Status |
|---------|--------------|---------------|---------|
| nginx | 9002 | 9002 | ✅ Exposed |
| datahub-frontend-react | 9002 | - | ❌ Not exposed |
| datahub-gms | 8080 | - | ❌ Not exposed (security) |
| datahub-actions | 8082 | - | ❌ Not exposed (via nginx) |
| elasticsearch | 9200 | - | ❌ Not exposed (security) |
| mysql | 3306 | - | ❌ Not exposed (security) |
| broker (Kafka) | 9092 | - | ❌ Not exposed (security) |

---

## Common Operations

### Check Service Health
```bash
# All services status
docker compose -f datahub-with-data-quality.yml ps

# Check specific service logs
docker compose -f datahub-with-data-quality.yml logs datahub-gms

# Follow logs in real-time
docker compose -f datahub-with-data-quality.yml logs -f
```

### Restart Services
```bash
# Restart all services
docker compose -f datahub-with-data-quality.yml restart

# Restart specific service
docker compose -f datahub-with-data-quality.yml restart datahub-gms

# Recreate containers (apply config changes)
docker compose -f datahub-with-data-quality.yml up -d --force-recreate
```

### Stop Services
```bash
# Stop all services (preserves data)
docker compose -f datahub-with-data-quality.yml stop

# Stop and remove containers (preserves data volumes)
docker compose -f datahub-with-data-quality.yml down

# DANGER: Remove everything including data
docker compose -f datahub-with-data-quality.yml down -v
```

### Update Images
```bash
# Pull latest images
docker compose -f datahub-with-data-quality.yml pull

# Recreate containers with new images
docker compose -f datahub-with-data-quality.yml up -d --force-recreate
```

### View Resource Usage
```bash
# CPU, Memory, Network usage
docker stats

# Disk usage
docker system df
```

---

## Troubleshooting

### Service Won't Start
1. Check logs: `docker compose -f datahub-with-data-quality.yml logs [service-name]`
2. Check dependencies are healthy: `docker compose -f datahub-with-data-quality.yml ps`
3. Verify .env variables: `cat .env`

### Application Not Accessible
1. Verify nginx is running: `docker compose -f datahub-with-data-quality.yml ps nginx`
2. Check nginx logs: `docker compose -f datahub-with-data-quality.yml logs nginx`
3. Test port: `curl http://localhost:9002`
4. Check if port 9002 is already in use: `netstat -ano | findstr 9002` (Windows)

### Container Keeps Restarting
1. Check logs: `docker compose -f datahub-with-data-quality.yml logs [service-name]`
2. Common issues:
   - MySQL password mismatch after changing .env
   - Elasticsearch out of memory (increase Docker memory limit)
   - Neo4j connection failing (check NEO4J_URI in .env)

### Database Connection Errors
If you changed MySQL password in .env after initial setup:
```bash
# Remove MySQL data volume (WARNING: deletes all metadata!)
docker compose -f datahub-with-data-quality.yml down
docker volume rm datahub_mysqldata

# Restart with new password
docker compose -f datahub-with-data-quality.yml up -d
```

### AI Assistant Not Working
1. Verify GEMINI_API_KEY is set in .env
2. Check datahub-actions logs: `docker compose -f datahub-with-data-quality.yml logs datahub-actions`
3. Test AI endpoint: `curl http://localhost:9002/api/ai-assistant/health`

---

## Environment Variables Reference

### Required Variables (in .env)
```bash
# Image versions
DATAHUB_VERSION=v1.3.0.1
DATAHUB_FRONTEND_IMAGE=ghcr.io/starschema/custom-datahub-frontend-react:latest
DATAHUB_ACTIONS_IMAGE=ghcr.io/starschema/datahub-actions:latest

# Secrets (use strong random values!)
DATAHUB_SECRET=<random-base64-string>
DATAHUB_SYSTEM_CLIENT_SECRET=<random-base64-string>
MYSQL_ROOT_PASSWORD=<strong-password>
MYSQL_PASSWORD=<strong-password>
NEO4J_PASSWORD=<strong-password>

# AI Configuration
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your-api-key>
GEMINI_MODEL=gemini-2.0-flash-exp

# Feature Flags
METADATA_SERVICE_AUTH_ENABLED=true
DATAHUB_TELEMETRY_ENABLED=true
```

### Generate New Secrets
```bash
# Generate random base64 string (32 bytes)
openssl rand -base64 32
```

---

## Backup and Restore

### Backup Data Volumes
```bash
# Backup MySQL data
docker run --rm --volumes-from datahub-mysql-1 -v $(pwd):/backup ubuntu tar czf /backup/mysql-backup.tar.gz /var/lib/mysql

# Backup Elasticsearch data
docker run --rm --volumes-from datahub-elasticsearch-1 -v $(pwd):/backup ubuntu tar czf /backup/elasticsearch-backup.tar.gz /usr/share/elasticsearch/data
```

### Restore Data Volumes
```bash
# Restore MySQL data
docker run --rm --volumes-from datahub-mysql-1 -v $(pwd):/backup ubuntu tar xzf /backup/mysql-backup.tar.gz -C /

# Restore Elasticsearch data
docker run --rm --volumes-from datahub-elasticsearch-1 -v $(pwd):/backup ubuntu tar xzf /backup/elasticsearch-backup.tar.gz -C /
```

---

## Security Best Practices

1. **Change Default Credentials**
   - Change DataHub default password (datahub/datahub) after first login
   - Use strong random secrets in .env (already done if you used verify script)

2. **Never Commit Secrets**
   - .env is gitignored (verified by verify-production script)
   - Use .env.example as template, not production values

3. **Network Security**
   - Only port 9002 exposed externally (nginx reverse proxy)
   - All backend services isolated to Docker network
   - GMS API requires authentication via frontend

4. **Regular Updates**
   - Keep Docker images updated
   - Monitor security advisories
   - Update GEMINI_API_KEY rotation policy

5. **Monitor Logs**
   - Regularly check logs for suspicious activity
   - Set up alerts for service failures
   - Monitor resource usage

---

## Production Checklist

Before going live, verify:
- [ ] Ran `verify-production.bat` / `verify-production.sh` successfully
- [ ] Changed all default secrets to strong random values
- [ ] Added real GEMINI_API_KEY to .env
- [ ] .env file is gitignored and not committed
- [ ] Changed default DataHub UI password after first login
- [ ] All services are running and healthy
- [ ] Application accessible at http://localhost:9002
- [ ] Backup strategy in place for MySQL and Elasticsearch volumes
- [ ] Monitoring/alerting configured for production
- [ ] Documented custom configuration changes

---

## Support

For issues or questions:
- Check logs first: `docker compose -f datahub-with-data-quality.yml logs`
- Review troubleshooting section above
- Check DataHub documentation: https://datahubproject.io/docs/
- Verify environment with: `verify-production.bat` / `verify-production.sh`
