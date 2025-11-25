# DataHub Port Security Guide

**Last Updated:** 2025-11-21
**Purpose:** Security documentation for port exposure in DataHub deployments

---

## Table of Contents

1. [Port Overview](#port-overview)
2. [Production Configuration](#production-configuration)
3. [Development Configuration](#development-configuration)
4. [Security Best Practices](#security-best-practices)
5. [Risk Assessment Matrix](#risk-assessment-matrix)
6. [Network Architecture](#network-architecture)
7. [Compliance Checklist](#compliance-checklist)

---

## Port Overview

### Exposed Ports (Production - `datahub-with-data-quality.yml`)

| Port | Service | Binding | Purpose | Security Level |
|------|---------|---------|---------|----------------|
| **9002** | datahub-frontend-react | `0.0.0.0:9002` | Web UI & API Gateway | ⚠️ **PUBLIC** |
| **8888** | datahub-gms | `0.0.0.0:8888` | GraphQL & REST APIs | ⚠️ **PUBLIC** |

### Exposed Ports (Development - `datahub_deployment_local.yml`)

| Port | Service | Binding | Purpose | Security Level |
|------|---------|---------|---------|----------------|
| **9002** | datahub-frontend-react | `0.0.0.0:9002` | Web UI & API Gateway | ⚠️ **PUBLIC** |
| **8888** | datahub-gms | `0.0.0.0:8888` | GraphQL & REST APIs | ⚠️ **PUBLIC** |
| **8082** | datahub-actions | `127.0.0.1:8082` | AI Assistant API | ✅ **LOCALHOST ONLY** |
| **3000** | React Dev Server (Vite) | `0.0.0.0:3000` | Hot-reload dev server | ⚠️ **DEV ONLY** |

### Internal-Only Ports (Docker Network)

| Port | Service | Exposure | Purpose | Security Level |
|------|---------|----------|---------|----------------|
| **9200** | elasticsearch | `expose` only | Search & indexing | 🔒 **INTERNAL** |
| **3306** | mysql | `expose` only | Metadata storage | 🔒 **INTERNAL** |
| **9092** | kafka (broker) | `expose` only | Event streaming | 🔒 **INTERNAL** |
| **29092** | kafka (internal) | `expose` only | Container-to-container | 🔒 **INTERNAL** |
| **2181** | zookeeper | `expose` only | Kafka coordination | 🔒 **INTERNAL** |
| **8081** | schema-registry | `expose` only | Schema management | 🔒 **INTERNAL** |
| **7474** | neo4j (HTTP) | External/optional | Graph database UI | 🔒 **EXTERNAL** |
| **7687** | neo4j (Bolt) | External/optional | Graph database protocol | 🔒 **EXTERNAL** |

---

## Production Configuration

### ✅ Correctly Secured (`datahub-with-data-quality.yml`)

#### Public-Facing Ports (MUST be exposed)

```yaml
# Frontend - User interface entry point
datahub-frontend-react:
  ports:
    - "9002:9002"  # ✅ Required for web UI access
  environment:
    - AI_ASSISTANT_HOST=actions
    - AI_ASSISTANT_PORT=8082  # Internal routing via proxy
```

**Why exposed:**
- User-facing web UI
- Authentication gateway
- Proxies requests to GMS (8080 internal) and AI Assistant (8082 internal)
- Should be behind reverse proxy (nginx/Apache) with SSL/TLS

```yaml
# GMS - API entry point
datahub-gms:
  ports:
    - "8888:8080"  # ✅ Required for API access
```

**Why exposed:**
- REST and GraphQL API access
- Required by ingestion pipelines
- Required by external clients (CLI, SDKs)
- Should be behind reverse proxy with SSL/TLS

#### Internal-Only Services (MUST NOT be exposed)

```yaml
# Elasticsearch - NEVER expose publicly
elasticsearch:
  expose:
    - 9200  # ✅ Only accessible within Docker network
  # ports:  # ❌ COMMENTED OUT - DO NOT UNCOMMENT
  #   - "9200:9200"  # This would expose to 0.0.0.0
```

**Why not exposed:**
- Direct access bypasses authentication
- Allows unauthorized data access
- No audit logging
- CRITICAL SECURITY RISK if exposed

```yaml
# MySQL - NEVER expose publicly
mysql:
  expose:
    - 3306  # ✅ Only accessible within Docker network
  # ports:  # ❌ COMMENTED OUT - DO NOT UNCOMMENT
  #   - "3306:3306"  # This would expose to 0.0.0.0
```

**Why not exposed:**
- Contains all metadata (schemas, lineage, users)
- Weak default credentials (`datahub/datahub`)
- CRITICAL SECURITY RISK if exposed

```yaml
# Kafka - NEVER expose publicly
broker:
  expose:
    - 9092
    - 29092  # ✅ Only accessible within Docker network
  # ports:  # ❌ COMMENTED OUT - DO NOT UNCOMMENT
  #   - "9092:9092"  # This would expose to 0.0.0.0
```

**Why not exposed:**
- No authentication configured (PLAINTEXT protocol)
- Event stream contains all metadata changes
- Could be used to inject malicious metadata

```yaml
# AI Assistant API - Access via frontend proxy only
datahub-actions:
  # NO ports section  # ✅ Not exposed to host
```

**Why not exposed:**
- Should only be accessed through frontend proxy (`/api/ai-assistant/`)
- Contains LLM API keys in environment
- No authentication layer

#### Recommended Production Setup

```nginx
# nginx reverse proxy configuration (RECOMMENDED)
server {
    listen 443 ssl http2;
    server_name datahub.yourcompany.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Frontend (UI)
    location / {
        proxy_pass http://localhost:9002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # GMS (APIs)
    location /api/ {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Development Configuration

### ⚠️ Development-Only Exposures (`datahub_deployment_local.yml`)

#### AI Assistant API (Localhost binding)

```yaml
datahub-actions:
  ports:
    - "127.0.0.1:8082:8082"  # ⚠️ LOCALHOST ONLY - Safe for local dev
```

**Security Analysis:**
- ✅ Bound to `127.0.0.1` (localhost only)
- ✅ Not accessible from network
- ✅ Safe for local development
- ❌ NEVER use `0.0.0.0:8082:8082` or `:8082:8082` (implicit 0.0.0.0)
- ❌ Remove this binding in production

**Why needed for development:**
- React dev server (port 3000) proxies to `localhost:8082`
- Enables frontend development without building images
- Hot-reload development workflow

#### React Dev Server (Vite)

```bash
# Manual dev server (not in compose file)
cd datahub-web-react && npx vite
```

**Port:** 3000 (default Vite binding: `0.0.0.0:3000`)

**Security Analysis:**
- ⚠️ Exposes source code and development tools
- ⚠️ Hot-reload can expose internal state
- ⚠️ Should NEVER run in production
- ⚠️ Should NEVER be accessible from external networks
- ✅ OK for local development only

**Firewall Recommendation:**
```bash
# Block port 3000 from external access
sudo ufw deny from any to any port 3000

# Or allow only from localhost
sudo ufw allow from 127.0.0.1 to any port 3000
```

---

## Security Best Practices

### 1. Port Binding Rules

#### ✅ Safe Bindings

```yaml
# Localhost only - accessible from host only
ports:
  - "127.0.0.1:8082:8082"

# Explicit public - when intentional
ports:
  - "0.0.0.0:9002:9002"  # Document why this is needed
```

#### ❌ Dangerous Bindings

```yaml
# Implicit 0.0.0.0 - accessible from ALL interfaces
ports:
  - "8082:8082"  # Same as 0.0.0.0:8082:8082 - AVOID

# Public binding of internal services
ports:
  - "0.0.0.0:9200:9200"  # Elasticsearch - NEVER DO THIS
  - "0.0.0.0:3306:3306"  # MySQL - NEVER DO THIS
  - "0.0.0.0:9092:9092"  # Kafka - NEVER DO THIS
```

### 2. Network Segmentation

```yaml
networks:
  default:
    name: datahub_network  # All services in same network

  # BETTER: Separate networks by tier (recommended for production)
  frontend_network:
    name: datahub_frontend
  backend_network:
    name: datahub_backend
    internal: true  # Not accessible from host
```

### 3. Firewall Configuration

#### Using UFW (Ubuntu)

```bash
# Default deny incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow only public services
sudo ufw allow 443/tcp   # HTTPS (nginx proxy)
sudo ufw allow 9002/tcp  # DataHub UI (if not behind proxy)
sudo ufw allow 8888/tcp  # DataHub GMS API (if not behind proxy)

# Deny all internal services explicitly
sudo ufw deny 9200/tcp   # Elasticsearch
sudo ufw deny 3306/tcp   # MySQL
sudo ufw deny 9092/tcp   # Kafka
sudo ufw deny 2181/tcp   # Zookeeper
sudo ufw deny 8081/tcp   # Schema Registry
sudo ufw deny 8082/tcp   # AI Assistant API

# Enable firewall
sudo ufw enable
```

#### Using iptables

```bash
# Block Elasticsearch from external access
sudo iptables -A INPUT -p tcp --dport 9200 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 9200 -j DROP

# Block MySQL from external access
sudo iptables -A INPUT -p tcp --dport 3306 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 3306 -j DROP

# Block Kafka from external access
sudo iptables -A INPUT -p tcp --dport 9092 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 9092 -j DROP
```

### 4. Authentication & Authorization

#### Frontend (Port 9002)

```yaml
environment:
  # Enable authentication
  - AUTH_ENABLED=true
  - AUTH_JWT_ENABLED=true
  - METADATA_SERVICE_AUTH_ENABLED=true

  # Session configuration
  - AUTH_SESSION_TTL_HOURS=24

  # OIDC integration (recommended)
  - AUTH_OIDC_ENABLED=${AUTH_OIDC_ENABLED}
  - AUTH_OIDC_CLIENT_ID=${AUTH_OIDC_CLIENT_ID}
  - AUTH_OIDC_CLIENT_SECRET=${AUTH_OIDC_CLIENT_SECRET}
  - AUTH_OIDC_DISCOVERY_URI=${AUTH_OIDC_DISCOVERY_URI}
```

#### GMS (Port 8888)

```yaml
environment:
  # Enable API authentication
  - METADATA_SERVICE_AUTH_ENABLED=true
  - DATAHUB_SYSTEM_CLIENT_ID=__datahub_system
  - DATAHUB_SYSTEM_CLIENT_SECRET=JohnSnowKnowsNothing  # CHANGE THIS
```

**⚠️ CRITICAL:** Change default secrets in production:

```bash
# Generate secure secrets
export DATAHUB_SECRET=$(openssl rand -base64 32)
export DATAHUB_SYSTEM_CLIENT_SECRET=$(openssl rand -base64 32)

# Use in docker-compose
docker compose -f datahub-with-data-quality.yml up -d
```

### 5. SSL/TLS Configuration

#### Production Deployment (Required)

```yaml
# Use reverse proxy with SSL termination
# Never expose 9002 or 8888 directly to internet

# nginx with Let's Encrypt (recommended)
server {
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/datahub.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/datahub.example.com/privkey.pem;

    # Strong SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:9002;
    }
}
```

### 6. Secrets Management

#### ❌ Bad Practice (Hardcoded)

```yaml
environment:
  - GEMINI_API_KEY=AIzaSyA26MaS06JMDpOliZO334jirYd13QKNV0w  # EXPOSED
  - MYSQL_PASSWORD=datahub  # WEAK
  - DATAHUB_SECRET=YouKnowNothing  # DEFAULT
```

#### ✅ Best Practice (Environment variables)

```yaml
environment:
  - GEMINI_API_KEY=${GEMINI_API_KEY}  # From .env file (not in git)
  - MYSQL_PASSWORD=${MYSQL_PASSWORD}  # From .env file (not in git)
  - DATAHUB_SECRET=${DATAHUB_SECRET}  # From .env file (not in git)
```

Create `.env` file (add to `.gitignore`):

```bash
# .env - DO NOT COMMIT TO GIT
GEMINI_API_KEY=your_actual_key_here
MYSQL_PASSWORD=strong_random_password_here
MYSQL_ROOT_PASSWORD=different_strong_password_here
DATAHUB_SECRET=random_secret_32_chars_here
DATAHUB_SYSTEM_CLIENT_SECRET=random_secret_32_chars_here
NEO4J_PASSWORD=strong_neo4j_password_here
```

---

## Risk Assessment Matrix

### Critical Risk - NEVER Expose

| Port | Service | Risk Level | Impact if Exposed | Mitigation |
|------|---------|------------|-------------------|------------|
| **9200** | Elasticsearch | 🔴 **CRITICAL** | Full data access, no auth, data manipulation | Use `expose` only, never `ports` |
| **3306** | MySQL | 🔴 **CRITICAL** | Full database access, weak credentials | Use `expose` only, never `ports` |
| **9092** | Kafka | 🔴 **CRITICAL** | Event stream access, metadata injection | Use `expose` only, never `ports` |
| **2181** | Zookeeper | 🔴 **CRITICAL** | Kafka cluster control, DoS attacks | Use `expose` only, never `ports` |
| **8081** | Schema Registry | 🟠 **HIGH** | Schema manipulation, data corruption | Use `expose` only, never `ports` |

### High Risk - Expose with Caution

| Port | Service | Risk Level | Impact if Exposed | Mitigation |
|------|---------|------------|-------------------|------------|
| **9002** | Frontend | 🟠 **HIGH** | Authentication bypass if misconfigured | Enable auth, use HTTPS, rate limiting |
| **8888** | GMS | 🟠 **HIGH** | API abuse, metadata manipulation | Enable auth, use HTTPS, rate limiting |
| **8082** | AI Assistant | 🟠 **HIGH** | LLM API key exposure, prompt injection | Localhost only or proxy through frontend |

### Medium Risk - Development Only

| Port | Service | Risk Level | Impact if Exposed | Mitigation |
|------|---------|------------|-------------------|------------|
| **3000** | Vite Dev Server | 🟡 **MEDIUM** | Source code exposure, dev tools access | Firewall block, localhost only |
| **7474** | Neo4j UI | 🟡 **MEDIUM** | Graph data visualization without auth | External host only, strong password |
| **7687** | Neo4j Bolt | 🟡 **MEDIUM** | Graph database access | External host only, strong password |

---

## Network Architecture

### Production Architecture (Recommended)

```
Internet
   |
   v
[Firewall: Allow 443 only]
   |
   v
[Reverse Proxy: nginx/Apache]
   |  (SSL/TLS termination)
   |
   +---> 127.0.0.1:9002 (Frontend)
   |        |
   |        +---> docker network: datahub-gms:8080 (Internal GMS)
   |        +---> docker network: actions:8082 (Internal AI Assistant)
   |
   +---> 127.0.0.1:8888 (GMS API)
            |
            +---> docker network: elasticsearch:9200 (Internal)
            +---> docker network: mysql:3306 (Internal)
            +---> docker network: broker:29092 (Internal)
```

### Current Development Architecture

```
Developer Machine
   |
   +---> 0.0.0.0:3000 (Vite Dev Server) ⚠️ Dev only
   |        |
   |        +---> 127.0.0.1:8082 (AI Assistant) ✅ Localhost only
   |        +---> 127.0.0.1:9002 (Frontend proxy) ✅ For auth/GraphQL
   |
   +---> 0.0.0.0:9002 (Frontend)
   |
   +---> 0.0.0.0:8888 (GMS API)
   |
   +---> docker network: all internal services 🔒
```

### Docker Network Isolation

```yaml
# Current: Single flat network (acceptable for development)
networks:
  default:
    name: datahub_network

# Recommended: Multi-tier network (for production)
networks:
  dmz:
    name: datahub_dmz
    driver: bridge
  backend:
    name: datahub_backend
    driver: bridge
    internal: true  # No external routing

services:
  datahub-frontend-react:
    networks:
      - dmz
      - backend

  datahub-gms:
    networks:
      - dmz
      - backend

  elasticsearch:
    networks:
      - backend  # Backend only - no DMZ access

  mysql:
    networks:
      - backend  # Backend only - no DMZ access
```

---

## Compliance Checklist

### Pre-Production Security Audit

#### Port Configuration

- [ ] Elasticsearch (9200) is NOT exposed to host (`expose` only, no `ports`)
- [ ] MySQL (3306) is NOT exposed to host (`expose` only, no `ports`)
- [ ] Kafka (9092) is NOT exposed to host (`expose` only, no `ports`)
- [ ] Zookeeper (2181) is NOT exposed to host (`expose` only, no `ports`)
- [ ] Schema Registry (8081) is NOT exposed to host (`expose` only, no `ports`)
- [ ] AI Assistant API (8082) is NOT exposed or bound to localhost only
- [ ] Frontend (9002) is behind reverse proxy with SSL/TLS
- [ ] GMS (8888) is behind reverse proxy with SSL/TLS
- [ ] React dev server (3000) is NOT running in production

#### Authentication & Authorization

- [ ] `AUTH_ENABLED=true` is set
- [ ] `METADATA_SERVICE_AUTH_ENABLED=true` is set
- [ ] `DATAHUB_SECRET` has been changed from default
- [ ] `DATAHUB_SYSTEM_CLIENT_SECRET` has been changed from default
- [ ] `MYSQL_PASSWORD` has been changed from default (`datahub`)
- [ ] `MYSQL_ROOT_PASSWORD` has been changed from default (`datahub`)
- [ ] `NEO4J_PASSWORD` has been changed from default (if using Neo4j)
- [ ] OIDC/SSO is configured for production users
- [ ] Personal Access Tokens (PATs) are enabled and documented

#### Network Security

- [ ] Firewall rules block all internal ports (9200, 3306, 9092, 2181, 8081)
- [ ] Firewall rules allow only public ports (443, or 9002/8888 if not using proxy)
- [ ] Network segmentation is implemented (separate frontend/backend networks)
- [ ] Docker networks use `internal: true` for backend tier
- [ ] Host-based firewall (ufw/iptables) is enabled and configured

#### SSL/TLS

- [ ] HTTPS is enabled via reverse proxy (nginx/Apache)
- [ ] Valid SSL certificate is installed (Let's Encrypt or commercial)
- [ ] HTTP to HTTPS redirect is configured
- [ ] Strong TLS configuration (TLSv1.2+ only, strong ciphers)
- [ ] HSTS header is enabled

#### Secrets Management

- [ ] No hardcoded secrets in docker-compose files
- [ ] All secrets are in `.env` file (not committed to git)
- [ ] `.env` is listed in `.gitignore`
- [ ] API keys (GEMINI_API_KEY) are rotated periodically
- [ ] Database passwords are strong (16+ characters, random)

#### Monitoring & Logging

- [ ] Failed authentication attempts are logged
- [ ] API access is logged with IP addresses
- [ ] Unusual access patterns trigger alerts
- [ ] Logs are sent to centralized logging system (ELK, Splunk, etc.)
- [ ] Security events (privilege changes, etc.) are audited

#### Incident Response

- [ ] Process to rotate compromised secrets is documented
- [ ] Contact information for security team is documented
- [ ] Backup and disaster recovery plan is tested
- [ ] Process to revoke access tokens is documented

---

## Port Configuration Examples

### Example 1: Fully Secured Production

```yaml
# datahub-with-data-quality.yml (PRODUCTION)

services:
  datahub-frontend-react:
    ports:
      - "127.0.0.1:9002:9002"  # Localhost only, nginx proxies from 443
    environment:
      - AUTH_ENABLED=true
      - METADATA_SERVICE_AUTH_ENABLED=true
      - AUTH_OIDC_ENABLED=true

  datahub-gms:
    ports:
      - "127.0.0.1:8888:8080"  # Localhost only, nginx proxies from 443
    environment:
      - METADATA_SERVICE_AUTH_ENABLED=true

  datahub-actions:
    # NO ports exposed - access via frontend proxy only

  elasticsearch:
    expose:
      - 9200  # Internal only

  mysql:
    expose:
      - 3306  # Internal only

  broker:
    expose:
      - 9092
      - 29092  # Internal only

  zookeeper:
    expose:
      - 2181  # Internal only

  schema-registry:
    expose:
      - 8081  # Internal only
```

```nginx
# /etc/nginx/sites-available/datahub (NGINX CONFIG)

server {
    listen 443 ssl http2;
    server_name datahub.company.com;

    ssl_certificate /etc/letsencrypt/live/datahub.company.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/datahub.company.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Frontend UI
    location / {
        proxy_pass http://127.0.0.1:9002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # GMS API
    location /api/ {
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name datahub.company.com;
    return 301 https://$server_name$request_uri;
}
```

### Example 2: Development with Safe Localhost Binding

```yaml
# datahub_deployment_local.yml (DEVELOPMENT)

services:
  datahub-frontend-react:
    ports:
      - "9002:9002"  # OK for local dev network

  datahub-gms:
    ports:
      - "8888:8080"  # OK for local dev network

  datahub-actions:
    ports:
      - "127.0.0.1:8082:8082"  # ✅ Localhost only - SAFE

  # All other services use 'expose' only
```

### Example 3: What NOT to Do (Dangerous)

```yaml
# ❌ DANGEROUS - DO NOT USE

services:
  elasticsearch:
    ports:
      - "9200:9200"  # ❌ CRITICAL RISK - Exposes Elasticsearch to network
    environment:
      - xpack.security.enabled=false  # ❌ No authentication

  mysql:
    ports:
      - "3306:3306"  # ❌ CRITICAL RISK - Exposes MySQL to network
    environment:
      - MYSQL_PASSWORD=datahub  # ❌ Weak default password

  datahub-actions:
    ports:
      - "8082:8082"  # ❌ HIGH RISK - Exposes AI Assistant with API keys

  broker:
    ports:
      - "9092:9092"  # ❌ CRITICAL RISK - Exposes Kafka without auth
    environment:
      - KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT  # ❌ No encryption
```

---

## Quick Reference

### Safe Port Bindings

```yaml
# Localhost only (safe)
ports:
  - "127.0.0.1:PORT:PORT"

# Internal only (safest)
expose:
  - PORT

# All interfaces (use with caution, only for public services)
ports:
  - "0.0.0.0:PORT:PORT"
  - "PORT:PORT"  # Same as 0.0.0.0
```

### Verification Commands

```bash
# Check which ports are listening and from where
sudo netstat -tlnp | grep -E '(9002|8888|9200|3306|9092|8082)'

# Check firewall rules
sudo ufw status verbose

# Check Docker port mappings
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Scan for open ports (from external machine)
nmap -p 1-65535 your-datahub-host.com
```

---

## Support and Updates

**Document Owner:** DevSecOps Team
**Review Frequency:** Quarterly
**Next Review Date:** 2025-02-21

**Report Security Issues:**
- Internal: security@yourcompany.com
- DataHub OSS: https://github.com/datahub-project/datahub/security

**Additional Resources:**
- [DataHub Security Documentation](https://datahubproject.io/docs/authentication/concepts)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)

---

## Changelog

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-21 | 1.0 | Initial security documentation | Claude Code |

---

**⚠️ IMPORTANT REMINDER:**

1. **NEVER expose Elasticsearch (9200), MySQL (3306), or Kafka (9092) to the network**
2. **ALWAYS use HTTPS in production (via reverse proxy)**
3. **ALWAYS change default passwords and secrets**
4. **ALWAYS use `127.0.0.1` binding for development-only ports**
5. **ALWAYS review this document before deploying to production**
