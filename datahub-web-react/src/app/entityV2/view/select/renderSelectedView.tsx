import { Tooltip } from '@components';
import CloseIcon from '@mui/icons-material/Close';
import { FadersHorizontal } from '@phosphor-icons/react';
import { Button } from 'antd';
import React from 'react';
import styled from 'styled-components';

import { ANTD_GRAY } from '@app/entityV2/shared/constants';
import { ViewLabel } from '@app/entityV2/view/select/styledComponents';
import { colors } from '@src/alchemy-components';

const SelectButton = styled(Button)<{ $selectedViewName: string; $isShowNavBarRedesign?: boolean }>`
    background-color: ${(props) => {
        if (props.$isShowNavBarRedesign) {
            return props.$selectedViewName ? colors.gray[1000] : colors.gray[50];
        }
        return props.$selectedViewName ? props.theme.styles['primary-color'] : 'transparent';
    }};
    border-color: ${(props) => {
        if (props.$isShowNavBarRedesign) {
            return props.$selectedViewName ? 'transparent' : colors.gray[200];
        }
        return props.$selectedViewName ? props.theme.styles['primary-color'] : 'transparent';
    }};
    border-radius: 6px;
    border: 1px solid;
    color: ${(props) => (props.$selectedViewName ? colors.white : colors.gray[600])} !important;
    max-width: ${(props) => (props.$isShowNavBarRedesign ? '120px' : '150px')};

    ${(props) =>
        props.$isShowNavBarRedesign &&
        `
        height: 28px;
        padding: 3px 8px;
        display: flex;
        box-shadow: none;
        line-height: 20px;

        & svg {
            color: ${props.$selectedViewName ? colors.white : colors.gray[600]} !important;
            transition: all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
        }
    `}

    &: hover {
        background: ${(props) => {
            if (props.$isShowNavBarRedesign) {
                return props.$selectedViewName ? colors.gray[1000] : 'rgba(255, 255, 255, 0.15)';
            }
            return props.theme.styles['primary-color'];
        }};
        color: ${(props) => (props.$selectedViewName ? colors.white : colors.gray[600])} !important;

        border-color: ${(props) => {
            if (props.$isShowNavBarRedesign) return 'rgba(255, 255, 255, 0.4)';
            return props.$selectedViewName ? props.theme.styles['primary-color'] : 'transparent';
        }};
    }

    &: focus {
        background-color: ${(props) => (props.$selectedViewName ? props.theme.styles['primary-color'] : 'transparent')};
        color: ${(props) => (props.$selectedViewName ? colors.white : colors.gray[600])} !important;
        border-color: ${(props) => (props.$selectedViewName ? props.theme.styles['primary-color'] : 'transparent')};

        ${(props) =>
            props.$isShowNavBarRedesign &&
            `
            background-color: rgba(255, 255, 255, 0.15);

            & svg {
                color: ${props.$selectedViewName ? colors.white : colors.gray[600]} !important;
            }
        `}
    }
`;

const SelectButtonContainer = styled.div`
    position: relative;

    &&&& .close-container {
        display: none;
    }

    &:hover,
    &:focus {
        &&&& .close-container {
            display: flex;
        }
    }
`;

const CloseButtonContainer = styled.div`
    position: absolute;
    top: -10px;
    right: -5px;
    background-color: ${ANTD_GRAY[1]};
    display: flex;
    align-items: center;
    border-radius: 100%;
    padding: 5px;
`;

const CloseIconStyle = styled(CloseIcon)`
    font-size: 10px !important;
    color: ${(props) => props.theme.styles['primary-color']};
`;

const StyledViewIcon = styled(FadersHorizontal)<{ $isShowNavBarRedesign?: boolean; $selectedViewName?: string }>`
    font-size: ${(props) => (props.$isShowNavBarRedesign ? '20px' : '18px')} !important;
    color: ${(props) => (props.$selectedViewName ? colors.white : colors.gray[600])} !important;
`;

type Props = {
    selectedViewName: string;
    isShowNavBarRedesign?: boolean;
    onClear: () => void;
    onClick?: () => void;
};

export const renderSelectedView = ({ selectedViewName, isShowNavBarRedesign, onClear, onClick }: Props) => {
    return (
        <SelectButtonContainer>
            <SelectButton
                $selectedViewName={selectedViewName}
                $isShowNavBarRedesign={isShowNavBarRedesign}
                onClick={() => onClick?.()}
            >
                <Tooltip showArrow={false} title={selectedViewName} placement="bottom">
                    <ViewLabel data-testid="views-icon">
                        {selectedViewName || (
                            <StyledViewIcon
                                $isShowNavBarRedesign={isShowNavBarRedesign}
                                $selectedViewName={selectedViewName}
                            />
                        )}
                    </ViewLabel>
                </Tooltip>
            </SelectButton>
            {selectedViewName && (
                <CloseButtonContainer
                    className="close-container"
                    onClick={(e) => {
                        e.stopPropagation();
                        onClear();
                    }}
                >
                    <CloseIconStyle />
                </CloseButtonContainer>
            )}
        </SelectButtonContainer>
    );
};
