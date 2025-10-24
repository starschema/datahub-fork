/**
 * GraphRAG Demo Server
 * Standalone GraphQL server for DataHub semantic search and Q&A
 */

import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import { readFileSync, existsSync } from 'fs';
import { config } from 'dotenv';
import { DataHubClient } from './datahubClient.js';
import { OpenAIClient } from './openaiClient.js';
import { VectorStore } from './vectorStore.js';

// Load environment variables
config();

// Initialize clients
const datahubClient = new DataHubClient(
  process.env.DATAHUB_GQL_URL || 'http://localhost:8080/api/graphql',
  process.env.DATAHUB_TOKEN
);

const openaiClient = new OpenAIClient(process.env.OPENAI_API_KEY);
const vectorStore = new VectorStore();

// Load pre-indexed vectors if available
if (existsSync('./vectors.json')) {
  try {
    const data = JSON.parse(readFileSync('./vectors.json', 'utf-8'));
    for (const [urn, vectorData] of data.vectors) {
      vectorStore.store(urn, vectorData.embedding, vectorData.metadata);
    }
    console.log(`✅ Loaded ${vectorStore.size()} pre-indexed vectors`);
  } catch (error) {
    console.warn('⚠️  Failed to load vectors.json:', error.message);
  }
} else {
  console.warn('⚠️  No vectors.json found. Run "npm run index" first!');
}

// Load GraphQL schema
const typeDefs = readFileSync('./schema.graphql', 'utf-8');

// Resolvers
const resolvers = {
  Query: {
    health: () => 'OK',

    /**
     * Semantic Search Resolver
     */
    semanticSearch: async (_, { query, limit = 10 }) => {
      console.log(`[SemanticSearch] Query: "${query}"`);

      try {
        // Generate query embedding
        const queryEmbedding = await openaiClient.generateEmbedding(query);

        // Search vector store
        const results = vectorStore.search(queryEmbedding, limit, 0.4);

        console.log(`[SemanticSearch] Found ${results.length} results`);

        return {
          query,
          results,
          total: results.length
        };
      } catch (error) {
        console.error('[SemanticSearch] Error:', error.message);
        throw new Error(`Semantic search failed: ${error.message}`);
      }
    },

    /**
     * Ask DataHub Resolver (RAG)
     */
    askDataHub: async (_, { question }) => {
      console.log(`[AskDataHub] Question: "${question}"`);

      try {
        // Step 1: Generate question embedding
        const questionEmbedding = await openaiClient.generateEmbedding(question);

        // Step 2: Retrieve relevant entities
        const relevantEntities = vectorStore.search(questionEmbedding, 5, 0.4);

        if (relevantEntities.length === 0) {
          return {
            question,
            answer: "I couldn't find relevant information in the data catalog to answer your question.",
            sources: [],
            confidence: 0.0
          };
        }

        console.log(`[AskDataHub] Retrieved ${relevantEntities.length} relevant entities`);

        // Step 3: Fetch full metadata for context
        const contextEntities = await Promise.all(
          relevantEntities.slice(0, 3).map(async (entity) => {
            try {
              const fullEntity = await datahubClient.getEntity(entity.urn);
              return fullEntity;
            } catch (error) {
              console.warn(`Failed to fetch entity ${entity.urn}:`, error.message);
              return entity;
            }
          })
        );

        // Step 4: Build context string
        const context = contextEntities.map((entity, idx) => {
          return `
[${idx + 1}] ${entity.name}
   URN: ${entity.urn}
   Platform: ${entity.platform}
   Description: ${entity.description || 'No description'}
   ${entity.owners ? `Owners: ${entity.owners.map(o => o.username).join(', ')}` : ''}
   ${entity.tags ? `Tags: ${entity.tags.join(', ')}` : ''}
          `.trim();
        }).join('\n\n');

        // Step 5: Generate answer using LLM
        const answer = await openaiClient.generateAnswer(question, context);

        console.log(`[AskDataHub] Generated answer`);

        // Step 6: Return response with sources
        return {
          question,
          answer,
          sources: relevantEntities.slice(0, 3).map(e => ({
            urn: e.urn,
            name: e.name,
            relevance: e.score
          })),
          confidence: relevantEntities[0]?.score || 0.0
        };
      } catch (error) {
        console.error('[AskDataHub] Error:', error.message);
        throw new Error(`Question answering failed: ${error.message}`);
      }
    }
  }
};

// Create Apollo Server
const server = new ApolloServer({
  typeDefs,
  resolvers,
});

// Start server
const { url } = await startStandaloneServer(server, {
  listen: { port: parseInt(process.env.PORT) || 4000 },
});

console.log(`\n🚀 GraphRAG Demo Server ready at: ${url}`);
console.log(`\n📊 Vector Store: ${vectorStore.size()} entities indexed`);
console.log(`\nTry these queries in GraphQL Playground:`);
console.log(`  - semanticSearch(query: "customer data")`);
console.log(`  - askDataHub(question: "What datasets do we have?")`);
console.log(`\n💡 Remember to run 'npm run index' first to index entities!\n`);

// Export for use by indexer
export { datahubClient, openaiClient, vectorStore };
