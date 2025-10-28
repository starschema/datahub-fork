import { Alert, Button, Card, Input, Space, Steps, Typography } from 'antd';
import React, { useState } from 'react';
import styled from 'styled-components';

import { useEntityData } from '@app/entity/shared/EntityContext';
import {
    AssertionConfig,
    executeSQL,
    ExecuteResponse,
    generateSQL,
    GenerateResponse,
    persistAssertion,
    validateRule,
    ValidateResponse,
} from './aiAssistantApi';

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

const Container = styled.div`
    padding: 24px;
    max-width: 1200px;
`;

const StyledCard = styled(Card)`
    margin-bottom: 16px;
`;

const SqlPreview = styled.pre`
    background: #f5f5f5;
    padding: 16px;
    border-radius: 4px;
    overflow-x: auto;
    font-family: 'Courier New', monospace;
    font-size: 13px;
`;

const MetricsCard = styled(Card)`
    background: #f9f9f9;
`;

type Phase = 'idle' | 'validating' | 'generating' | 'executing' | 'ready_to_persist' | 'persisted';

export function AIAssistantTab() {
    const { urn: datasetUrn } = useEntityData();

    const [phase, setPhase] = useState<Phase>('idle');
    const [nlRule, setNlRule] = useState('');
    const [error, setError] = useState<string | null>(null);

    // Validate phase state
    const [validateResponse, setValidateResponse] = useState<ValidateResponse | null>(null);

    // Generate phase state
    const [generateResponse, setGenerateResponse] = useState<GenerateResponse | null>(null);

    // Execute phase state
    const [executeResponse, setExecuteResponse] = useState<ExecuteResponse | null>(null);

    // Persist phase state
    const [assertionUrn, setAssertionUrn] = useState<string | null>(null);

    const handleValidate = async () => {
        if (!nlRule.trim()) {
            setError('Please enter a quality rule');
            return;
        }

        setError(null);
        setPhase('validating');

        try {
            const response = await validateRule(datasetUrn, nlRule);
            setValidateResponse(response);

            if (!response.feasible) {
                setError(`Rule is not feasible: ${response.reasons.join(', ')}`);
                setPhase('idle');
            } else {
                setPhase('idle');
            }
        } catch (err: any) {
            setError(err.message || 'Validation failed');
            setPhase('idle');
        }
    };

    const handleGenerate = async () => {
        setError(null);
        setPhase('generating');

        try {
            const response = await generateSQL(datasetUrn, nlRule);
            setGenerateResponse(response);
            setPhase('idle');
        } catch (err: any) {
            setError(err.message || 'SQL generation failed');
            setPhase('idle');
        }
    };

    const handleExecute = async () => {
        if (!generateResponse) {
            setError('Please generate SQL first');
            return;
        }

        setError(null);
        setPhase('executing');

        try {
            const response = await executeSQL(datasetUrn, generateResponse.sql, generateResponse.config);
            setExecuteResponse(response);

            if (response.error) {
                setError(`Execution error: ${response.error}`);
                setPhase('idle');
            } else {
                setPhase('ready_to_persist');
            }
        } catch (err: any) {
            setError(err.message || 'Execution failed');
            setPhase('idle');
        }
    };

    const handlePersist = async () => {
        if (!generateResponse) {
            setError('Please generate SQL first');
            return;
        }

        setError(null);
        setPhase('persisted');

        try {
            const response = await persistAssertion(
                datasetUrn,
                generateResponse.sql,
                generateResponse.config,
                nlRule,
                {
                    title: `AI: ${nlRule.substring(0, 50)}`,
                    description: `AI-generated assertion: ${nlRule}`,
                },
            );
            setAssertionUrn(response.assertion_urn);
        } catch (err: any) {
            setError(err.message || 'Persistence failed');
            setPhase('idle');
        }
    };

    const handleReset = () => {
        setPhase('idle');
        setNlRule('');
        setError(null);
        setValidateResponse(null);
        setGenerateResponse(null);
        setExecuteResponse(null);
        setAssertionUrn(null);
    };

    const currentStep =
        phase === 'idle'
            ? 0
            : phase === 'validating'
              ? 0
              : phase === 'generating'
                ? 1
                : phase === 'executing'
                  ? 2
                  : phase === 'ready_to_persist' || phase === 'persisted'
                    ? 3
                    : 0;

    return (
        <Container>
            <Title level={3}>AI Quality Assistant</Title>
            <Paragraph>
                Describe a data quality rule in natural language, and I'll generate a SQL assertion that automatically runs on every ingestion.
            </Paragraph>

            <Steps
                current={currentStep}
                items={[
                    { title: 'Validate' },
                    { title: 'Generate' },
                    { title: 'Execute' },
                    { title: 'Persist' },
                ]}
                style={{ marginBottom: 24 }}
            />

            {error && (
                <Alert
                    message="Error"
                    description={error}
                    type="error"
                    closable
                    onClose={() => setError(null)}
                    style={{ marginBottom: 16 }}
                />
            )}

            <StyledCard title="1. Describe Your Quality Rule">
                <TextArea
                    placeholder="Example: Ensure revenue column has no negative values"
                    value={nlRule}
                    onChange={(e) => setNlRule(e.target.value)}
                    rows={3}
                    disabled={phase === 'persisted'}
                />
                <Space style={{ marginTop: 16 }}>
                    <Button
                        type="primary"
                        onClick={handleValidate}
                        loading={phase === 'validating'}
                        disabled={!nlRule.trim() || phase === 'persisted'}
                    >
                        Validate
                    </Button>
                    {validateResponse?.feasible && (
                        <Button
                            type="primary"
                            onClick={handleGenerate}
                            loading={phase === 'generating'}
                            disabled={phase === 'persisted'}
                        >
                            Generate SQL
                        </Button>
                    )}
                </Space>

                {validateResponse && (
                    <Alert
                        message={validateResponse.feasible ? 'Rule is feasible' : 'Rule is not feasible'}
                        description={
                            validateResponse.reasons.length > 0 ? validateResponse.reasons.join(', ') : 'Ready to generate SQL'
                        }
                        type={validateResponse.feasible ? 'success' : 'warning'}
                        style={{ marginTop: 16 }}
                    />
                )}
            </StyledCard>

            {generateResponse && (
                <StyledCard title="2. Generated SQL">
                    <SqlPreview>{generateResponse.sql}</SqlPreview>
                    <Space style={{ marginTop: 16 }}>
                        <Button
                            type="primary"
                            onClick={handleExecute}
                            loading={phase === 'executing'}
                            disabled={phase === 'persisted'}
                        >
                            Test Execution
                        </Button>
                    </Space>
                </StyledCard>
            )}

            {executeResponse && (
                <StyledCard title="3. Execution Results">
                    <MetricsCard size="small">
                        <Space direction="vertical" style={{ width: '100%' }}>
                            <div>
                                <Text strong>Status: </Text>
                                <Text type={executeResponse.passed ? 'success' : 'danger'}>
                                    {executeResponse.passed ? 'PASSED ✓' : 'FAILED ✗'}
                                </Text>
                            </div>
                            {Object.entries(executeResponse.metrics).map(([key, value]) => (
                                <div key={key}>
                                    <Text strong>{key}: </Text>
                                    <Text>{JSON.stringify(value)}</Text>
                                </div>
                            ))}
                        </Space>
                    </MetricsCard>
                    <Space style={{ marginTop: 16 }}>
                        <Button type="primary" onClick={handlePersist} disabled={phase === 'persisted'}>
                            Save as Assertion
                        </Button>
                    </Space>
                </StyledCard>
            )}

            {assertionUrn && (
                <Alert
                    message="Assertion Created Successfully!"
                    description={`Assertion URN: ${assertionUrn}. This assertion will now run automatically on every ingestion.`}
                    type="success"
                    action={
                        <Button size="small" onClick={handleReset}>
                            Create Another
                        </Button>
                    }
                />
            )}
        </Container>
    );
}
