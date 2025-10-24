# GraphRAG Demo - Quick Start

**Get running in 5 minutes!**

## Prerequisites

- ✅ DataHub running at `http://localhost:8080`
- ✅ Node.js 18+ installed
- ✅ OpenAI API key

## 4 Simple Steps

### 1. Install

```bash
cd graphrag-demo
npm install
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:
```env
OPENAI_API_KEY=sk-your-key-here
```

### 3. Index DataHub Entities

```bash
npm run index
```

Wait 2-5 minutes while it:
- Fetches datasets from DataHub
- Generates embeddings
- Saves to `vectors.json`

### 4. Start Server

```bash
npm start
```

Opens at: `http://localhost:4000`

## Try It!

### Semantic Search

```graphql
query {
  semanticSearch(query: "customer data") {
    results {
      name
      score
    }
  }
}
```

### Ask Questions

```graphql
query {
  askDataHub(question: "What datasets do we have?") {
    answer
  }
}
```

## What Next?

- See `README.md` for detailed documentation
- See `DEMO_SCRIPT.md` for presentation guide
- See `test-queries.js` for more examples

## Troubleshooting

**No DataHub found?**
```bash
# Make sure DataHub is running
curl http://localhost:8080/api/graphql
```

**OpenAI errors?**
- Check API key in `.env`
- Verify billing enabled on OpenAI account

**No entities indexed?**
- DataHub must have datasets ingested
- Check DataHub UI to verify data exists

---

That's it! You now have GraphRAG working with DataHub. 🎉
