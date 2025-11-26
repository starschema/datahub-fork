# AI Query Integration

This directory contains the React components for the AI Query feature, which allows users to ask questions about their data using natural language powered by GPT-4.

## Architecture

The AI Query feature uses a **proxy architecture** to integrate with the NL Query Server:

```
User Browser
    ↓
DataHub Frontend (React on port 9002)
    ↓ (HTTP requests to /api/nl-query/*)
Vite Dev Proxy → NL Query Server (Node.js on port 5000)
    ↓ (HTTP requests to http://localhost:8080/api/graphql)
DataHub GMS (Backend GraphQL API on port 8080)
```

### Components

- **`AiQueryPage.tsx`** - Main container component for the AI Query page
- **`components/QueryInput.tsx`** - Input interface with example queries
- **`components/QueryResults.tsx`** - Results display with loading and error states
- **`components/GraphQLQueryDisplay.tsx`** - Syntax-highlighted GraphQL query viewer
- **`components/JSONResultDisplay.tsx`** - Collapsible JSON results viewer
- **`utils/api.ts`** - API client for communicating with NL Query Server

### Key Features

1. **Natural Language Processing** - Converts user questions to GraphQL queries using GPT-4
2. **Query Caching** - Caches generated GraphQL queries for frequently asked questions
3. **Syntax Highlighting** - Displays GraphQL queries with syntax highlighting
4. **Copy to Clipboard** - Easy copy buttons for queries and results
5. **Expandable Results** - Collapsible JSON viewer for large result sets

## Setup

### Prerequisites

1. **NL Query Server must be running on port 5000**
   ```bash
   # From the DataHub root directory
   node nl-query-server-v2-cached.js
   ```

2. **DataHub GMS must be running on port 8080**
   ```bash
   # Usually started via docker-compose or quickstart
   ```

3. **OpenAI API Key must be configured**
   ```bash
   # In .env file at DataHub root
   OPENAI_API_KEY=your-api-key-here
   ```

### Development

1. **Start the React dev server:**
   ```bash
   cd datahub-web-react
   ../gradlew yarnServe
   ```
   This starts the React app on **port 3000** with hot reload.

2. **The proxy configuration in `vite.config.ts` automatically forwards:**
   - `/api/nl-query/*` → `http://localhost:5000/`
   - This is already configured - no changes needed!

3. **Navigate to AI Query:**
   - Open: `http://localhost:3000/ai-query`
   - Or click the "AI Query" link in the DataHub header

### Production Build

For production deployment:

```bash
cd datahub-web-react
../gradlew build
```

The built assets will be in `dist/` and will be served by the DataHub frontend on port 9002.

**Important for Production:** You'll need to configure a backend proxy (nginx, etc.) to route `/api/nl-query/*` requests to the NL Query Server on port 5000.

## API Endpoints

The NL Query Server (port 5000) exposes these endpoints:

### POST `/query`
Query DataHub using natural language

**Request:**
```json
{
  "question": "search for customer datasets"
}
```

**Response:**
```json
{
  "question": "search for customer datasets",
  "graphqlQuery": "query { search(...) { ... } }",
  "results": {
    "data": { ... }
  },
  "suggestion": "Optional suggestion text"
}
```

### POST `/entity-summary`
Get detailed summary for a specific entity

**Request:**
```json
{
  "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,test_db.tpch_1000.customer,PROD)"
}
```

**Response:**
```json
{
  "urn": "...",
  "type": "dataset",
  "name": "CUSTOMER",
  "platform": "snowflake",
  "stats": { ... },
  "lineage": { ... }
}
```

### GET `/health`
Health check for the NL Query Server

**Response:**
```json
{
  "status": "ok",
  "openai": true,
  "cacheSize": 8
}
```

## Navigation Integration

The AI Query link has been added to the DataHub header navigation in:
- **File:** `src/app/shared/admin/HeaderLinks.tsx`
- **Route:** `/ai-query` (defined in `src/conf/Global.ts`)
- **Icon:** `CommentOutlined` from Ant Design Icons

## Testing

### Manual Testing

1. **Start all services:**
   ```bash
   # Terminal 1: Start NL Query Server
   node nl-query-server-v2-cached.js

   # Terminal 2: Start React dev server
   cd datahub-web-react && ../gradlew yarnServe
   ```

2. **Test the integration:**
   - Navigate to `http://localhost:3000/ai-query`
   - Try example queries like:
     - "search for customer datasets"
     - "show me columns in test_db.tpch_1000.customer"
     - "what data quality checks exist"

3. **Verify proxy is working:**
   - Check browser DevTools Network tab
   - API calls should go to `/api/nl-query/query` (not `http://localhost:5000`)
   - No CORS errors should appear

### Troubleshooting

**Issue:** "NL Query server is not available"
- **Solution:** Make sure NL Query Server is running on port 5000
- **Check:** Run `curl http://localhost:5000/health`

**Issue:** CORS errors in browser console
- **Solution:** This means the proxy isn't working. Make sure you're accessing the app through the dev server (port 3000), not directly opening the HTML file.

**Issue:** "Query failed with status 401"
- **Solution:** DataHub GMS authentication is enabled. Check `METADATA_SERVICE_AUTH_ENABLED` environment variable.

**Issue:** GraphQL syntax highlighting not working
- **Solution:** This is cosmetic only. The queries still work. Check browser console for any JavaScript errors.

## Future Enhancements

Potential improvements for the AI Query feature:

1. **Entity Selection UI** - Add interactive UI for selecting entities from search results
2. **Query History** - Show recent queries and allow re-running them
3. **Smart Suggestions** - Show suggested follow-up questions based on results
4. **Export Results** - Download results as CSV or JSON
5. **Query Templates** - Pre-built query templates for common use cases
6. **Collaborative Queries** - Share queries with team members

## Related Files

- **Proxy Config:** `vite.config.ts` - Lines 48-53
- **Routes:** `src/app/SearchRoutes.tsx` - Line 90
- **Page Routes:** `src/conf/Global.ts` - Line 39
- **Header Navigation:** `src/app/shared/admin/HeaderLinks.tsx` - Lines 159-170
- **NL Query Server:** `../../nl-query-server-v2-cached.js`
