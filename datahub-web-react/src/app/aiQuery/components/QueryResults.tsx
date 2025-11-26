import React from 'react';
import styled from 'styled-components';
import { Alert, Spin, Typography } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { QueryResponse } from '../utils/api';
import GraphQLQueryDisplay from './GraphQLQueryDisplay';
import JSONResultDisplay from './JSONResultDisplay';

const { Text } = Typography;

const COLORS = {
    border: '#d9d9d9',
    background: '#ffffff',
    text: '#262626',
    textSecondary: '#8c8c8c',
    codeBg: '#f5f5f5',
    success: '#52c41a',
    error: '#ff4d4f',
};

const ResultsContainer = styled.div`
    margin-top: 24px;
`;

const Card = styled.div`
    background: ${COLORS.background};
    border: 1px solid ${COLORS.border};
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 16px;
`;

const CardHeader = styled.div`
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid #f0f0f0;
`;

const CardTitle = styled.div`
    font-size: 14px;
    font-weight: 600;
    color: ${COLORS.text};
`;

const QuestionText = styled(Text)`
    && {
        font-size: 14px;
        color: ${COLORS.textSecondary};
    }
`;

const LoadingContainer = styled(Card)`
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    gap: 16px;
`;

const LoadingText = styled.div`
    color: ${COLORS.textSecondary};
    font-size: 14px;
`;

const SuggestionBox = styled(Alert)`
    && {
        margin-bottom: 16px;
    }
`;

interface QueryResultsProps {
    response: QueryResponse | null;
    error: string | null;
    loading: boolean;
}

export default function QueryResults({ response, error, loading }: QueryResultsProps) {
    if (loading) {
        return (
            <ResultsContainer>
                <LoadingContainer>
                    <Spin indicator={<LoadingOutlined style={{ fontSize: 32 }} spin />} />
                    <LoadingText>Thinking and querying DataHub...</LoadingText>
                </LoadingContainer>
            </ResultsContainer>
        );
    }

    if (error) {
        return (
            <ResultsContainer>
                <Alert message="Error" description={error} type="error" showIcon />
            </ResultsContainer>
        );
    }

    if (!response) {
        return null;
    }

    return (
        <ResultsContainer>
            {response.suggestion && (
                <SuggestionBox
                    message="Suggestion"
                    description={response.suggestion}
                    type="info"
                    showIcon
                    closable
                />
            )}

            <Card>
                <CardHeader>
                    <CardTitle>Your Question</CardTitle>
                </CardHeader>
                <QuestionText>{response.question}</QuestionText>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Generated GraphQL Query</CardTitle>
                </CardHeader>
                <GraphQLQueryDisplay query={response.graphqlQuery} />
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Results</CardTitle>
                </CardHeader>
                <JSONResultDisplay data={response.results.data} />
            </Card>
        </ResultsContainer>
    );
}
