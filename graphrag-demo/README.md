# DataHub GraphRAG Demo

**Quick demonstration of GraphRAG capabilities with DataHub using GraphQL**

This is a simplified standalone demo that shows semantic search and natural language Q&A over DataHub metadata.

## What This Demo Does

1. **Semantic Search** - Search for datasets using natural language:
   ```
   "customer revenue data" → finds relevant datasets even without exact keyword matches
   ```

2. **Natural Language Q&A** - Ask questions about your data catalog:
   ```
   "What datasets contain customer information and who owns them?"
   → Gets answer with citations from actual DataHub metadata
   ```

## Architecture

```
┌─────────────────┐
│   DataHub       │ (your existing instance)
│   GraphQL API   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  GraphRAG Demo  │ (this server)
│  GraphQL Server │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────┐
│ OpenAI  │ │ In-Memory│
│ API     │ │ Vector   │
│         │ │ Store    │
└─────────┘ └──────────┘
```

## Prerequisites

- Node.js 18+ installed
- DataHub instance running (at `http://localhost:8080`)
- OpenAI API key

## Quick Start

### 1. Install Dependencies

```bash
cd graphrag-demo
npm install
```

### 2. Configure Environment

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-key-here
DATAHUB_GQL_URL=http://localhost:8080/api/graphql
PORT=4000
```

### 3. Index Entities from DataHub

This fetches datasets from DataHub and generates embeddings:

```bash
npm run index
```

**What happens:**
- Fetches up to 100 datasets from your DataHub instance
- Generates embeddings for each using OpenAI
- Stores them in `vectors.json` (for demo simplicity)
- Takes ~2-5 minutes depending on number of entities

**Expected output:**
```
🔍 Fetching entities from DataHub...
📦 Found 47 entities

🧠 Generating embeddings...
Indexed: 47/47

✅ Indexing complete!
   Successfully indexed: 47
   Failed: 0
   Total vectors: 47

💾 Vectors saved to vectors.json

🚀 Now run 'npm start' to start the GraphRAG server!
```

### 4. Start the GraphQL Server

```bash
npm start
```

**Expected output:**
```
✅ Loaded 47 pre-indexed vectors

🚀 GraphRAG Demo Server ready at: http://localhost:4000/

📊 Vector Store: 47 entities indexed

Try these queries in GraphQL Playground:
  - semanticSearch(query: "customer data")
  - askDataHub(question: "What datasets do we have?")

💡 Remember to run 'npm run index' first to index entities!
```

### 5. Test the Queries

Open browser to `http://localhost:4000` to access GraphQL Playground.

Or run automated tests:

```bash
npm test
```

## Example Queries

### Query 1: Semantic Search

Find datasets using natural language:

```graphql
query {
  semanticSearch(query: "customer revenue data", limit: 5) {
    query
    total
    results {
      urn
      name
      type
      platform
      description
      score
    }
  }
}
```

**Example Response:**
```json
{
  "data": {
    "semanticSearch": {
      "query": "customer revenue data",
      "total": 5,
      "results": [
        {
          "urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,sales.customer_revenue,PROD)",
          "name": "customer_revenue",
          "type": "DATASET",
          "platform": "mysql",
          "description": "Daily customer revenue aggregated by customer ID",
          "score": 0.87
        }
      ]
    }
  }
}
```

### Query 2: Ask DataHub (Simple)

```graphql
query {
  askDataHub(question: "What datasets do we have?") {
    question
    answer
    sources {
      name
      urn
      relevance
    }
    confidence
  }
}
```

### Query 3: Ask DataHub (Ownership)

```graphql
query {
  askDataHub(question: "Which datasets contain customer information and who owns them?") {
    question
    answer
    sources {
      name
      relevance
    }
  }
}
```

**Example Response:**
```json
{
  "data": {
    "askDataHub": {
      "question": "Which datasets contain customer information and who owns them?",
      "answer": "Based on the data catalog, here are the datasets containing customer information:\n\n1. **customer_revenue** (MySQL)\n   - Owner: john.doe\n   - Contains daily customer revenue aggregated by customer ID\n\n2. **customers** (PostgreSQL)\n   - Owner: sarah.smith\n   - Core customer profile data including demographics\n\n3. **customer_events** (Snowflake)\n   - Owner: mike.chen\n   - Customer interaction and event tracking data",
      "sources": [
        {
          "name": "customer_revenue",
          "relevance": 0.89
        },
        {
          "name": "customers",
          "relevance": 0.85
        },
        {
          "name": "customer_events",
          "relevance": 0.82
        }
      ]
    }
  }
}
```

### Query 4: Ask DataHub (Lineage/Impact)

```graphql
query {
  askDataHub(question: "What would happen if the transactions table in MySQL was deleted?") {
    question
    answer
    sources {
      name
    }
  }
}
```

## How It Works

### 1. Indexing (Run Once)

```
DataHub → Fetch Entities → Generate Embeddings → Store Vectors
                              (OpenAI API)        (vectors.json)
```

### 2. Semantic Search

```
User Query → Generate Embedding → Vector Similarity Search → Return Results
              (OpenAI API)          (Cosine Similarity)
```

### 3. RAG Question Answering

```
User Question → Generate Embedding → Find Relevant Entities
                  ↓
               Fetch Full Metadata from DataHub
                  ↓
               Build Context (names, descriptions, owners, etc.)
                  ↓
               Generate Answer with GPT-4
                  ↓
               Return Answer + Citations
```

## Project Structure

```
graphrag-demo/
├── package.json           # Dependencies
├── .env                   # Configuration (create from .env.example)
├── schema.graphql         # GraphQL schema
├── index.js              # Main server with resolvers
├── vectorStore.js        # In-memory vector store
├── datahubClient.js      # DataHub GraphQL client
├── openaiClient.js       # OpenAI API client
├── indexer.js            # Entity indexing script
├── test-queries.js       # Automated test queries
└── vectors.json          # Indexed vectors (generated)
```

## Cost Estimate

For demo with ~50 entities:

**Initial Indexing:**
- 50 embeddings × $0.00002 = **$0.001**

**Testing (20 queries):**
- 20 query embeddings × $0.00002 = **$0.0004**
- 20 GPT-4 calls (avg 500 tokens) ≈ **$0.30**

**Total for demo: ~$0.30** ☕

## Troubleshooting

### Error: "No entities found"

- Make sure DataHub is running at `http://localhost:8080`
- Verify DataHub has datasets indexed
- Check if DataHub requires authentication (add `DATAHUB_TOKEN` to `.env`)

### Error: "OpenAI API key invalid"

- Verify your OpenAI API key in `.env`
- Make sure you have billing enabled on OpenAI account

### Error: "Rate limit exceeded"

- The indexer includes 200ms delays between requests
- If you hit rate limits, wait a minute and retry

### Slow indexing

- Normal for 50+ entities (each needs an API call)
- Consider indexing in smaller batches
- Embeddings are cached in `vectors.json`

## Limitations (This is a Demo!)

This is intentionally simplified for demonstration:

- ❌ **No persistence** - Vectors stored in JSON file (not production-ready)
- ❌ **No authentication** - No auth on GraphQL endpoint
- ❌ **No incremental updates** - Must re-index all entities
- ❌ **Limited entity types** - Only indexes datasets
- ❌ **No caching** - Every query calls OpenAI
- ❌ **In-memory only** - Vectors lost on restart (unless loaded from JSON)

## Next Steps

For production implementation, see:
- `GRAPHRAG_IMPLEMENTATION_GUIDE.md` - Full implementation with DataHub integration
- `GRAPHRAG_ARCHITECTURE.md` - Production architecture
- `GRAPHRAG_QUICKSTART.md` - Self-hosted options (pgvector, etc.)

## Demo Video

Record your demo showing:
1. Index entities: `npm run index`
2. Start server: `npm start`
3. Run semantic search in GraphQL Playground
4. Ask natural language questions
5. Show responses with citations

## Questions?

This is a minimal demo to show GraphRAG concepts. For production use, integrate directly with DataHub codebase.

---

**Built with:**
- Apollo Server (GraphQL)
- OpenAI API (embeddings + GPT-4)
- DataHub GraphQL API
- Node.js

**Time to build this demo:** 2-4 hours
**Time to run demo:** 5-10 minutes
