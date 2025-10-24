/**
 * DataHub GraphQL Client
 * Connects to existing DataHub instance and fetches metadata
 */

import fetch from 'node-fetch';

export class DataHubClient {
  constructor(url, token = null) {
    this.url = url;
    this.token = token;
  }

  /**
   * Execute GraphQL query against DataHub
   */
  async query(query, variables = {}) {
    const headers = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(this.url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ query, variables })
    });

    if (!response.ok) {
      throw new Error(`DataHub query failed: ${response.statusText}`);
    }

    const result = await response.json();

    if (result.errors) {
      throw new Error(`GraphQL errors: ${JSON.stringify(result.errors)}`);
    }

    return result.data;
  }

  /**
   * Search datasets in DataHub
   */
  async searchDatasets(query = '*', start = 0, count = 100) {
    const gqlQuery = `
      query SearchDatasets($query: String!, $start: Int!, $count: Int!) {
        search(input: {
          type: DATASET
          query: $query
          start: $start
          count: $count
        }) {
          searchResults {
            entity {
              urn
              type
              ... on Dataset {
                name
                description
                platform {
                  name
                }
                properties {
                  name
                  description
                }
                tags {
                  tags {
                    tag {
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
    `;

    const data = await this.query(gqlQuery, { query, start, count });
    return data.search.searchResults.map(r => this.normalizeEntity(r.entity));
  }

  /**
   * Get entity by URN
   */
  async getEntity(urn) {
    const gqlQuery = `
      query GetEntity($urn: String!) {
        entity(urn: $urn) {
          urn
          type
          ... on Dataset {
            name
            description
            platform {
              name
            }
            properties {
              name
              description
            }
            ownership {
              owners {
                owner {
                  ... on CorpUser {
                    urn
                    username
                  }
                }
                type
              }
            }
            tags {
              tags {
                tag {
                  name
                }
              }
            }
          }
        }
      }
    `;

    const data = await this.query(gqlQuery, { urn });
    return this.normalizeEntity(data.entity);
  }

  /**
   * Normalize entity to common format
   */
  normalizeEntity(entity) {
    if (!entity) return null;

    const normalized = {
      urn: entity.urn,
      type: entity.type,
      name: entity.name || entity.properties?.name || 'Unknown',
      description: entity.description || entity.properties?.description || '',
      platform: entity.platform?.name || 'unknown',
    };

    // Extract tags
    if (entity.tags?.tags) {
      normalized.tags = entity.tags.tags.map(t => t.tag.name);
    }

    // Extract owners
    if (entity.ownership?.owners) {
      normalized.owners = entity.ownership.owners.map(o => ({
        username: o.owner.username,
        type: o.type
      }));
    }

    return normalized;
  }

  /**
   * Convert entity to text for embedding
   */
  entityToText(entity) {
    const parts = [
      entity.name,
      entity.description,
      `Platform: ${entity.platform}`,
      entity.tags ? `Tags: ${entity.tags.join(', ')}` : '',
      entity.owners ? `Owners: ${entity.owners.map(o => o.username).join(', ')}` : ''
    ];

    return parts.filter(p => p).join('\n');
  }
}
