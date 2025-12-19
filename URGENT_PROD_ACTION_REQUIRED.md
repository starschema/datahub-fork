# 🚨 URGENT: Production Server Action Required

**TO:** Production Server Administrators
**FROM:** DataHub Development Team
**PRIORITY:** HIGH - Time Sensitive
**DATE:** 2024-12-18

---

## Situation Summary

A critical configuration issue has been discovered in the DataHub deployment that affects secret persistence. **All secrets (database credentials, API keys, Snowflake credentials) are currently at risk of being lost on the next production restart.**

## What's Happening

- **Root Cause:** DataHub docker-compose is missing `SECRET_SERVICE_ENCRYPTION_KEY` configuration
- **Current Impact:** Secrets work NOW but will be lost on ANY restart (server reboot, deployment, crash recovery)
- **Triggered By:** ANY event that restarts containers (image updates, server maintenance, power outage, etc.)
- **NOT caused by:** Recent image changes - this is a pre-existing configuration bug

## Immediate Action Required (BEFORE Next Prod Restart)

### Option 1: Extract Current Encryption Key (Preferred)

**If production is currently running with working secrets:**

```bash
# 1. SSH to production server
ssh <production-server>

# 2. Find the running GMS container
docker ps | grep datahub-gms

# 3. Check if encryption key is set
docker exec <gms-container-name> printenv SECRET_SERVICE_ENCRYPTION_KEY

# 4. If the above returns empty, the key is auto-generated in memory
# Check GMS startup logs for any encryption key information:
docker logs <gms-container-name> 2>&1 | grep -i "secret\|encryption" | head -50

# 5. Contact development team with findings immediately
```

**If we can extract the current key:**
- We can set it as a persistent value
- Apply the fix without losing any secrets ✅
- Zero downtime migration

### Option 2: Document All Credentials (Fallback)

**If we cannot extract the current key:**

```bash
# 1. Document all ingestion sources
# Log into DataHub UI: http://<prod-server>:9002
# Navigate to: Ingestion → Sources
# Screenshot or document ALL sources and their configurations

# 2. Export configuration (if possible)
docker exec <gms-container> curl -s http://localhost:8080/config > prod-config-backup.json

# 3. Backup MySQL volume
docker run --rm -v <mysql-volume-name>:/data -v $(pwd):/backup \
  alpine tar czf /backup/prod-mysql-backup-$(date +%Y%m%d).tar.gz /data

# 4. Gather all credentials from secure vaults:
# - Snowflake credentials
# - Database passwords
# - API keys
# - Any other ingestion source credentials
```

## The Fix (Development Team Has This Ready)

**Files Ready to Deploy:**
- ✅ Updated `datahub-with-data-quality.yml` with SECRET_SERVICE_ENCRYPTION_KEY
- ✅ `.env` template file for secure key storage
- ✅ Migration documentation
- ✅ Rollback procedures

**Deployment Steps:**
1. Create `.env` file with persistent encryption key
2. Update docker-compose configuration
3. Restart containers with new configuration
4. Re-enter credentials (if Option 1 failed)
5. Verify secrets persist across restart
6. Done - production is now stable

## Timeline

⏰ **Action Required:** ASAP - Before any production restart
⏰ **Estimated Deployment Time:** 30-60 minutes (includes testing)
⏰ **One-time Cost:** Possible credential re-entry (if Option 1 fails)
⏰ **Long-term Benefit:** Stable secret management, zero future issues

## Risk Assessment

**If we do nothing:**
- ❌ Next server reboot = all secrets lost
- ❌ Next deployment = all secrets lost
- ❌ Next Docker restart = all secrets lost
- ❌ Production outage until credentials manually re-entered
- ❌ Data pipeline downtime

**If we apply the fix:**
- ✅ One-time controlled migration
- ✅ Secrets persist reliably forever
- ✅ Production-grade deployment
- ✅ No future secret loss

## Who to Contact

**For Questions:**
- Development Team: [Your contact info]
- This Issue: See `INCIDENT_REPORT.md` and `MIGRATION_SECRET_ENCRYPTION.md`

**For Production Access:**
- [Name of person with prod access]
- [DevOps team contact]

## References

- **Incident Report:** `INCIDENT_REPORT.md`
- **Migration Guide:** `MIGRATION_SECRET_ENCRYPTION.md`
- **Quick Summary:** `SECRET_ENCRYPTION_FIX_SUMMARY.md`
- **Fix Implementation:** Pull request #[number] or commit [hash]

---

## Next Steps

1. **[ ] Production admin acknowledges this message**
2. **[ ] Attempt Option 1 (extract current key)**
3. **[ ] If Option 1 fails, execute Option 2 (document credentials)**
4. **[ ] Schedule maintenance window for deployment**
5. **[ ] Apply fix to production**
6. **[ ] Verify secrets persist across restart**
7. **[ ] Close incident**

---

**This is not an emergency requiring immediate downtime, but it requires action before the next unplanned restart.**

Time is of the essence - the longer production runs without this fix, the higher the risk of losing secrets during an unexpected restart.
