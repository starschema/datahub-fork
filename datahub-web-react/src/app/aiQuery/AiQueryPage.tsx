import React, { useState } from 'react';
import styled from 'styled-components';
import { Typography, message } from 'antd';
import QueryInput from './components/QueryInput';
import QueryResults from './components/QueryResults';
import { queryNLServer, QueryResponse } from './utils/api';

const { Title } = Typography;

const PageContainer = styled.div`
    padding: 28px 40px;
    max-width: 1400px;
    margin: 0 auto;
`;

const Header = styled.div`
    margin-bottom: 24px;
`;

const PageTitle = styled(Title)`
    && {
        margin-bottom: 8px;
        font-size: 24px;
        font-weight: 600;
    }
`;

const Description = styled.div`
    color: #595959;
    font-size: 14px;
`;

export default function AiQueryPage() {
    const [loading, setLoading] = useState(false);
    const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleQuery = async (question: string) => {
        setLoading(true);
        setError(null);
        setQueryResponse(null);

        try {
            const response = await queryNLServer(question);
            setQueryResponse(response);
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
            setError(errorMessage);
            message.error(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    return (
        <PageContainer>
            <Header>
                <PageTitle>AI Query</PageTitle>
                <Description>
                    Ask questions about your data in natural language, powered by GPT-4
                </Description>
            </Header>

            <QueryInput onSubmit={handleQuery} loading={loading} />

            {(queryResponse || error) && (
                <QueryResults response={queryResponse} error={error} loading={loading} />
            )}
        </PageContainer>
    );
}
