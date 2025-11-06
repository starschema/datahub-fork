# Security Fix: Removed Public Exposure of Infrastructure Services

## 🚨 Critical Security Vulnerability - FIXED

**Date:** 2025-11-06
**Severity:** CRITICAL
**Issue:** Multiple infrastructure services were publicly exposed without authentication

---

## What Was Fixed

### Before (VULNERABLE)
The following services were accessible from ANY external IP address:

| Service | Port | Exposure | Risk Level |
|---------|------|----------|------------|
| **Elasticsearch** | 9200 | 0.0.0.0:9200 → Internet | 🔴 CRITICAL |
| **MySQL** | 3306 | 0.0.0.0:3306 → Internet | 🔴 HIGH |
| **Kafka** | 9092 | 0.0.0.0:9092 → Internet | 🔴 HIGH |
| **Zookeeper** | 2181 | 0.0.0.0:2181 → Internet | 🟡 MEDIUM |
| **Schema Registry** | 8081 | 0.0.0.0:8081 → Internet | 🟡 MEDIUM |

**Attack Surface:**
```bash
# Anyone on the internet could do this:
curl http://YOUR_SERVER_IP:9200  # Read ALL your data
curl http://YOUR_SERVER_IP:9200/_cat/indices  # List all indices
curl -X DELETE http://YOUR_SERVER_IP:9200/your_index  # Delete data!

mysql -h YOUR_SERVER_IP -u datahub -p  # Access database
# Default password: datahub (exposed in docker-compose.yml)
```

### After (SECURE)
Services are now only accessible within the Docker network:

| Service | Port | Exposure | Access |
|---------|------|----------|--------|
| **Elasticsearch** | 9200 | Docker network only | ✅ Internal containers only |
| **MySQL** | 3306 | Docker network only | ✅ Internal containers only |
| **Kafka** | 9092 | Docker network only | ✅ Internal containers only |
| **Zookeeper** | 2181 | Docker network only | ✅ Internal containers only |
| **Schema Registry** | 8081 | Docker network only | ✅ Internal containers only |
| **DataHub GMS** | 8888 | Host (localhost:8888) | ✅ API access preserved |
| **DataHub Frontend** | 9002 | Host (0.0.0.0:9002) | ✅ UI access preserved |

---

## Changes Made

### File: `datahub-with-data-quality.yml`

**Changed from:**
```yaml
elasticsearch:
  ports:
    - ${DATAHUB_MAPPED_ELASTIC_PORT:-9200}:9200  # PUBLICLY EXPOSED!
```

**Changed to:**
```yaml
elasticsearch:
  # SECURITY: Only expose internally to Docker network
  expose:
    - 9200  # Accessible only to other containers
  # ports:  # COMMENTED OUT - DO NOT expose publicly!
  #   - ${DATAHUB_MAPPED_ELASTIC_PORT:-9200}:9200
```

**Applied to:**
- ✅ Elasticsearch (port 9200)
- ✅ MySQL (port 3306)
- ✅ Kafka/broker (ports 9092, 29092)
- ✅ Zookeeper (port 2181)
- ✅ Schema Registry (port 8081)

---

## Verification

### Test External Access is Blocked

```bash
# From outside the Docker network (should FAIL):
nc -vz YOUR_SERVER_IP 9200  # Connection refused ✅
nc -vz YOUR_SERVER_IP 3306  # Connection refused ✅
nc -vz YOUR_SERVER_IP 9092  # Connection refused ✅
nc -vz YOUR_SERVER_IP 2181  # Connection refused ✅
nc -vz YOUR_SERVER_IP 8081  # Connection refused ✅

curl http://YOUR_SERVER_IP:9200  # Connection refused ✅
```

### Test Internal Access Still Works

```bash
# From within Docker network (should SUCCEED):
docker exec datahub-datahub-gms-1 curl http://elasticsearch:9200
# Response: Elasticsearch info JSON ✅

docker exec datahub-datahub-gms-1 nc -vz mysql 3306
# Connection successful ✅

docker exec datahub-datahub-actions-1 nc -vz broker 9092
# Connection successful ✅
```

### Test User-Facing Services

```bash
# Frontend should still work:
curl http://YOUR_SERVER_IP:9002
# Response: DataHub UI ✅

# API should still work:
curl http://YOUR_SERVER_IP:8888/health
# Response: Health check JSON ✅
```

---

## Understanding Docker Port Exposure

### `ports:` (Maps to Host)
```yaml
ports:
  - "9200:9200"  # Binds to 0.0.0.0:9200 on host = PUBLIC
  - "127.0.0.1:9200:9200"  # Binds to localhost:9200 = LOCALHOST ONLY
```

**Effect:** Service accessible from host machine and/or internet

### `expose:` (Docker Network Only)
```yaml
expose:
  - 9200  # Only accessible to other containers in same network
```

**Effect:** Service accessible ONLY within Docker network

---

## Deployment Instructions

### Step 1: Apply Changes
```bash
cd /path/to/datahub

# Stop containers
docker compose -f datahub-with-data-quality.yml down

# Start with new configuration
docker compose -f datahub-with-data-quality.yml up -d
```

### Step 2: Verify Security
```bash
# Test external access is blocked (run from outside server):
nc -vz YOUR_SERVER_IP 9200  # Should: Connection refused
nc -vz YOUR_SERVER_IP 3306  # Should: Connection refused
nc -vz YOUR_SERVER_IP 9092  # Should: Connection refused

# Test internal services work:
docker exec datahub-datahub-gms-1 curl -s http://elasticsearch:9200 | grep cluster_name
# Should: Output cluster info

# Test UI still works:
curl -I http://YOUR_SERVER_IP:9002
# Should: HTTP 200 OK
```

### Step 3: Verify DataHub Functionality
1. Navigate to `http://YOUR_SERVER_IP:9002`
2. Login to DataHub UI
3. Search for datasets
4. Verify lineage, schema, and governance tabs work
5. Run ingestion to confirm Kafka/Elasticsearch connectivity

---

## Reverting (NOT RECOMMENDED)

If you need to temporarily expose a service for debugging:

```yaml
# Option 1: Bind to localhost only (safer)
ports:
  - "127.0.0.1:9200:9200"  # Accessible only from host machine

# Option 2: Public access (DANGEROUS - for debugging only!)
ports:
  - "9200:9200"  # Accessible from internet - USE WITH CAUTION
```

**⚠️ Warning:** Only use public exposure temporarily and with proper firewall rules!

---

## Additional Security Recommendations

### 1. Enable Firewall Rules
```bash
# Example: ufw (Ubuntu)
sudo ufw default deny incoming
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 9002/tcp # DataHub UI
sudo ufw allow 8888/tcp # DataHub API (if needed externally)
sudo ufw enable

# Block infrastructure ports explicitly:
sudo ufw deny 9200/tcp  # Elasticsearch
sudo ufw deny 3306/tcp  # MySQL
sudo ufw deny 9092/tcp  # Kafka
```

### 2. Enable Elasticsearch Security (X-Pack)
```yaml
elasticsearch:
  environment:
    - xpack.security.enabled=true  # Enable authentication
    - ELASTIC_PASSWORD=your_secure_password
```

### 3. Change Default MySQL Passwords
```yaml
mysql:
  environment:
    - MYSQL_PASSWORD=${MYSQL_PASSWORD:-secure_password_here}  # Not 'datahub'!
    - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-another_secure_password}
```

### 4. Use Docker Secrets for Production
Store passwords in Docker secrets instead of environment variables.

### 5. Network Segmentation
Consider using separate Docker networks for different tiers:
```yaml
networks:
  frontend:  # Public-facing services
  backend:   # Application services
  database:  # Data stores
```

---

## Impact Assessment

### ✅ No User Impact
- DataHub UI remains accessible on port 9002
- DataHub API remains accessible on port 8888
- All ingestion functionality continues to work
- All features remain functional

### ✅ Security Improvements
- Elasticsearch data protected from unauthorized access
- MySQL database protected from direct connections
- Kafka message broker no longer publicly accessible
- Reduced attack surface by ~5 exposed ports

### ⚠️ Potential Impact on Debugging
- Cannot directly connect to Elasticsearch from host machine
- Cannot use external MySQL clients to connect
- Cannot use external Kafka tools directly

**Solution:** Use `docker exec` to run commands inside containers:
```bash
# Instead of: mysql -h YOUR_SERVER_IP -u datahub -p
# Use: docker exec -it datahub-mysql-1 mysql -u datahub -p

# Instead of: curl http://YOUR_SERVER_IP:9200
# Use: docker exec datahub-datahub-gms-1 curl http://elasticsearch:9200
```

---

## Related Issues

- **GitHub Issue:** #XXX - "Elasticsearch responding to outside requests"
- **Reporter:** hawle
- **Original Report:** External access to Elasticsearch confirmed via `nc` and `curl`

---

## Summary

| Before | After |
|--------|-------|
| 🔴 5 services publicly exposed | ✅ 0 infrastructure services exposed |
| 🔴 No authentication required | ✅ Network isolation enforced |
| 🔴 Data accessible to anyone | ✅ Internal-only access |
| ✅ User features working | ✅ User features still working |

**Status:** SECURITY VULNERABILITY RESOLVED ✅
