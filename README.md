# DataHub Modifications

This repository contains two major enhancements to DataHub:

## 1. GraphRAG Integration

AI-powered semantic search and natural language Q&A for DataHub using GraphQL.

**Features:**
- 🔍 **Semantic Search** - Search datasets using natural language, not just keywords
- 💬 **AI Q&A** - Ask questions about your data catalog and get intelligent answers
- 🎯 **GraphQL API** - Clean, modern API interface
- 🤖 **OpenAI Integration** - Powered by GPT-4 and embeddings

**Implementation:** Complete working code in `graphrag-demo/` directory

## 2. Keycloak SSO Integration

Enterprise-grade Single Sign-On authentication for DataHub using Keycloak and OIDC.

**Features:**
- 🔐 **Centralized Authentication** - One login for all applications
- 👥 **User Management** - Manage users in Keycloak, not DataHub
- 🛡️ **Security** - Industry-standard OIDC protocol, 2FA capability
- ⚡ **JIT Provisioning** - Auto-create users on first login

**Implementation:** Complete setup guide in `COMPLETE_SSO_JOURNEY.md`

---

## GraphRAG Quick Start

### Prerequisites

- Node.js 18+
- DataHub running at `http://localhost:8080`
- OpenAI API key

### Setup (5 minutes)

```bash
# 1. Navigate to demo directory
cd graphrag-demo

# 2. Install dependencies
npm install

# 3. Configure environment
cp .env.example .env
# Edit .env and add your OpenAI API key

# 4. Index your DataHub entities
npm run index

# 5. Start the GraphQL server
npm start
```

Open `http://localhost:4000` in your browser to access the GraphQL Playground.

## Example Queries

### Semantic Search

Find datasets using natural language:

```graphql
query {
  semanticSearch(query: "customer revenue data", limit: 5) {
    results {
      name
      platform
      score
    }
  }
}
```

### Ask Questions

Get natural language answers about your data:

```graphql
query {
  askDataHub(question: "What datasets do we have and what do they contain?") {
    answer
    sources {
      name
    }
  }
}
```

## Architecture

```
┌─────────────────┐
│   DataHub       │  Your existing DataHub instance
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  GraphRAG Demo  │  New GraphQL server (Node.js)
│  Apollo Server  │  Port 4000
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────┐
│ OpenAI  │ │ Vector   │
│ API     │ │ Store    │
└─────────┘ └──────────┘
```

## What's Different from Standard DataHub

### New: GraphRAG Demo (`graphrag-demo/`)

A standalone GraphQL server that adds AI-powered features:

**Files:**
- `index.js` - GraphQL server with semantic search and Q&A resolvers
- `schema.graphql` - GraphQL schema defining new queries
- `vectorStore.js` - In-memory vector search using cosine similarity
- `datahubClient.js` - Client to fetch metadata from DataHub
- `openaiClient.js` - OpenAI integration for embeddings and GPT-4
- `indexer.js` - Script to generate embeddings for DataHub entities

**Key Features:**
- Semantic search over DataHub metadata
- RAG-powered question answering
- Vector embeddings for similarity search
- Natural language interface

### Configuration

**Model Configuration** (`openaiClient.js`):
```javascript
this.embeddingModel = 'text-embedding-3-small';  // For semantic search
this.chatModel = 'gpt-4-turbo-preview';          // For answers
```

Change these to use different models (e.g., `gpt-3.5-turbo` for lower cost).

**Similarity Threshold** (`index.js`):
```javascript
vectorStore.search(queryEmbedding, limit, 0.4);  // 0.4 = 40% similarity
```

Adjust for stricter/looser matching.

## How It Works

### 1. Indexing

```
DataHub Entities → Extract Metadata → Generate Embeddings → Store Vectors
                                        (OpenAI API)         (JSON file)
```

### 2. Semantic Search

```
User Query → Generate Embedding → Vector Similarity Search → Return Results
              (OpenAI API)         (Cosine Similarity)
```

### 3. RAG Question Answering

```
Question → Find Similar Entities → Fetch Full Metadata → Build Context → GPT-4 Answer
```

## Cost

For ~100 entities with moderate usage:

- **Initial indexing**: ~$0.002
- **Per query**: ~$0.01-0.03 (depending on model)
- **Monthly (100 queries)**: ~$1-3

Use `gpt-3.5-turbo` instead of `gpt-4` for 10-20x cost reduction.

## Limitations

This is a demonstration implementation:

- ❌ **No persistence** - Vectors stored in JSON (not production-ready)
- ❌ **No authentication** - Open GraphQL endpoint
- ❌ **Limited context** - Doesn't fetch lineage relationships
- ❌ **Single entity type** - Only indexes datasets
- ❌ **In-memory only** - Not distributed

For production, consider:
- Persistent vector database (Pinecone, Weaviate, Milvus, pgvector)
- Authentication and authorization
- Full context aggregation (lineage, ownership, quality)
- Multiple entity types (dashboards, charts, etc.)
- Caching and optimization

## GraphRAG Documentation

- `graphrag-demo/README.md` - Detailed setup and usage
- `graphrag-demo/QUICKSTART.md` - 5-minute quick start
- `graphrag-demo/DEMO_SCRIPT.md` - Presentation guide
- `GRAPHRAG_DEMO_SUMMARY.md` - Implementation overview

---

## Keycloak SSO Setup

For complete instructions on setting up Single Sign-On with Keycloak, see:

**📖 [COMPLETE_SSO_JOURNEY.md](COMPLETE_SSO_JOURNEY.md)**

This comprehensive guide covers:
- Step-by-step Keycloak installation and configuration
- DataHub OIDC integration setup
- Troubleshooting common issues
- Understanding SSO concepts (OAuth, OIDC, realms, clients)
- Docker networking and environment variables
- Security best practices

### Quick Overview

**What was implemented:**
1. Keycloak running on port 8180 with PostgreSQL backend
2. DataHub configured with OIDC authentication
3. JIT (Just-In-Time) user provisioning enabled
4. Traditional username/password login disabled

**Key Configuration:**
- **Realm:** DataHub
- **Client:** datahub-client (OpenID Connect, Confidential)
- **Redirect URI:** http://localhost:9002/*
- **Discovery URI:** http://host.docker.internal:8180/realms/DataHub/.well-known/openid-configuration

**Result:** Users login through Keycloak instead of typing datahub/datahub

### Screenshots

See `errors_solved/` directory for configuration screenshots:
- `keycloak redirect.png` - Valid redirect URIs configuration
- `datahub_realm.png` - DataHub realm setup

---

## Technology Stack

### GraphRAG
- **Apollo Server** - GraphQL server
- **OpenAI API** - Embeddings (text-embedding-3-small) + LLM (GPT-4)
- **Node.js** - Runtime environment
- **Cosine Similarity** - Vector search algorithm

### Keycloak SSO
- **Keycloak 23.0** - Identity and access management
- **PostgreSQL** - Keycloak database backend
- **OIDC** - OpenID Connect protocol
- **Docker** - Containerization

### Base Platform
- **DataHub** - Metadata platform

## Development

### Modify Models

Edit `graphrag-demo/openaiClient.js`:
```javascript
this.embeddingModel = 'text-embedding-3-small';
this.chatModel = 'gpt-3.5-turbo';  // Change to cheaper model
```

### Adjust Search Threshold

Edit `graphrag-demo/index.js`:
```javascript
vectorStore.search(queryEmbedding, limit, 0.5);  // Increase for stricter matching
```

### Re-index Entities

If DataHub data changes:
```bash
cd graphrag-demo
npm run index  # Regenerate embeddings
```

## Troubleshooting

**Server won't start:**
```bash
# Check if port 4000 is in use
netstat -ano | findstr :4000

# Kill process
taskkill //PID <pid> //F
```

**No results from semantic search:**
- Lower similarity threshold in `index.js`
- Verify vectors.json exists
- Re-run indexer

**OpenAI errors:**
- Check API key in `.env`
- Verify billing enabled
- Check usage limits

## Contributing

This is a demonstration implementation. For production use:

1. Integrate directly into DataHub codebase
2. Add persistent vector storage
3. Implement proper authentication
4. Add lineage and relationship traversal
5. Support multiple entity types

## License

Apache License 2.0 (same as DataHub)

## Acknowledgments

Built on top of:
- [DataHub](https://datahubproject.io) - Open-source metadata platform
- [Apollo Server](https://www.apollographql.com) - GraphQL server
- [OpenAI](https://openai.com) - Embeddings and LLM

Inspired by Microsoft's [GraphRAG](https://arxiv.org/abs/2404.16130) paper.

---

**Questions?** See documentation in `graphrag-demo/` directory or open an issue.

**Ready to try it?** → `cd graphrag-demo && npm install && npm start`
