import { Typography } from 'antd';
import React from 'react';

import { AssertionInfo } from '@types';

type Props = {
    assertionInfo: AssertionInfo;
};

/**
 * A human-readable description of a SQL Assertion.
 */
export const SqlAssertionDescription = ({ assertionInfo }: Props) => {
    if (!assertionInfo) {
        return <Typography.Text>SQL assertion information unavailable</Typography.Text>;
    }

    const { description } = assertionInfo;

    return <Typography.Text>{description}</Typography.Text>;
};
