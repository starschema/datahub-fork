/**
 * Test Queries for GraphRAG Demo
 * Run with: node test-queries.js
 */

import fetch from 'node-fetch';

const GRAPHQL_URL = 'http://localhost:4000';

async function runQuery(query, variables = {}) {
  const response = await fetch(GRAPHQL_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, variables })
  });

  const result = await response.json();
  return result.data;
}

async function testQueries() {
  console.log('🧪 Testing GraphRAG Queries...\n');

  try {
    // Test 1: Health Check
    console.log('1️⃣  Health Check');
    const healthResult = await runQuery('query { health }');
    console.log('   Result:', healthResult.health);
    console.log('   ✅ Passed\n');

    // Test 2: Semantic Search
    console.log('2️⃣  Semantic Search');
    const searchQuery = `
      query {
        semanticSearch(query: "customer data", limit: 5) {
          query
          total
          results {
            urn
            name
            type
            platform
            score
          }
        }
      }
    `;
    const searchResult = await runQuery(searchQuery);
    console.log(`   Query: "${searchResult.semanticSearch.query}"`);
    console.log(`   Results: ${searchResult.semanticSearch.total}`);
    searchResult.semanticSearch.results.forEach((r, idx) => {
      console.log(`   [${idx + 1}] ${r.name} (${r.platform}) - Score: ${r.score.toFixed(3)}`);
    });
    console.log('   ✅ Passed\n');

    // Test 3: Ask DataHub (Simple)
    console.log('3️⃣  Ask DataHub - Simple Question');
    const askQuery1 = `
      query {
        askDataHub(question: "What datasets do we have?") {
          question
          answer
          sources {
            name
            relevance
          }
          confidence
        }
      }
    `;
    const askResult1 = await runQuery(askQuery1);
    console.log(`   Question: "${askResult1.askDataHub.question}"`);
    console.log(`   Answer: ${askResult1.askDataHub.answer.substring(0, 200)}...`);
    console.log(`   Sources: ${askResult1.askDataHub.sources.length}`);
    console.log(`   Confidence: ${askResult1.askDataHub.confidence?.toFixed(3) || 'N/A'}`);
    console.log('   ✅ Passed\n');

    // Test 4: Ask DataHub (Complex)
    console.log('4️⃣  Ask DataHub - Complex Question');
    const askQuery2 = `
      query {
        askDataHub(question: "Which datasets contain customer information and who owns them?") {
          question
          answer
          sources {
            name
            urn
            relevance
          }
        }
      }
    `;
    const askResult2 = await runQuery(askQuery2);
    console.log(`   Question: "${askResult2.askDataHub.question}"`);
    console.log(`   Answer:\n   ${askResult2.askDataHub.answer.replace(/\n/g, '\n   ')}`);
    console.log(`\n   Sources used:`);
    askResult2.askDataHub.sources.forEach((s, idx) => {
      console.log(`   [${idx + 1}] ${s.name} (relevance: ${s.relevance.toFixed(3)})`);
    });
    console.log('   ✅ Passed\n');

    console.log('✅ All tests passed!');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error(error);
  }
}

// Run tests
testQueries();
