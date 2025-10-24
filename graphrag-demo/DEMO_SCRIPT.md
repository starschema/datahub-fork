# GraphRAG Demo Script

Use this script when demonstrating GraphRAG with DataHub.

## Preparation (Before Demo)

1. **Ensure DataHub is running:**
   ```bash
   # In DataHub directory
   ./gradlew quickstartDebug
   ```

2. **Install dependencies:**
   ```bash
   cd graphrag-demo
   npm install
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

4. **Index entities (takes 2-5 min):**
   ```bash
   npm run index
   ```

## Demo Flow (10 minutes)

### Part 1: Introduction (2 minutes)

**"Today I'll demonstrate GraphRAG - combining DataHub's metadata graph with semantic search and LLM-powered Q&A."**

Show the architecture diagram:
```
DataHub → GraphQL Gateway → OpenAI API → Results
```

**"This is a simplified demo with a standalone GraphQL server. Production version would integrate directly into DataHub."**

### Part 2: Start the Server (1 minute)

```bash
npm start
```

Show terminal output:
```
✅ Loaded 47 pre-indexed vectors
🚀 GraphRAG Demo Server ready at: http://localhost:4000/
📊 Vector Store: 47 entities indexed
```

**"The server loaded 47 pre-indexed datasets from DataHub with their embeddings."**

Open browser to `http://localhost:4000`

### Part 3: Semantic Search Demo (3 minutes)

**"Let's start with semantic search. Traditional keyword search requires exact matches. Semantic search understands meaning."**

#### Query 1: Basic Search

```graphql
query {
  semanticSearch(query: "customer revenue data", limit: 5) {
    total
    results {
      name
      platform
      description
      score
    }
  }
}
```

**"Notice it found datasets even if they don't have the exact words 'customer revenue' in the name. The similarity scores show relevance."**

#### Query 2: Conceptual Search

```graphql
query {
  semanticSearch(query: "user activity and behavior tracking", limit: 5) {
    results {
      name
      platform
      score
    }
  }
}
```

**"It understands concepts - 'user activity' matches 'clickstream', 'events', 'sessions', etc."**

### Part 4: Natural Language Q&A (4 minutes)

**"Now the powerful part - asking questions about your data catalog in plain English."**

#### Query 1: Discovery Question

```graphql
query {
  askDataHub(question: "What datasets do we have?") {
    answer
    sources {
      name
    }
  }
}
```

**"The LLM generates a natural language answer based on actual DataHub metadata. Notice the sources cited."**

#### Query 2: Ownership Question

```graphql
query {
  askDataHub(question: "Which datasets contain customer information and who owns them?") {
    answer
    sources {
      name
      relevance
    }
  }
}
```

**"It retrieves relevant entities using semantic search, fetches their metadata from DataHub (including ownership), and generates a comprehensive answer."**

Point out:
- ✅ Accurate information from DataHub
- ✅ Natural language response
- ✅ Citations to source datasets
- ✅ Relevance scores

#### Query 3: Complex Analysis

```graphql
query {
  askDataHub(question: "What data is available for building a customer churn prediction model?") {
    answer
    sources {
      name
      relevance
    }
  }
}
```

**"This shows understanding of complex questions that require domain knowledge."**

### Part 5: How It Works (2 minutes)

Show the code flow briefly:

1. **Vector Store** (`vectorStore.js`) - In-memory cosine similarity
2. **DataHub Client** (`datahubClient.js`) - Fetches metadata
3. **OpenAI Client** (`openaiClient.js`) - Embeddings + GPT-4
4. **Resolvers** (`index.js`) - Orchestrates the flow

**"For semantic search:"**
```
User query → Embedding → Vector search → Results
```

**"For RAG:"**
```
Question → Find relevant entities → Fetch metadata → Build context → LLM answer
```

### Part 6: Q&A and Next Steps (remaining time)

**Common Questions:**

**Q: "Does this work with our production DataHub?"**
A: Yes! Just point `DATAHUB_GQL_URL` to your instance. This demo uses DataHub's existing GraphQL API.

**Q: "How accurate are the answers?"**
A: Very accurate because they're based on your actual metadata. The LLM just formats it naturally.

**Q: "What about cost?"**
A: For 50 entities, ~$0.30 for testing. Production can use cheaper models or self-hosted LLMs.

**Q: "Can this work without OpenAI?"**
A: Yes! Can use pgvector + sentence-transformers + local LLM (Llama, Mistral).

**Q: "How do we deploy this to production?"**
A: Full implementation guide available - integrates directly into DataHub's GraphQL layer with proper vector DB (Pinecone/Weaviate), caching, auth, etc.

### Closing

**"This demonstrates GraphRAG's potential for DataHub:**
- ✅ Natural language data discovery
- ✅ Semantic search beyond keywords
- ✅ AI-powered Q&A with citations
- ✅ Works with existing DataHub metadata"**

**Next Steps:**
- See `GRAPHRAG_IMPLEMENTATION_GUIDE.md` for production version
- This demo code is in `graphrag-demo/` directory
- All source code and docs available

## Demo Variations

### Short Demo (5 minutes)
- Skip explanation, just show 2-3 queries
- Focus on semantic search + one complex Q&A

### Technical Deep Dive (20 minutes)
- Show code in VS Code
- Explain vector embeddings
- Demonstrate indexing process
- Show how resolvers work

### Business-Focused (10 minutes)
- Focus on use cases (discovery, impact analysis)
- Show ROI (faster data finding, better governance)
- Less technical details

## Backup Plan

If something goes wrong:

1. **Server won't start:**
   - Check DataHub is running
   - Verify OpenAI API key
   - Show pre-recorded video instead

2. **No results:**
   - Check `vectors.json` exists
   - Re-run `npm run index`
   - Use backup demo dataset

3. **OpenAI errors:**
   - Use cached example responses
   - Show code and explain what would happen

## Demo Tips

✅ **Do:**
- Test everything 5 minutes before demo
- Have backup queries ready
- Explain at audience's technical level
- Show real DataHub data (not mock)
- Emphasize this is a quick POC

❌ **Don't:**
- Promise features not yet built
- Claim 100% accuracy
- Skip explaining it's a demo
- Assume audience knows GraphQL
- Forget to mention cost/resources needed

## Recording Demo

If recording for async viewing:

1. **Screen setup:**
   - Terminal (bottom half)
   - Browser with GraphQL Playground (top half)
   - Clear, readable fonts

2. **Narration script:**
   - Introduce yourself and topic
   - Follow the 10-minute flow above
   - Pause briefly between sections
   - Summarize key takeaways

3. **Editing:**
   - Speed up indexing process (show start/end)
   - Add captions for queries
   - Include architecture diagram slides
   - End with "Questions?" slide

---

**Good luck with your demo!** 🚀
