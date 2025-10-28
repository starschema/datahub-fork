import React from 'react';
import { Link } from 'react-router-dom';
import styled from 'styled-components';

import { useNavBarContext } from '@app/homeV2/layout/navBarRedesign/NavBarContext';
import NavBarToggler from '@app/homeV2/layout/navBarRedesign/NavBarToggler';
import { useShowHomePageRedesign } from '@app/homeV3/context/hooks/useShowHomePageRedesign';
import { useIsHomePage } from '@app/shared/useIsHomePage';
import analytics, { EventType } from '@src/app/analytics';

const Container = styled.div`
    display: flex;
    width: 100%;
    height: 40px;
    min-height: 40px;
    align-items: center;
    gap: 8px;
    margin-left: -3px;
    transition: padding 250ms ease-in-out;
`;

const Logotype = styled.div`
    display: flex !important;
    align-items: center;
    justify-content: center;
    min-height: 24px;
    max-height: 24px;
    max-width: 42px;
    min-width: 42px;
    border-radius: 4px;
    position: relative;
    object-fit: contain;
    visibility: visible !important;
    opacity: 1 !important;

    & svg,
    img {
        max-height: 24px;
        max-width: 42px;
        min-width: 42px;
        object-fit: contain;
        visibility: visible !important;
        opacity: 1 !important;
    }
`;

const LogoText = styled.span`
    font-size: 16px;
    font-weight: 600;
    color: ${(props) => props.theme.styles['primary-color']};
    white-space: nowrap;
`;

const StyledLink = styled(Link)`
    display: flex;
    height: 40px;
    align-items: center;
    max-width: calc(100% - 40px);
    width: 100%;
    gap: 8px;
`;

type Props = {
    logotype?: React.ReactElement;
};

export default function NavBarHeader({ logotype }: Props) {
    const { toggle, isCollapsed } = useNavBarContext();
    const showHomepageRedesign = useShowHomePageRedesign();
    const isHomePage = useIsHomePage();

    function handleLogoClick() {
        if (isHomePage && showHomepageRedesign) {
            toggle();
        }
        analytics.event({ type: EventType.NavBarItemClick, label: 'Home' });
    }

    return (
        <Container>
            <StyledLink to="/" onClick={handleLogoClick}>
                <Logotype>{logotype}</Logotype>
                {!isCollapsed && <LogoText>DataHub Core</LogoText>}
            </StyledLink>
            {!isCollapsed && <NavBarToggler />}
        </Container>
    );
}
