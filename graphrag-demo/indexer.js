/**
 * Entity Indexer
 * Fetches entities from DataHub and generates embeddings
 */

import { config } from 'dotenv';
import { DataHubClient } from './datahubClient.js';
import { OpenAIClient } from './openaiClient.js';
import { VectorStore } from './vectorStore.js';

// Load environment variables
config();

const datahubClient = new DataHubClient(
  process.env.DATAHUB_GQL_URL || 'http://localhost:8080/api/graphql',
  process.env.DATAHUB_TOKEN
);

const openaiClient = new OpenAIClient(process.env.OPENAI_API_KEY);
const vectorStore = new VectorStore();

async function indexEntities() {
  console.log('🔍 Fetching entities from DataHub...');

  try {
    // Fetch datasets from DataHub
    const entities = await datahubClient.searchDatasets('*', 0, 100);

    console.log(`📦 Found ${entities.length} entities`);

    if (entities.length === 0) {
      console.log('\n⚠️  No entities found. Make sure DataHub has some datasets indexed.');
      return;
    }

    console.log('\n🧠 Generating embeddings...');

    let indexed = 0;
    let failed = 0;

    for (const entity of entities) {
      try {
        // Convert entity to text
        const text = datahubClient.entityToText(entity);

        // Generate embedding
        const embedding = await openaiClient.generateEmbedding(text);

        // Store in vector store
        vectorStore.store(entity.urn, embedding, {
          name: entity.name,
          type: entity.type,
          platform: entity.platform,
          description: entity.description
        });

        indexed++;
        process.stdout.write(`\rIndexed: ${indexed}/${entities.length}`);

        // Small delay to avoid rate limits
        await new Promise(resolve => setTimeout(resolve, 200));

      } catch (error) {
        failed++;
        console.error(`\n❌ Failed to index ${entity.urn}: ${error.message}`);
      }
    }

    console.log(`\n\n✅ Indexing complete!`);
    console.log(`   Successfully indexed: ${indexed}`);
    console.log(`   Failed: ${failed}`);
    console.log(`   Total vectors: ${vectorStore.size()}`);

    // Save to file for the server to load
    const data = {
      vectors: Array.from(vectorStore.vectors.entries())
    };

    const fs = await import('fs');
    fs.writeFileSync('./vectors.json', JSON.stringify(data, null, 2));

    console.log(`\n💾 Vectors saved to vectors.json`);
    console.log(`\n🚀 Now run 'npm start' to start the GraphRAG server!`);

  } catch (error) {
    console.error('\n❌ Indexing failed:', error.message);
    process.exit(1);
  }
}

// Run indexer
indexEntities();
