# DataHub GraphRAG Demo

This directory contains tools and demos for querying DataHub's metadata using GraphQL and performing semantic search using Graph-based Retrieval Augmented Generation (GraphRAG).

## Overview

**GraphRAG** combines graph-based data structures (like DataHub's metadata graph) with semantic search capabilities to enable intelligent querying of your data catalog. Instead of just keyword-based search, you can:

- Find datasets by semantic similarity
- Ask natural language questions about your data
- Navigate relationships between datasets, columns, and data quality rules
- Build context-aware data discovery applications

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                          │
│              (GraphQL Client / GraphRAG Tool)                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │   CORS Proxy (port 3001) │  ◄── Handles browser CORS
         └────────────┬─────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │  DataHub GMS (port 8080)│  ◄── GraphQL API
         └────────────┬─────────────┘
                      │
         ┌────────────┴──────────────┐
         ▼                           ▼
    ┌─────────┐              ┌──────────────┐
    │  MySQL  │              │ Elasticsearch│
    │Metadata │              │   Search     │
    └─────────┘              └──────────────┘
```

## Components

### 1. GraphQL CORS Proxy (`../graphql-proxy.js`)
A lightweight Node.js proxy that:
- Adds CORS headers to DataHub GraphQL API responses
- Allows browser-based clients to query DataHub
- Runs on **port 3001**

**Start it:**
```bash
cd ..
node graphql-proxy.js
```

### 2. GraphQL HTML Client (`../graphql-client.html`)
An interactive web interface for testing GraphQL queries against DataHub.

**Access it:**
1. Start the HTTP server: `python -m http.server 8765`
2. Open: `http://localhost:8765/graphql-client.html`

**Features:**
- Pre-built query examples for common operations
- Real-time query execution
- Syntax-highlighted responses
- Query dataset columns, assertions, ownership, tags, and more

### 3. Node.js Query Script (`../test-datahub-query.js`)
A command-line script for programmatic GraphQL access (no CORS issues).

**Run it:**
```bash
node ../test-datahub-query.js
```

### 4. Vector Embeddings (`vectors.json`)
Pre-computed semantic embeddings for datasets in your DataHub instance. These enable semantic similarity search for GraphRAG applications.

**Format:**
```json
{
  "vectors": [
    ["urn:li:dataset:(...)", { "embedding": [...] }]
  ]
}
```

## GraphQL Query Examples

### Get Dataset Columns (Schema)

```graphql
query {
  dataset(urn: "urn:li:dataset:(urn:li:dataPlatform:snowflake,test_db.tpch_1000.customer,PROD)") {
    name
    platform { name }
    schemaMetadata {
      fields {
        fieldPath
        type
        nativeDataType
        description
        nullable
        tags {
          tags {
            tag { name }
          }
        }
      }
    }
  }
}
```

### Get Data Quality Assertions

```graphql
query {
  dataset(urn: "urn:li:dataset:(urn:li:dataPlatform:snowflake,test_db.tpch_1000.customer,PROD)") {
    name
    assertions(start: 0, count: 100) {
      total
      assertions {
        urn
        info {
          type
          description
          datasetAssertion {
            scope
            fields { path }
          }
        }
        runEvents(status: COMPLETE, limit: 1) {
          succeeded
          failed
          runEvents {
            timestampMillis
            result {
              type
              actualAggValue
              rowCount
            }
          }
        }
      }
    }
  }
}
```

### Search for Datasets

```graphql
query {
  search(input: {
    type: DATASET
    query: "customer"
    start: 0
    count: 10
  }) {
    total
    searchResults {
      entity {
        ... on Dataset {
          urn
          name
          platform { name }
          description
        }
      }
    }
  }
}
```

### Get Dataset Lineage

```graphql
query {
  dataset(urn: "urn:li:dataset:(...)") {
    name
    upstream: relationships(
      input: { types: ["DownstreamOf"], direction: OUTGOING }
    ) {
      relationships {
        entity {
          ... on Dataset {
            urn
            name
          }
        }
      }
    }
    downstream: relationships(
      input: { types: ["DownstreamOf"], direction: INCOMING }
    ) {
      relationships {
        entity {
          ... on Dataset {
            urn
            name
          }
        }
      }
    }
  }
}
```

## Using GraphRAG

### Concept

GraphRAG extends traditional RAG by:
1. **Graph Structure**: Leveraging DataHub's entity relationships (dataset → columns, lineage, ownership)
2. **Semantic Search**: Using vector embeddings to find relevant datasets
3. **Context Enrichment**: Pulling detailed metadata via GraphQL for the LLM

### Workflow

```
User Question
     │
     ▼
1. Embed question using same model as datasets
     │
     ▼
2. Find similar datasets via cosine similarity (vectors.json)
     │
     ▼
3. For top matches, query detailed metadata via GraphQL
     │
     ▼
4. Build context from:
   - Dataset name, description, platform
   - Column names, types, descriptions
   - Lineage (upstream/downstream datasets)
   - Data quality assertions and results
   - Tags, glossary terms, ownership
     │
     ▼
5. Pass context + question to LLM
     │
     ▼
6. Return answer with sources
```

### Example Use Cases

1. **"Which tables contain customer phone numbers?"**
   - Embed question → find datasets with "customer" semantic similarity
   - Query schema fields via GraphQL
   - Check for fields matching "phone" pattern
   - Return datasets with metadata context

2. **"Show me datasets failing quality checks"**
   - Query all datasets via GraphQL search
   - For each, query assertions and their latest runEvents
   - Filter where `runEvents.failed > 0`
   - Return with details of which assertions failed

3. **"What are the downstream impacts of the orders table?"**
   - Query lineage relationships via GraphQL
   - Recursively fetch downstream datasets
   - Build dependency graph
   - Return visualization + metadata

### Implementation Snippet

```javascript
// 1. Find semantically similar datasets
const questionEmbedding = await embedText(userQuestion);
const similarDatasets = findTopKSimilar(questionEmbedding, vectors, k=5);

// 2. Fetch detailed metadata via GraphQL
const contexts = await Promise.all(
  similarDatasets.map(urn =>
    fetchDatasetMetadata(urn)  // Uses GraphQL
  )
);

// 3. Build LLM prompt
const prompt = `
Context: ${JSON.stringify(contexts)}

User Question: ${userQuestion}

Based on the above metadata, answer the question.
`;

// 4. Query LLM
const answer = await queryLLM(prompt);
```

## Getting Started

### Prerequisites
- DataHub running (port 8080)
- Node.js installed

### Quick Start

1. **Start the CORS proxy:**
   ```bash
   cd ..
   node graphql-proxy.js
   ```
   Leave this running in the background.

2. **Start the HTTP server (for HTML client):**
   ```bash
   cd ..
   python -m http.server 8765
   ```

3. **Access the GraphQL client:**
   Open `http://localhost:8765/graphql-client.html` in your browser.

4. **Try example queries:**
   - Click "Get Table Columns" to see dataset schema
   - Click "Get Assertions" to see data quality checks
   - Modify the URN to query your own datasets

### Direct API Usage (No Browser)

Use the Node.js script for server-side or CLI usage:

```bash
node ../test-datahub-query.js
```

Or use curl:

```bash
curl -X POST http://localhost:8080/api/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __typename }"}'
```

## Ports Reference

| Port | Service | Purpose |
|------|---------|---------|
| 8080 | DataHub GMS | GraphQL API (backend) |
| 3001 | CORS Proxy | Adds CORS headers for browser access |
| 8765 | HTTP Server | Serves HTML GraphQL client |
| 9002 | DataHub Frontend | DataHub React UI |

## Advanced: Building a GraphRAG Application

To build a full GraphRAG application:

1. **Generate Embeddings**
   - Use OpenAI, Cohere, or open-source embedding models
   - Embed dataset descriptions, column names, tags
   - Store in `vectors.json` or a vector database

2. **Implement Semantic Search**
   - Compute cosine similarity between query and dataset embeddings
   - Return top-K most relevant datasets

3. **Enrich with GraphQL**
   - Query detailed metadata for matched datasets
   - Include columns, lineage, assertions, ownership
   - Build comprehensive context

4. **LLM Integration**
   - Format metadata as structured context
   - Provide to LLM (GPT-4, Claude, etc.)
   - Generate natural language answers

5. **Iterate with Feedback**
   - Use LLM response to refine search
   - Query additional datasets or drill into specific columns
   - Build multi-turn conversations

## Troubleshooting

### CORS Errors in Browser
**Problem:** `Failed to fetch` or CORS policy errors
**Solution:** Ensure the CORS proxy (`graphql-proxy.js`) is running on port 3001

### Empty Responses
**Problem:** Queries return `null` for dataset
**Solution:**
- Verify the dataset URN exists in DataHub
- Check the platform name matches (e.g., `snowflake`, `mysql`)
- Ensure DataHub has ingested the metadata

### Slow Queries
**Problem:** GraphQL queries take 10+ seconds
**Solution:**
- DataHub is warming up (first query after restart is slow)
- Check Elasticsearch health: `curl http://localhost:9200/_cluster/health`
- Simplify query to fetch less data

## Resources

- [DataHub GraphQL API Docs](https://datahubproject.io/docs/api/graphql/)
- [DataHub Entity Types](https://datahubproject.io/docs/what/entity/)
- [GraphQL Query Reference](https://datahubproject.io/docs/api/graphql/queries/)
- [DataHub Metadata Model](https://datahubproject.io/docs/what/metadata-model/)

## Next Steps

- Integrate with LangChain for RAG pipelines
- Build a vector database (Pinecone, Weaviate, Qdrant)
- Create a Streamlit/Gradio UI for natural language queries
- Implement caching for frequently accessed metadata
- Add authentication for production deployments
However, 