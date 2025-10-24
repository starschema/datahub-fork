/**
 * Simple in-memory vector store for demo
 * Uses cosine similarity for search
 */

export class VectorStore {
  constructor() {
    this.vectors = new Map(); // urn -> {embedding: [], metadata: {}}
  }

  /**
   * Store a vector with metadata
   */
  store(urn, embedding, metadata) {
    this.vectors.set(urn, {
      embedding,
      metadata: {
        urn,
        ...metadata
      }
    });
  }

  /**
   * Search for similar vectors using cosine similarity
   */
  search(queryEmbedding, limit = 10, threshold = 0.0) {
    const results = [];

    for (const [urn, data] of this.vectors.entries()) {
      const similarity = this.cosineSimilarity(queryEmbedding, data.embedding);

      if (similarity >= threshold) {
        results.push({
          ...data.metadata,
          score: similarity
        });
      }
    }

    // Sort by score descending
    results.sort((a, b) => b.score - a.score);

    return results.slice(0, limit);
  }

  /**
   * Calculate cosine similarity between two vectors
   */
  cosineSimilarity(a, b) {
    if (a.length !== b.length) {
      throw new Error('Vectors must have same length');
    }

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    const magnitude = Math.sqrt(normA) * Math.sqrt(normB);
    return magnitude === 0 ? 0 : dotProduct / magnitude;
  }

  /**
   * Get vector by URN
   */
  get(urn) {
    return this.vectors.get(urn);
  }

  /**
   * Check if URN exists
   */
  has(urn) {
    return this.vectors.has(urn);
  }

  /**
   * Get total count
   */
  size() {
    return this.vectors.size;
  }

  /**
   * Clear all vectors
   */
  clear() {
    this.vectors.clear();
  }
}
