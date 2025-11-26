import React, { useState } from 'react';
import styled from 'styled-components';
import { Input, Button, Tag } from 'antd';
import { SendOutlined } from '@ant-design/icons';

const COLORS = {
    primary: '#1890ff',
    primaryHover: '#40a9ff',
    border: '#d9d9d9',
    borderHover: '#40a9ff',
    background: '#ffffff',
    text: '#262626',
    textSecondary: '#8c8c8c',
    cardBg: '#fafafa',
};

const Card = styled.div`
    background: ${COLORS.background};
    border: 1px solid ${COLORS.border};
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 24px;
`;

const CardHeader = styled.div`
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
`;

const CardTitle = styled.div`
    font-size: 16px;
    font-weight: 600;
    color: ${COLORS.text};
`;

const GPTBadge = styled(Tag)`
    && {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        font-size: 11px;
        font-weight: 500;
        padding: 2px 8px;
        margin: 0;
    }
`;

const InputWrapper = styled.div`
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
`;

const StyledInput = styled(Input)`
    && {
        height: 40px;
        font-size: 14px;
        border-radius: 6px;

        &:hover {
            border-color: ${COLORS.borderHover};
        }

        &:focus {
            border-color: ${COLORS.primary};
            box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.1);
        }
    }
`;

const StyledButton = styled(Button)`
    && {
        height: 40px;
        min-width: 100px;
        border-radius: 6px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 6px;
    }
`;

const ExamplesSection = styled.div`
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
`;

const ExamplesLabel = styled.span`
    font-size: 13px;
    color: ${COLORS.textSecondary};
    font-weight: 500;
`;

const ExampleChip = styled.span`
    display: inline-block;
    padding: 4px 12px;
    background: ${COLORS.cardBg};
    border: 1px solid ${COLORS.border};
    border-radius: 16px;
    font-size: 12px;
    color: ${COLORS.text};
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
        background: ${COLORS.primary};
        color: white;
        border-color: ${COLORS.primary};
    }
`;

interface QueryInputProps {
    onSubmit: (question: string) => void;
    loading?: boolean;
}

const EXAMPLE_QUERIES = [
    'search for customer datasets',
    'show me columns in test_db.tpch_1000.customer',
    'what data quality checks exist',
    'show upstream datasets',
];

export default function QueryInput({ onSubmit, loading = false }: QueryInputProps) {
    const [question, setQuestion] = useState('');

    const handleSubmit = () => {
        const trimmedQuestion = question.trim();
        if (trimmedQuestion) {
            onSubmit(trimmedQuestion);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleSubmit();
        }
    };

    const fillExample = (text: string) => {
        setQuestion(text);
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Ask a Question</CardTitle>
                <GPTBadge>GPT-4</GPTBadge>
            </CardHeader>

            <InputWrapper>
                <StyledInput
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="e.g., What columns are in the customer table?"
                    disabled={loading}
                    autoFocus
                />
                <StyledButton type="primary" onClick={handleSubmit} loading={loading} icon={<SendOutlined />}>
                    Ask
                </StyledButton>
            </InputWrapper>

            <ExamplesSection>
                <ExamplesLabel>Try these examples:</ExamplesLabel>
                {EXAMPLE_QUERIES.map((example, index) => (
                    <ExampleChip key={index} onClick={() => fillExample(example)}>
                        {example}
                    </ExampleChip>
                ))}
            </ExamplesSection>
        </Card>
    );
}
