import React, { useState } from 'react';
import styled from 'styled-components';
import { message, Button } from 'antd';
import { CopyOutlined, ExpandOutlined, CompressOutlined } from '@ant-design/icons';

const Container = styled.div`
    position: relative;
`;

const JSONBox = styled.pre<{ expanded: boolean }>`
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
    max-height: ${(props) => (props.expanded ? 'none' : '400px')};
    overflow-y: ${(props) => (props.expanded ? 'visible' : 'auto')};
    white-space: pre;
`;

const ActionButtons = styled.div`
    position: absolute;
    top: 12px;
    right: 12px;
    display: flex;
    gap: 8px;
`;

const ActionButton = styled(Button)`
    && {
        font-size: 12px;
        height: 28px;
        padding: 0 12px;
    }
`;

interface JSONResultDisplayProps {
    data: any;
}

export default function JSONResultDisplay({ data }: JSONResultDisplayProps) {
    const [expanded, setExpanded] = useState(false);

    const handleCopy = () => {
        const jsonString = JSON.stringify(data, null, 2);
        navigator.clipboard.writeText(jsonString);
        message.success('Results copied to clipboard');
    };

    const formattedJSON = JSON.stringify(data, null, 2);

    return (
        <Container>
            <ActionButtons>
                <ActionButton size="small" icon={<CopyOutlined />} onClick={handleCopy}>
                    Copy
                </ActionButton>
                <ActionButton
                    size="small"
                    icon={expanded ? <CompressOutlined /> : <ExpandOutlined />}
                    onClick={() => setExpanded(!expanded)}
                >
                    {expanded ? 'Collapse' : 'Expand'}
                </ActionButton>
            </ActionButtons>
            <JSONBox expanded={expanded}>{formattedJSON}</JSONBox>
        </Container>
    );
}
