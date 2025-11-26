import React from 'react';
import styled from 'styled-components';
import { message } from 'antd';
import { CopyOutlined } from '@ant-design/icons';

const Container = styled.div`
    position: relative;
`;

const QueryBox = styled.pre`
    background: #f5f5f5;
    border: 1px solid #e8e8e8;
    border-radius: 6px;
    padding: 16px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 13px;
    line-height: 1.6;
    color: #262626;
    overflow-x: auto;
    margin: 0;
    white-space: pre;

    /* Syntax highlighting for GraphQL */
    .keyword {
        color: #cf222e;
        font-weight: 600;
    }

    .field {
        color: #0550ae;
    }

    .type {
        color: #8250df;
    }

    .string {
        color: #0a3069;
    }
`;

const CopyButton = styled.button`
    position: absolute;
    top: 12px;
    right: 12px;
    background: white;
    border: 1px solid #d9d9d9;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 12px;
    color: #595959;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;

    &:hover {
        background: #f5f5f5;
        border-color: #1890ff;
        color: #1890ff;
    }

    &:active {
        transform: scale(0.98);
    }
`;

interface GraphQLQueryDisplayProps {
    query: string;
}

export default function GraphQLQueryDisplay({ query }: GraphQLQueryDisplayProps) {
    const handleCopy = () => {
        navigator.clipboard.writeText(query);
        message.success('Query copied to clipboard');
    };

    const highlightGraphQL = (code: string): string => {
        return code
            .replace(/\b(query|mutation|subscription|fragment|on)\b/g, '<span class="keyword">$1</span>')
            .replace(/\b([A-Z][a-zA-Z0-9_]*)\b/g, '<span class="type">$1</span>')
            .replace(/"([^"]+)"/g, '<span class="string">"$1"</span>');
    };

    return (
        <Container>
            <CopyButton onClick={handleCopy}>
                <CopyOutlined />
                Copy
            </CopyButton>
            <QueryBox dangerouslySetInnerHTML={{ __html: highlightGraphQL(query) }} />
        </Container>
    );
}
