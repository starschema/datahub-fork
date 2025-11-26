export interface QueryResponse {
    question: string;
    graphqlQuery: string;
    results: {
        data: any;
        extensions?: any;
    };
    suggestion?: string;
}

export interface EntitySummary {
    urn: string;
    type: string;
    name: string;
    platform: string;
    platformLogo?: string;
    description?: string;
    qualifiedName?: string;
    stats?: {
        rowCount: number;
        columnCount: number;
        sizeInBytes: number;
        lastProfiled: number;
    };
    owners: Array<{
        username: string;
        displayName: string;
    }>;
    tags: Array<{
        name: string;
        color?: string;
    }>;
    domain?: string;
    container?: string;
    subTypes: string[];
    lastUpdated?: number;
    lineage: {
        upstream: {
            total: number;
            byType: Record<string, number>;
        };
        downstream: {
            total: number;
            byType: Record<string, number>;
        };
    };
}

// NL Query Server URL - use relative URLs to go through nginx proxy with same-origin cookies
// When accessing via nginx at port 9002, requests will be proxied to the NL server
// This ensures DataHub session cookies (set for localhost:9002) are sent with requests
const NL_QUERY_SERVER = '';

export async function queryNLServer(question: string): Promise<QueryResponse> {
    const response = await fetch(`${NL_QUERY_SERVER}/query`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
        credentials: 'include', // Pass auth cookies to NL server for user-based authorization
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Query failed with status ${response.status}`);
    }

    return response.json();
}

export async function getEntitySummary(urn: string): Promise<EntitySummary> {
    const response = await fetch(`${NL_QUERY_SERVER}/entity-summary`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ urn }),
        credentials: 'include', // Pass auth cookies to NL server for user-based authorization
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Failed to fetch entity summary`);
    }

    return response.json();
}

export async function checkNLServerHealth(): Promise<{ status: string; openai: boolean; cacheSize: number }> {
    const response = await fetch(`${NL_QUERY_SERVER}/health`);

    if (!response.ok) {
        throw new Error('NL Query server is not available');
    }

    return response.json();
}
