# DataHub Quick Start Guide

This guide provides step-by-step instructions to get DataHub up and running on your local machine.

## Prerequisites

- **Docker** (version 20.10+)
- **Docker Compose** (version 2.0+)
- **Git**
- **Minimum 8GB RAM** (16GB recommended)
- **10GB free disk space**

---

## Step 1: Clone the Repository and Pull Images

```bash
# Clone the DataHub repository
git clone https://github.com/starschema/Custom-Datahub.git

# Navigate to the project directory
cd Custom-Datahub

# Pull pre-built custom images (saves over 1 hour of build time!)
./docker/pull-images.sh
```

**Note:** If you encounter authentication issues, see [GHCR-IMAGES-README.md](./GHCR-IMAGES-README.md) for authentication instructions.

---

## Step 2: Start DataHub Using Docker Compose

```bash
# Navigate to the quickstart directory
cd docker/quickstart

# Start all DataHub services
docker-compose -f docker-compose.quickstart.yml up -d
```

**What this does:**
- Downloads all required Docker images
- Starts DataHub core services
- Initializes databases and message queues
- Sets up Elasticsearch for search functionality

**Note:** First-time startup may take 5-10 minutes as it downloads images and initializes services.

---

## Step 3: Verify Services are Running

Check that all containers are healthy:

```bash
docker ps
```

You should see these containers running:
- `datahub-frontend-react` (UI)
- `datahub-gms` (Backend API)
- `datahub-actions`
- `elasticsearch`
- `mysql`
- `broker` (Kafka)
- `schema-registry`
- `zookeeper`

---

## Step 4: Access DataHub UI

Open your web browser and navigate to:

**http://localhost:9002**

### Default Login Credentials

- **Username:** `datahub`
- **Password:** `datahub`

---

## Service Ports & Credentials

### Core Services

| Service | URL | Description |
|---------|-----|-------------|
| **DataHub UI** | http://localhost:9002 | Main web interface |
| **GMS API** | http://localhost:8888 | Backend GraphQL & REST APIs |
| **Elasticsearch** | http://localhost:9200 | Search engine |
| **MySQL** | localhost:3306 | Metadata database |
| **Kafka** | localhost:9092 | Message broker |
| **Schema Registry** | http://localhost:8081 | Schema management |
| **Zookeeper** | localhost:2181 | Coordination service |

### Database Credentials

#### MySQL Database
```
Host:      localhost
Port:      3306
Database:  datahub
Username:  datahub
Password:  datahub
Root Password: datahub
```

#### Neo4j (Optional - if enabled)
```
HTTP:      http://localhost:7474
Bolt:      bolt://localhost:7687
Username:  neo4j
Password:  P@ssword1
```

#### Elasticsearch
```
Host:      http://localhost:9200
Auth:      None (disabled by default)
```

### Application Secrets

These are internal secrets used by DataHub services:

- **DataHub Secret:** `YouKnowNothing`
- **System Client ID:** `__datahub_system`
- **System Client Secret:** `JohnSnowKnowsNothing`

---

## What to Do Next

### 1. Explore the UI

After logging in, you'll see:
- **Search Bar** - Search for datasets, dashboards, and other data assets
- **Home Page** - Browse recent activity and popular entities
- **Navigation Menu** - Access Datasets, Dashboards, Charts, Pipelines, etc.

### 2. Ingest Your First Dataset

There are two ways to ingest metadata:

#### Option A: Using the UI (Recommended)
1. Click **"Ingestion"** in the top navigation
2. Click **"Create new source"**
3. Select your data source (e.g., Snowflake, MySQL, Postgres)
4. Configure connection details
5. Click **"Execute"** to run the ingestion

#### Option B: Using the CLI
```bash
# Install DataHub CLI
pip install 'acryl-datahub'

# Run ingestion with a recipe file
datahub ingest -c your-recipe.yml
```

Example recipe for Snowflake:
```yaml
source:
  type: snowflake
  config:
    account_id: your-account
    username: your-username
    password: your-password
    warehouse: your-warehouse
    role: your-role

sink:
  type: datahub-rest
  config:
    server: 'http://localhost:8080'
```

### 3. Explore Features

- **Lineage:** View upstream and downstream dependencies
- **Documentation:** Add descriptions and tags
- **Domains:** Organize assets by business domain
- **Glossary:** Create business terms
- **Data Quality:** View data quality rules and test results

---

## Stopping DataHub

### Stop All Services (keeps data)
```bash
docker-compose -f docker-compose.quickstart.yml down
```

### Stop All Services and Remove Data
```bash
docker-compose -f docker-compose.quickstart.yml down -v
```

### Restart Services
```bash
docker-compose -f docker-compose.quickstart.yml restart
```

---

## Troubleshooting

### Services Won't Start

1. **Check Docker resources:**
   ```bash
   docker stats
   ```
   Ensure sufficient CPU and memory allocated

2. **View service logs:**
   ```bash
   docker logs <container-name>
   # Example:
   docker logs datahub-gms
   ```

3. **Check for port conflicts:**
   ```bash
   # On Linux/Mac:
   lsof -i :9002

   # On Windows:
   netstat -ano | findstr :9002
   ```

### Cannot Access UI (Port 9002)

- Ensure no other application is using port 9002
- Check if frontend container is healthy:
  ```bash
  docker ps | grep datahub-frontend-react
  ```
- Try accessing from: http://127.0.0.1:9002

### Slow Performance

- Increase Docker memory allocation:
  - Docker Desktop → Settings → Resources → Memory (set to at least 8GB)
- Close unnecessary applications
- Check disk space availability

### Common Issues

| Issue | Solution |
|-------|----------|
| Port already in use | Change ports in docker-compose file or stop conflicting service |
| Insufficient memory | Increase Docker memory allocation |
| Containers keep restarting | Check logs with `docker logs <container>` |
| UI shows "Cannot connect" | Wait for GMS to be healthy, check with `docker ps` |

---

## Useful Commands

### View All Container Logs
```bash
docker-compose -f docker-compose.quickstart.yml logs -f
```

### View Specific Container Logs
```bash
docker logs -f datahub-gms
docker logs -f datahub-frontend-react
docker logs -f elasticsearch
```

### Check Container Health
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Clean Up Everything
```bash
# Stop and remove containers, networks, volumes
docker-compose -f docker-compose.quickstart.yml down -v

# Remove unused images (optional)
docker system prune -a
```

---

## Additional Resources

- **Documentation:** https://datahubproject.io/docs/
- **GitHub Repository:** https://github.com/datahub-project/datahub
- **Slack Community:** https://datahubspace.slack.com/
- **Demo Instance:** https://demo.datahub.io/
- **Ingestion Sources:** https://datahubproject.io/docs/metadata-ingestion/

---

## Architecture Overview

DataHub consists of:
- **Frontend (React):** User interface at port 9002
- **GMS (Backend):** GraphQL/REST API server at port 8888
- **Elasticsearch:** Search and indexing at port 9200
- **MySQL:** Persistent metadata storage at port 3306
- **Kafka:** Real-time event streaming at port 9092
- **Actions Framework:** Automation and webhooks

---

**Need Help?** Join our [Slack community](https://datahubspace.slack.com/) or open an issue on [GitHub](https://github.com/datahub-project/datahub/issues).
