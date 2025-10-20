# Custom DataHub - RAG Metadata Store for Data Estate

## Project Overview

This is a customized DataHub implementation designed to serve as a **metadata-powered knowledge base for RAG (Retrieval-Augmented Generation)** systems.

**Our Goal:** Build an intelligent metadata catalog that:
- Ingests metadata from diverse data sources across the data estate (Snowflake, MySQL, PostgreSQL, S3, etc.)
- Provides a unified view of datasets, schemas, lineage, and quality metrics
- Serves as a structured knowledge store for AI/LLM queries about data assets
- Enables intelligent data discovery through metadata enrichment

**Use Case:** Instead of traditional data catalogs, we're leveraging DataHub's metadata graph to power:
- Conversational data discovery ("What tables contain customer PII?")
- Automated data documentation generation
- Intelligent schema suggestions and recommendations
- Data quality monitoring with automated assertions

---

## Quick Start

### Prerequisites

- **Docker** (version 20.10+) and **Docker Compose** (v2.0+)
- **Git**
- **Minimum 8GB RAM** (16GB recommended)
- **10GB free disk space**

### Start DataHub in 3 Steps

**1. Clone the Repository**
```bash
git clone https://github.com/starschema/Custom-Datahub.git
cd datahub
```

**2. Start All Services (with Data Quality)**
```bash
docker-compose -f datahub-with-data-quality.yml up -d
```

> **Note:** This boots DataHub with automatic data quality testing enabled. Tests run automatically when you ingest data.

**3. Access the UI**

Open your browser and navigate to: **http://localhost:9002**

**Default credentials:**
- Username: `datahub`
- Password: `datahub`

> **Note:** First startup takes 5-10 minutes to download images and initialize services.

---

## Core Services & Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| **DataHub UI** | http://localhost:9002 | Main web interface for metadata browsing |
| **GMS API** | http://localhost:8888 | Backend GraphQL & REST APIs |
| **DataHub Actions** | (background) | Automatic data quality testing & automation |
| **MySQL** | localhost:3306 | Metadata persistence (`datahub`/`datahub`) |
| **Elasticsearch** | http://localhost:9200 | Search and indexing |
| **Kafka** | localhost:9092 | Event streaming |
| **Neo4j** (optional) | http://localhost:7474 | Graph database (`neo4j`/`P@ssword1`) |

**For complete service details and credentials, see [QUICKSTART.md](./QUICKSTART.md)**

---

## Architecture for RAG Use Case

```
┌─────────────────────────────────────────────────┐
│         Data Sources (Data Estate)              │
│  Snowflake • MySQL • PostgreSQL • S3 • APIs     │
└────────────────┬────────────────────────────────┘
                 │ Ingestion
                 ↓
┌─────────────────────────────────────────────────┐
│              DataHub Core                       │
│  ┌─────────────┐  ┌──────────────┐             │
│  │  Metadata   │  │    Search    │             │
│  │   Storage   │  │  (Elastic)   │             │
│  │  (MySQL)    │  └──────────────┘             │
│  └─────────────┘  ┌──────────────┐             │
│  ┌─────────────┐  │   Lineage    │             │
│  │   Events    │  │   (Neo4j)    │             │
│  │  (Kafka)    │  └──────────────┘             │
│  └─────────────┘                                │
└────────────────┬────────────────────────────────┘
                 │ GraphQL/REST APIs
                 ↓
┌─────────────────────────────────────────────────┐
│           RAG Application Layer                 │
│  • Metadata Retrieval • Context Enrichment      │
│  • LLM Queries • Semantic Search                │
└─────────────────────────────────────────────────┘
```

**Key Components:**
- **Frontend (React):** User interface for browsing metadata
- **GMS (Backend):** GraphQL/REST API server for programmatic access
- **Elasticsearch:** Powers semantic search across metadata
- **MySQL:** Persistent storage for all metadata entities
- **Kafka:** Real-time event streaming for metadata changes
- **Actions Framework:** Custom automation (data quality checks, webhooks)

---

## Getting Started with Metadata Ingestion

### Option 1: Using the UI (Recommended)

1. Navigate to **Ingestion** → **Create new source**
2. Select your data source (Snowflake, MySQL, etc.)
3. Configure connection details
4. Click **Execute** to start ingestion

### Option 2: Using the CLI

```bash
# Install DataHub CLI
pip install 'acryl-datahub'

# Create a recipe file (e.g., snowflake-recipe.yml)
# See examples in ./examples/recipes/

# Run ingestion
datahub ingest -c snowflake-recipe.yml
```

**Example Snowflake Recipe:**
```yaml
source:
  type: snowflake
  config:
    account_id: YOUR_ACCOUNT
    username: YOUR_USERNAME
    password: YOUR_PASSWORD
    warehouse: YOUR_WAREHOUSE
    role: YOUR_ROLE

sink:
  type: datahub-rest
  config:
    server: 'http://localhost:8080'
```

---

## Key Features

✅ **Metadata Discovery**
- Automatically extract schemas, column types, descriptions
- Map relationships and data lineage
- Track data quality metrics

✅ **Semantic Search**
- Full-text search across dataset names, descriptions, columns
- Tag-based filtering and domain organization
- Glossary terms for business context

✅ **API Access for RAG**
- GraphQL API for structured metadata queries
- REST API for bulk retrieval
- Real-time updates via Kafka events

✅ **Automatic Data Quality Testing** (NEW!)
- **20 built-in test types** (13 profile-based + 7 query-based)
- **Zero-duplication credentials** - Tests reuse ingestion source configs
- **Real-time monitoring** - Tests auto-run on every ingestion
- **Stateful optimization** - Only tests changed datasets
- See [DATA_QUALITY_FLOW.md](./DATA_QUALITY_FLOW.md) for details

✅ **Custom Automation**
- DataHub Actions framework for event-driven workflows
- Custom transformers for metadata enrichment
- Webhooks for external integrations

---

## Customizations in This Fork

- ✨ **Automatic Data Quality Testing** - 20 test types, zero-duplication credentials, event-driven execution
- 🔧 **Enhanced DataHub Actions** - Extended automation framework with custom plugins
- 📊 **RAG-Optimized Metadata** - Enhanced metadata schemas for LLM consumption
- 🔄 **Stateful Ingestion** - Smart incremental updates for efficient re-ingestion

---

## Stopping & Managing Services

**Stop services (keeps data):**
```bash
docker-compose -f datahub-with-data-quality.yml down
```

**Stop and remove all data:**
```bash
docker-compose -f datahub-with-data-quality.yml down -v
```

**View logs:**
```bash
# All services
docker-compose -f datahub-with-data-quality.yml logs -f

# Specific services
docker logs datahub-gms -f           # Backend API logs
docker logs datahub-datahub-actions-1 -f  # Data quality action logs
```

---

## Troubleshooting

**Services won't start?**
- Check Docker has at least 8GB RAM allocated
- Verify no port conflicts (9002, 8888, 3306, 9200, 9092)
- View logs: `docker logs datahub-gms`

**Can't access UI?**
- Wait 5-10 minutes for all services to initialize
- Check container health: `docker ps`
- Try: http://127.0.0.1:9002

**For detailed troubleshooting, see [QUICKSTART.md](./QUICKSTART.md#troubleshooting)**

---

## Additional Resources

- 📖 **Detailed Setup Guide:** [QUICKSTART.md](./QUICKSTART.md)
- 🔬 **Data Quality Flow:** [DATA_QUALITY_FLOW.md](./DATA_QUALITY_FLOW.md)
- 📋 **Query-Based Tests:** [QUERY_BASED_QUALITY_TESTS.md](./QUERY_BASED_QUALITY_TESTS.md)
- 📘 **Official DataHub Docs:** [docs.datahub.com](https://docs.datahub.com/)
- 🏗️ **Architecture Overview:** [docs/architecture/architecture.md](./docs/architecture/architecture.md)
- 🔌 **Ingestion Sources:** [Supported Connectors](https://docs.datahub.com/docs/metadata-ingestion/)
- 🤝 **Community:** [DataHub Slack](https://datahub.com/slack)

---

## Development

To build and modify DataHub components, see:
- [Development Guide](https://docs.datahub.com/docs/developers)
- [CLAUDE.md](./CLAUDE.md) - AI-assisted development guidelines

---

## License

[Apache License 2.0](./LICENSE)

---

**Built with ❤️ using DataHub** - An open-source data catalog for the modern data stack.
