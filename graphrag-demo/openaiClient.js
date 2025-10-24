/**
 * OpenAI Client for embeddings and LLM
 */

import OpenAI from 'openai';

export class OpenAIClient {
  constructor(apiKey) {
    this.client = new OpenAI({ apiKey });
    this.embeddingModel = 'text-embedding-3-small';
    this.chatModel = 'gpt-3.5-turbo';
  }

  /**
   * Generate embedding for text
   */
  async generateEmbedding(text) {
    try {
      const response = await this.client.embeddings.create({
        model: this.embeddingModel,
        input: text,
      });

      return response.data[0].embedding;
    } catch (error) {
      console.error('Embedding generation failed:', error.message);
      throw error;
    }
  }

  /**
   * Generate embeddings for multiple texts
   */
  async generateEmbeddings(texts) {
    const embeddings = [];

    for (const text of texts) {
      const embedding = await this.generateEmbedding(text);
      embeddings.push(embedding);

      // Small delay to avoid rate limits
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    return embeddings;
  }

  /**
   * Generate answer using GPT-4
   */
  async generateAnswer(question, context) {
    const systemPrompt = `You are DataHub AI, an expert assistant for data discovery and metadata management.
Your role is to help users understand their data catalog by answering questions based on metadata.

Guidelines:
- Provide accurate, concise answers based on the provided context
- Cite specific entities when making claims (use entity names)
- If information is missing from context, say so clearly
- Use technical terms appropriately for a data-savvy audience
- Be helpful and conversational`;

    const userPrompt = `Question: ${question}

Available Data Catalog Information:
${context}

Answer the question based on the information above. Be specific and cite entity names.`;

    try {
      const response = await this.client.chat.completions.create({
        model: this.chatModel,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt }
        ],
        temperature: 0.7,
        max_tokens: 500
      });

      return response.choices[0].message.content;
    } catch (error) {
      console.error('Answer generation failed:', error.message);
      throw error;
    }
  }

  /**
   * Extract key concepts from query (for query understanding)
   */
  async extractConcepts(query) {
    try {
      const response = await this.client.chat.completions.create({
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: 'Extract 3-5 key concepts from the user query. Return as comma-separated list.'
          },
          { role: 'user', content: query }
        ],
        temperature: 0.3,
        max_tokens: 50
      });

      const concepts = response.choices[0].message.content
        .split(',')
        .map(c => c.trim())
        .filter(c => c);

      return concepts;
    } catch (error) {
      console.error('Concept extraction failed:', error.message);
      return [];
    }
  }
}
