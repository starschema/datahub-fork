import React from 'react';
import styled from 'styled-components';

import { useShowNavBarRedesign } from '@app/useShowNavBarRedesign';
import { colors } from '@src/alchemy-components';

const Container = styled.div<{ $isShowNavBarRedesign?: boolean }>`
    color: ${colors.gray[600]};
    background-color: ${colors.gray[50]};
    opacity: 0.9;
    border-color: ${colors.gray[200]};
    border-radius: 6px;
    border: 1px solid ${colors.gray[200]};
    padding-right: 6px;
    padding-left: 6px;
    margin-right: 4px;
    margin-left: 4px;
    height: ${(props) => (props.$isShowNavBarRedesign ? '28px' : '24px')};
    display: ${(props) => (props.$isShowNavBarRedesign ? 'flex' : 'block')};
`;

const Letter = styled.span<{ $isShowNavBarRedesign?: boolean }>`
    padding: 2px;
    color: ${colors.gray[600]};
    text-align: center;
    line-height: ${(props) => (props.$isShowNavBarRedesign ? '23px' : 'normal')};
`;

export const CommandK = () => {
    const isShowNavBarRedesign = useShowNavBarRedesign();

    return (
        <Container $isShowNavBarRedesign={isShowNavBarRedesign}>
            <Letter $isShowNavBarRedesign={isShowNavBarRedesign}>⌘</Letter>
            <Letter $isShowNavBarRedesign={isShowNavBarRedesign}>K</Letter>
        </Container>
    );
};
