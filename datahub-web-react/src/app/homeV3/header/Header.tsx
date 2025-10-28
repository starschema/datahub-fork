import { colors } from '@components';
import React from 'react';
import styled from 'styled-components';

import GreetingText from '@app/homeV3/header/components/GreetingText';
import SearchBar from '@app/homeV3/header/components/SearchBar';
import { CenteredContainer, contentWidth } from '@app/homeV3/styledComponents';

export const HeaderWrapper = styled.div`
    display: flex;
    justify-content: center;
    padding: 16px 0 16px 0;
    background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 50%, #4f46e5 100%);
    border-bottom: 1px solid ${colors.gray[100]};
    border-radius: 0;
    position: relative;
    box-sizing: border-box;
`;

const StyledCenteredContainer = styled(CenteredContainer)`
    padding: 0 43px;
    ${contentWidth(0)}
`;

const Header = () => {
    return (
        <HeaderWrapper>
            <StyledCenteredContainer>
                <GreetingText />
                <SearchBar />
            </StyledCenteredContainer>
        </HeaderWrapper>
    );
};

export default Header;
