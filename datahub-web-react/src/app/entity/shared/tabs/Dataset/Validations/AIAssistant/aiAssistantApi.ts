/**
 * API client for AI Assistant backend service.
 * Uses relative path for automatic dev/production compatibility.
 */

const AI_ASSISTANT_BASE_URL = '/api/ai-assistant';

export interface ColumnSchema {
    name: string;
    type: string;
    nullable: boolean;
    primary_key: boolean;
    description?: string;
}

export interface DatasetSchema {
    columns: ColumnSchema[];
    platform: string;
    database?: string;
    schema_name?: string;
    table: string;
}

export interface ValidateResponse {
    feasible: boolean;
    reasons: string[];
    schema?: DatasetSchema;
}

export interface AssertionConfig {
    type: string;
    params: Record<string, any>;
}

export interface GenerateResponse {
    sql: string;
    config: AssertionConfig;
    guardrails: {
        readonly: boolean;
        limits: {
            rowLimit: number;
            timeoutSec: number;
        };
    };
}

export interface ExecuteResponse {
    passed: boolean;
    metrics: Record<string, any>;
    error?: string;
}

export interface PersistResponse {
    assertion_urn: string;
}

export async function validateRule(datasetUrn: string, nlRule: string): Promise<ValidateResponse> {
    const response = await fetch(`${AI_ASSISTANT_BASE_URL}/validate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            dataset_urn: datasetUrn,
            nl_rule: nlRule,
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Validation failed');
    }

    return response.json();
}

export async function generateSQL(datasetUrn: string, nlRule: string): Promise<GenerateResponse> {
    const response = await fetch(`${AI_ASSISTANT_BASE_URL}/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            dataset_urn: datasetUrn,
            nl_rule: nlRule,
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'SQL generation failed');
    }

    return response.json();
}

export async function executeSQL(datasetUrn: string, sql: string, config: AssertionConfig): Promise<ExecuteResponse> {
    const response = await fetch(`${AI_ASSISTANT_BASE_URL}/execute`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            dataset_urn: datasetUrn,
            sql,
            config,
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'SQL execution failed');
    }

    return response.json();
}

export async function persistAssertion(
    datasetUrn: string,
    sql: string,
    config: AssertionConfig,
    nlRule: string,
    metadata?: {
        title?: string;
        description?: string;
        tags?: string[];
    },
    passed?: boolean,
    metrics?: Record<string, any>,
): Promise<PersistResponse> {
    const response = await fetch(`${AI_ASSISTANT_BASE_URL}/persist`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            dataset_urn: datasetUrn,
            sql,
            config,
            nl_rule: nlRule,
            metadata,
            passed,
            metrics,
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Persistence failed');
    }

    return response.json();
}
