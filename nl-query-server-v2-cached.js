/**
 * NL Query Server v2 with Caching
 *
 * A Node.js server that converts natural language questions into DataHub GraphQL queries
 * using OpenAI's GPT-4, with intelligent caching for frequently asked questions.
 *
 * Architecture:
 *   User Question → OpenAI GPT-4 → GraphQL Query → DataHub GMS → Results
 *
 * Required Environment Variables:
 *   - OPENAI_API_KEY: Your OpenAI API key
 *   - DATAHUB_GMS_URL: DataHub GMS URL (default: http://localhost:8080)
 *
 * Usage:
 *   node nl-query-server-v2-cached.js
 *
 * Endpoints:
 *   POST /query - Convert NL question to GraphQL and execute
 *   POST /entity-summary - Get detailed entity summary
 *   GET /health - Server health check
 */

const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.NL_QUERY_PORT || 5000;
const DATAHUB_GMS_URL = process.env.DATAHUB_GMS_URL || 'http://localhost:8080';
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const DATAHUB_TOKEN = process.env.DATAHUB_TOKEN;

// Query cache: stores GraphQL queries for frequently asked questions
const queryCache = new Map();

// Middleware - CORS configuration for credentials
app.use(cors({
    origin: ['http://localhost:3000', 'http://localhost:9002'],
    credentials: true
}));
app.use(express.json());

// Request logging
app.use((req, res, next) => {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
    next();
});

/**
 * Call OpenAI API to convert natural language to GraphQL
 */
async function generateGraphQLQuery(question) {
    if (!OPENAI_API_KEY) {
        throw new Error('OPENAI_API_KEY not configured');
    }

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${OPENAI_API_KEY}`
        },
        body: JSON.stringify({
            model: 'gpt-4',
            messages: [
                {
                    role: 'system',
                    content: `You are a DataHub GraphQL query generator. Convert natural language questions into valid DataHub GraphQL queries.

DataHub GraphQL Schema Overview:
- search(input: SearchInput!): Search for entities
  - query: String (search term)
  - type: EntityType (DATASET, DASHBOARD, CHART, etc.)
  - start: Int, count: Int (pagination)

- dataset(urn: String!): Get dataset details
  - Returns: Dataset with properties, schema, owners, tags, etc.

- listDatasets(input: ListInput!): List all datasets
  - start: Int, count: Int

Common Query Patterns:
1. Search: query { search(input: {query: "customer", type: DATASET, start: 0, count: 10}) { searchResults { entity { urn, ... on Dataset { name } } } } }
2. Get Dataset: query { dataset(urn: "urn:li:dataset:...") { properties { name, description } } }
3. List: query { listDatasets(input: {start: 0, count: 10}) { datasets { urn, name } } }

Return ONLY the GraphQL query, no explanations.`
                },
                {
                    role: 'user',
                    content: question
                }
            ],
            temperature: 0.3,
            max_tokens: 500
        })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(`OpenAI API error: ${error.error?.message || response.statusText}`);
    }

    const data = await response.json();
    return data.choices[0].message.content.trim();
}

/**
 * Get DataHub access token for system authentication
 */
async function getDataHubToken() {
    return DATAHUB_TOKEN || null;
}

/**
 * Execute GraphQL query against DataHub GMS
 */
async function executeGraphQL(query) {
    const headers = {
        'Content-Type': 'application/json',
    };

    // Add authentication if token is available
    const token = await getDataHubToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${DATAHUB_GMS_URL}/api/graphql`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ query })
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`DataHub GMS error: ${response.statusText} - ${errorText}`);
    }

    return response.json();
}

/**
 * POST /query
 * Convert natural language question to GraphQL and execute
 */
app.post('/query', async (req, res) => {
    try {
        const { question } = req.body;

        if (!question) {
            return res.status(400).json({ error: 'Question is required' });
        }

        console.log(`Processing question: "${question}"`);

        // Check cache first
        let graphqlQuery = queryCache.get(question.toLowerCase());
        let cached = !!graphqlQuery;

        if (!graphqlQuery) {
            // Generate new query using OpenAI
            console.log('Generating GraphQL query with OpenAI...');
            graphqlQuery = await generateGraphQLQuery(question);

            // Cache the query
            queryCache.set(question.toLowerCase(), graphqlQuery);
            console.log(`Query cached. Cache size: ${queryCache.size}`);
        } else {
            console.log('Using cached GraphQL query');
        }

        // Execute the GraphQL query
        console.log('Executing GraphQL query against DataHub...');
        const results = await executeGraphQL(graphqlQuery);

        // Return response
        res.json({
            question,
            graphqlQuery,
            results,
            cached,
            suggestion: null // Can add intelligent suggestions here
        });

    } catch (error) {
        console.error('Error processing query:', error);
        res.status(500).json({
            error: error.message,
            question: req.body.question
        });
    }
});

/**
 * POST /entity-summary
 * Get detailed summary for a specific entity
 */
app.post('/entity-summary', async (req, res) => {
    try {
        const { urn } = req.body;

        if (!urn) {
            return res.status(400).json({ error: 'URN is required' });
        }

        console.log(`Fetching entity summary for: ${urn}`);

        // Build GraphQL query to fetch entity details
        const query = `
            query {
                dataset(urn: "${urn}") {
                    urn
                    type
                    name
                    platform {
                        name
                    }
                    properties {
                        name
                        description
                        qualifiedName
                    }
                    schemaMetadata {
                        fields {
                            fieldPath
                            type
                            nativeDataType
                        }
                    }
                    ownership {
                        owners {
                            owner {
                                ... on CorpUser {
                                    username
                                    info {
                                        displayName
                                    }
                                }
                            }
                        }
                    }
                    tags {
                        tags {
                            tag {
                                name
                            }
                        }
                    }
                    institutionalMemory {
                        elements {
                            url
                            description
                        }
                    }
                }
            }
        `;

        const results = await executeGraphQL(query);

        // Transform results into summary format
        const dataset = results.data?.dataset;
        if (!dataset) {
            return res.status(404).json({ error: 'Entity not found' });
        }

        const summary = {
            urn: dataset.urn,
            type: dataset.type || 'dataset',
            name: dataset.name || dataset.properties?.name,
            platform: dataset.platform?.name || 'unknown',
            description: dataset.properties?.description,
            qualifiedName: dataset.properties?.qualifiedName,
            stats: {
                rowCount: null,
                columnCount: dataset.schemaMetadata?.fields?.length || 0,
                sizeInBytes: null,
                lastProfiled: null
            },
            owners: dataset.ownership?.owners?.map(o => ({
                username: o.owner.username,
                displayName: o.owner.info?.displayName || o.owner.username
            })) || [],
            tags: dataset.tags?.tags?.map(t => ({
                name: t.tag.name
            })) || [],
            domain: null,
            container: null,
            subTypes: [],
            lastUpdated: null,
            lineage: {
                upstream: { total: 0, byType: {} },
                downstream: { total: 0, byType: {} }
            }
        };

        res.json(summary);

    } catch (error) {
        console.error('Error fetching entity summary:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * GET /health
 * Health check endpoint
 */
app.get('/health', async (req, res) => {
    try {
        // Check OpenAI connectivity
        const openaiAvailable = !!OPENAI_API_KEY;

        // Check DataHub GMS connectivity
        let datahubAvailable = false;
        try {
            const response = await fetch(`${DATAHUB_GMS_URL}/health`, {
                method: 'GET',
                timeout: 3000
            });
            datahubAvailable = response.ok;
        } catch (err) {
            console.warn('DataHub GMS health check failed:', err.message);
        }

        res.json({
            status: 'ok',
            openai: openaiAvailable,
            datahub: datahubAvailable,
            cacheSize: queryCache.size,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(500).json({
            status: 'error',
            error: error.message
        });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    res.status(500).json({
        error: 'Internal server error',
        message: err.message
    });
});

// Start server
app.listen(PORT, () => {
    console.log('='.repeat(60));
    console.log('NL Query Server v2 (with caching)');
    console.log('='.repeat(60));
    console.log(`Server running on: http://localhost:${PORT}`);
    console.log(`DataHub GMS URL: ${DATAHUB_GMS_URL}`);
    console.log(`OpenAI API Key: ${OPENAI_API_KEY ? '✓ Configured' : '✗ Missing'}`);
    console.log('='.repeat(60));
    console.log('\nEndpoints:');
    console.log(`  POST   http://localhost:${PORT}/query`);
    console.log(`  POST   http://localhost:${PORT}/entity-summary`);
    console.log(`  GET    http://localhost:${PORT}/health`);
    console.log('='.repeat(60));

    if (!OPENAI_API_KEY) {
        console.warn('\n⚠️  WARNING: OPENAI_API_KEY not configured!');
        console.warn('   Set it in your .env file or environment variables.\n');
    }
});
