# DataHub GraphQL API Documentation

## How to Access GraphQL API

### Base URL
```
http://localhost:8888/api/graphql
```

### Authentication
All requests require a Personal Access Token (PAT) in the Authorization header:
```bash
curl -X POST http://localhost:8888/api/graphql \
  -H "Authorization: Bearer YOUR_PAT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"YOUR_GRAPHQL_QUERY"}'
```

### Your Current PAT
```
eyJhbGciOiJIUzI1NiJ9.eyJhY3RvclR5cGUiOiJVU0VSIiwiYWN0b3JJZCI6ImRhdGFodWIiLCJ0eXBlIjoiUEVSU09OQUwiLCJ2ZXJzaW9uIjoiMiIsImp0aSI6Ijc5NGEyMGM4LTdmY2ItNDE1Mi1iMmY5LWFlMmExMDUxMWM0ZiIsInN1YiI6ImRhdGFodWIiLCJleHAiOjE3NjU2ODU2NjcsImlzcyI6ImRhdGFodWItbWV0YWRhdGEtc2VydmljZSJ9.ctzcDA7mmNb-uipmrzTgVstUPdxHqwYa2SyY46rV5cY
```

---

## Key GraphQL Queries by Category

### 📊 Search & Discovery

#### Search across all entities
```graphql
{
  searchAcrossEntities(
    input: {
      types: [DATASET, DASHBOARD, CHART]
      query: "covid"
      start: 0
      count: 10
    }
  ) {
    total
    searchResults {
      entity {
        urn
        type
        ... on Dataset {
          name
          platform { name }
        }
      }
    }
  }
}
```

#### Search specific entity type
```graphql
{
  search(
    input: {
      type: DATASET
      query: "*"
      start: 0
      count: 10
    }
  ) {
    total
    searchResults {
      entity {
        urn
        type
      }
    }
  }
}
```

#### Browse hierarchy
```graphql
{
  browse(
    input: {
      type: DATASET
      path: ""
      start: 0
      count: 10
    }
  ) {
    total
    entities {
      urn
      type
    }
    groups {
      name
      count
    }
  }
}
```

---

### 🗂️ Ingestion Management (UI: `/ingestion`)

#### List ingestion sources
```graphql
{
  listIngestionSources(input: { start: 0, count: 100 }) {
    total
    ingestionSources {
      urn
      name
      type
      config {
        recipe
      }
      executions(start: 0, count: 10) {
        total
        executionRequests {
          urn
          result {
            status
          }
        }
      }
    }
  }
}
```

#### Get specific ingestion source
```graphql
{
  ingestionSource(urn: "urn:li:dataHubIngestionSource:YOUR_SOURCE_ID") {
    urn
    name
    type
    config {
      recipe
    }
  }
}
```

#### List execution requests (ingestion runs)
```graphql
{
  listExecutionRequests(input: { start: 0, count: 20 }) {
    total
    executionRequests {
      urn
      result {
        status
        startTimeMs
        durationMs
      }
    }
  }
}
```

---

### 🏢 Domains Management (UI: `/domains`)

#### List all domains
```graphql
{
  listDomains(input: { start: 0, count: 100 }) {
    total
    domains {
      urn
      id
      properties {
        name
        description
      }
      entities {
        total
      }
    }
  }
}
```

#### Get specific domain
```graphql
{
  domain(urn: "urn:li:domain:YOUR_DOMAIN_ID") {
    urn
    properties {
      name
      description
    }
    entities(input: { start: 0, count: 10 }) {
      total
      relationships {
        entity {
          urn
          type
        }
      }
    }
  }
}
```

---

### 📋 Structured Properties (UI: `/structured-properties`)

#### List structured properties
```graphql
{
  listStructuredProperties(input: { start: 0, count: 100 }) {
    total
    structuredProperties {
      urn
      definition {
        qualifiedName
        displayName
        description
        valueType
        cardinality
      }
    }
  }
}
```

#### Get specific structured property
```graphql
{
  structuredProperty(urn: "urn:li:structuredProperty:YOUR_PROPERTY_ID") {
    urn
    definition {
      qualifiedName
      displayName
      valueType
    }
  }
}
```

---

### 📈 Analytics (UI: `/analytics`)

#### Get analytics charts
```graphql
{
  getAnalyticsCharts(input: { dashboardName: "GlobalAnalytics" }) {
    charts {
      title
      type
      data
    }
  }
}
```

#### Get metadata analytics
```graphql
{
  getMetadataAnalyticsCharts(input: {}) {
    charts {
      title
      type
      data
    }
  }
}
```

#### Get highlights (key metrics)
```graphql
{
  getHighlights(input: {}) {
    value
    title
    body
  }
}
```

---

### 📚 Glossary

#### Get root glossary terms
```graphql
{
  getRootGlossaryTerms(input: { start: 0, count: 100 }) {
    total
    glossaryTerms {
      urn
      glossaryTermInfo {
        name
        definition
      }
    }
  }
}
```

#### Get specific glossary term
```graphql
{
  glossaryTerm(urn: "urn:li:glossaryTerm:YOUR_TERM_ID") {
    urn
    glossaryTermInfo {
      name
      definition
    }
  }
}
```

---

### 👥 Users & Groups

#### List users
```graphql
{
  listUsers(input: { start: 0, count: 100 }) {
    total
    users {
      urn
      username
      properties {
        displayName
        email
      }
    }
  }
}
```

#### List groups
```graphql
{
  listGroups(input: { start: 0, count: 100 }) {
    total
    groups {
      urn
      name
      properties {
        displayName
        description
      }
    }
  }
}
```

#### Get current user
```graphql
{
  me {
    corpUser {
      urn
      username
      properties {
        displayName
        email
      }
    }
  }
}
```

---

### 🔐 Access Control

#### List access tokens
```graphql
{
  listAccessTokens(input: { start: 0, count: 100 }) {
    total
    tokens {
      urn
      name
      description
      actorUrn
      ownerUrn
      createdAt
      expiresAt
    }
  }
}
```

#### List policies
```graphql
{
  listPolicies(input: { start: 0, count: 100 }) {
    total
    policies {
      urn
      name
      description
      state
      type
    }
  }
}
```

#### List roles
```graphql
{
  listRoles(input: { start: 0, count: 100 }) {
    total
    roles {
      urn
      name
      description
    }
  }
}
```

---

### 🗃️ Entity Operations

#### Get dataset details
```graphql
{
  dataset(urn: "urn:li:dataset:(urn:li:dataPlatform:snowflake,covid19.public.demographics,PROD)") {
    urn
    name
    platform {
      name
    }
    properties {
      name
      description
    }
    schema {
      fields {
        fieldPath
        type
        description
      }
    }
  }
}
```

#### Get multiple entities
```graphql
{
  entities(urns: [
    "urn:li:dataset:...",
    "urn:li:dashboard:..."
  ]) {
    urn
    type
  }
}
```

#### Check if entity exists
```graphql
{
  entityExists(urn: "urn:li:dataset:...")
}
```

---

### 🔍 Introspection (Explore the API)

#### List all available queries
```graphql
{
  __schema {
    queryType {
      fields {
        name
        description
      }
    }
  }
}
```

#### List all available mutations
```graphql
{
  __schema {
    mutationType {
      fields {
        name
        description
      }
    }
  }
}
```

#### Get details about a specific type
```graphql
{
  __type(name: "Dataset") {
    fields {
      name
      type {
        name
        kind
      }
    }
  }
}
```

---

## Common Patterns

### Pagination
Most list queries support pagination:
```graphql
{
  listDomains(input: {
    start: 0,    # Offset
    count: 20    # Page size
  }) {
    total        # Total count
    # ... results
  }
}
```

### Filtering
Search queries support filters:
```graphql
{
  search(input: {
    type: DATASET
    query: "platform:snowflake AND tags:pii"
    filters: [
      { field: "platform", values: ["snowflake"] }
    ]
  }) {
    # ... results
  }
}
```

### Sorting
```graphql
{
  search(input: {
    type: DATASET
    query: "*"
    sort: { field: "created", direction: DESC }
  }) {
    # ... results
  }
}
```

---

## Tools for Exploring the API

### 1. Command Line (curl)
```bash
curl -X POST http://localhost:8888/api/graphql \
  -H "Authorization: Bearer YOUR_PAT" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ me { corpUser { username } } }"}'
```

### 2. Postman
- Create a POST request to `http://localhost:8888/api/graphql`
- Add Header: `Authorization: Bearer YOUR_PAT`
- Body (JSON):
  ```json
  {
    "query": "{ me { corpUser { username } } }"
  }
  ```

### 3. GraphQL Playground (Desktop App)
- Download: https://github.com/graphql/graphql-playground
- URL: `http://localhost:8888/api/graphql`
- HTTP Headers:
  ```json
  {
    "Authorization": "Bearer YOUR_PAT"
  }
  ```

### 4. Python Example
```python
import requests

url = "http://localhost:8888/api/graphql"
headers = {
    "Authorization": "Bearer YOUR_PAT",
    "Content-Type": "application/json"
}
query = """
{
  me {
    corpUser {
      username
    }
  }
}
"""

response = requests.post(url, json={"query": query}, headers=headers)
print(response.json())
```

---

## Saved Files

I've saved the complete GraphQL schema for you:
- **Queries:** `graphql_schema.json`
- **Mutations:** `graphql_mutations.json`

You can explore these files to see all available operations!

---

## Official Documentation

- **DataHub Docs:** https://docs.datahub.com/docs/api/graphql/overview
- **GraphQL Spec:** https://graphql.org/learn/
